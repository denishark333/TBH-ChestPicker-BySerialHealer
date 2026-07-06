from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from typing import Any


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str = "") -> None:
        self.token = token.strip()
        self.chat_id = str(chat_id).strip()

    def call_api(self, method: str, payload: dict[str, Any] | None = None) -> tuple[bool, str, dict[str, Any]]:
        if not self.token:
            return False, "Telegram bot token is empty", {}

        payload = payload or {}
        url = f"https://api.telegram.org/bot{self.token}/{method}"

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "TBH-Chest-Peeker",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                body = response.read().decode("utf-8")
            data = json.loads(body) if body else {}
            if not data.get("ok", False):
                return False, data.get("description", "Telegram API returned ok=false"), data
            return True, "Success", data
        except Exception as urllib_error:
            return self._call_api_with_curl(url, payload, urllib_error)

    def _call_api_with_curl(
        self,
        url: str,
        payload: dict[str, Any],
        original_error: Exception,
    ) -> tuple[bool, str, dict[str, Any]]:
        curl_path = shutil.which("curl.exe") or shutil.which("curl")
        if not curl_path:
            return False, str(original_error), {}

        body_path = ""
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".json") as body_file:
                json.dump(payload, body_file)
                body_path = body_file.name

            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.run(
                [
                    curl_path,
                    "--silent",
                    "--show-error",
                    "--max-time",
                    "10",
                    "-X",
                    "POST",
                    "-H",
                    "Content-Type: application/json",
                    "--data-binary",
                    f"@{body_path}",
                    url,
                ],
                capture_output=True,
                text=True,
                creationflags=creationflags,
            )
            if proc.returncode != 0:
                detail = proc.stderr.strip() or proc.stdout.strip() or str(original_error)
                return False, detail, {}

            data = json.loads(proc.stdout) if proc.stdout else {}
            if not data.get("ok", False):
                return False, data.get("description", "Telegram API returned ok=false"), data
            return True, "Success", data
        except Exception as curl_error:
            return False, f"urllib failed: {original_error}; curl failed: {curl_error}", {}
        finally:
            if body_path:
                try:
                    os.unlink(body_path)
                except Exception:
                    pass

    def detect_chat_id(self) -> tuple[bool, str, str]:
        success, msg, data = self.call_api("getUpdates", {})
        if not success:
            return False, msg, ""

        for update in reversed(data.get("result", [])):
            message = update.get("message") or update.get("edited_message") or update.get("channel_post")
            if not message:
                continue
            chat = message.get("chat") or {}
            if "id" in chat:
                return True, "Success", str(chat["id"])

        return False, "No Chat ID found. Send /start to your bot in Telegram, then try again.", ""

    def send_message(self, text: str, chat_id: str | None = None) -> tuple[bool, str]:
        target_chat_id = str(chat_id or self.chat_id).strip()
        if not target_chat_id:
            return False, "Telegram Chat ID is empty"

        success, msg, _ = self.call_api(
            "sendMessage",
            {
                "chat_id": target_chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
        )
        return success, msg

    def send_target_alert(self, item_id: int, item_name: str, grade: str, action_type: str) -> tuple[bool, str]:
        return self.send_message(self.build_target_message(item_id, item_name, grade, action_type))

    @staticmethod
    def build_target_message(item_id: int, item_name: str, grade: str, action_type: str) -> str:
        if action_type == "chests":
            status = "Item found in upcoming chests"
        elif action_type == "direct":
            status = "Item collected as direct drop"
        elif action_type == "synthesis":
            status = "Item collected by synthesis"
        else:
            status = "Item detected"

        return (
            "TBH target alert\n"
            f"{status}\n\n"
            f"Name: {item_name}\n"
            f"ID: {item_id}\n"
            f"Grade: {grade}"
        )
