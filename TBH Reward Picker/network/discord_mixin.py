import json
import urllib.request
import threading
from typing import Any
import customtkinter as ctk


COLOR_BG = "#0b0b0b"
COLOR_FRAME = "#141414"
COLOR_PRIMARY = "#c8a24b"
COLOR_HOVER = "#f2c94c"
COLOR_SECONDARY = "#1d1d1d"
COLOR_SEC_HOVER = "#2a2a2a"
COLOR_TEXT = "#e8e8e8"
COLOR_MUTED = "#b8b8b8"
COLOR_ENTRY_BG = "#111111"
COLOR_BORDER = "#2f2f2f"

class DiscordMixin:
    def on_discord_notify_toggled(self) -> None:
        self.discord_notify_enabled = self.discord_notify_var.get()
        self.save_peeker_config()
        self.append_log(f"[CONFIG] Discord notification enabled: {self.discord_notify_enabled}\n")

    def on_webhook_url_typed(self, event: Any) -> None:
        self.discord_webhook_url = self.entry_webhook_url.get().strip()
        self.save_peeker_config()

    def on_discord_user_id_typed(self, event: Any) -> None:
        self.discord_user_id = self.entry_discord_user_id.get().strip()
        self.save_peeker_config()

    def send_test_discord_notification(self) -> None:
        url = self.entry_webhook_url.get().strip()
        if not url:
            self.append_log("[DISCORD] Cannot send test notification: Webhook URL is empty.\n")
            return
        self.append_log("[DISCORD] Sending test notification...\n")
        def run_test():
            payload = {
                "username": "TBH Chest Peeker",
                "content": "🔔 This is a test notification from your TBH Chest Peeker! Your Webhook configuration is working correctly."
            }
            success, msg = self.post_to_discord_webhook(url, payload)
            if success:
                self.after(0, lambda: self.append_log("[DISCORD] Test notification sent successfully!\n"))
            else:
                self.after(0, lambda: self.append_log(f"[DISCORD] [ERROR] Failed to send test notification: {msg}\n"))
        threading.Thread(target=run_test, daemon=True).start()

    def post_to_discord_webhook(self, url: str, payload: dict) -> tuple[bool, str]:
        import urllib.request
        import urllib.error
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                response.read()
            return True, "Success"
        except urllib.error.HTTPError as e:
            return False, f"HTTP Error {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            return False, f"URL Error: {e.reason}"
        except Exception as e:
            return False, str(e)

    def notify_discord_match(self, item_id: int, item_name: str, grade: str, action_type: str) -> None:
        if not self.discord_notify_enabled or not self.discord_webhook_url:
            return
        import datetime
        # Color based on item grade
        color_hex_map = {
            "RARE": 0x3498db,      # Blue
            "BEYOND": 0x1abc9c,    # Dark Cyan
            "LEGENDARY": 0xe67e22, # Orange
            "IMMORTAL": 0xe74c3c,  # Red
            "ARCANA": 0x9b59b6,    # Purple
            "CELESTIAL": 0x00d2d3, # Cyan/Light Blue
            "DIVINE": 0xf1c40f,    # Gold
            "COSMIC": 0xfd79a8,    # Pink
            "BOSS": 0x34495e,      # Dark Gray
        }
        color = color_hex_map.get(grade.upper(), 0xbdc3c7) # default gray
        title = "🎯 Target Item Filter Matched!"
        if action_type == "chests":
            desc = f"**Item Found in Upcoming Chests!**\n\n• **Name**: {item_name}\n• **ID**: {item_id}\n• **Grade**: {grade}\n\n*The relogger has paused to let you collect it.*"
        elif action_type == "direct":
            desc = f"**Item Collected (Direct Drop)!**\n\n• **Name**: {item_name}\n• **ID**: {item_id}\n• **Grade**: {grade}\n\n*The relogger is resuming automated re-entry.*"
        elif action_type == "synthesis":
            desc = f"**Item Collected (Synthesis)!**\n\n• **Name**: {item_name}\n• **ID**: {item_id}\n• **Grade**: {grade}\n\n*The relogger is resuming automated re-entry.*"
        else:
            desc = f"**Item Detected!**\n\n• **Name**: {item_name}\n• **ID**: {item_id}\n• **Grade**: {grade}"
        payload = {
            "username": "TBH Chest Peeker",
            "embeds": [
                {
                    "title": title,
                    "description": desc,
                    "color": color,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                }
            ]
        }
        # Add @mention if Discord User ID is set
        if self.discord_user_id:
            payload["content"] = f"<@{self.discord_user_id}>"
        def run_notify():
            success, msg = self.post_to_discord_webhook(self.discord_webhook_url, payload)
            if not success:
                self.after(0, lambda: self.append_log(f"[DISCORD] [ERROR] Failed to send webhook alert: {msg}\n"))
        threading.Thread(target=run_notify, daemon=True).start()