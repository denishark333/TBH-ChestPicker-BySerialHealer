import os
import sys
import json
import threading
import subprocess
import time
import shutil
import ctypes
from pathlib import Path
from typing import Any
import re
from tkinter import messagebox
try:
    import winsound
except ImportError:
    winsound = None

ROOT = Path(__file__).parent.parent.resolve()
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

GRADE_COLORS = {
    "COMMON": "#e4e4e4",
    "UNCOMMON": "#54fc0c",
    "RARE": "#2f8bfc",
    "LEGENDARY": "#fc9c0c",
    "IMMORTAL": "#fc2424",
    "ARCANA": "#b40cfc",
    "BEYOND": "#fc246c",
    "CELESTIAL": "#6ccce4",
    "DIVINE": "#fce454",
    "COSMIC": "#fcfcfc",
    "BOSS": "#00a8ff",
    "SOULSTONE": "#e74c3c"
}

ADDON_PATH = ROOT / "chest_peeker.py"

class ProxyMixin:
    def generate_certificate(self) -> bool:
        cert_path = Path(os.path.expandvars(r"%USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.cer"))
        if cert_path.exists():
            return True
        self.append_log("[INFO] Certificate not found. Generating certificate via mitmproxy...\n")
        # Start proxy briefly to generate cert
        port = 8877
        try:
            pdata = json.loads((ROOT / "config.json").read_text(encoding="utf-8-sig"))
            port = int(pdata.get("listen_port", 8877))
        except Exception:
            pass
        common_args = [
            "-q",
            "-s",
            str(ADDON_PATH),
            "--listen-port",
            str(port),
            "--flow-detail",
            "0",
            "--set",
            "block_global=false",
        ]
        mitmdump = shutil.which("mitmdump")
        if mitmdump:
            cmd = [mitmdump, *common_args]
        else:
            cmd = [
                sys.executable,
                "-u",
                "-c",
                "from mitmproxy.tools.main import mitmdump; mitmdump()",
                *common_args
            ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                cwd=str(ROOT)
            )
            # Wait up to 5 seconds for cert generation
            for _ in range(50):
                if cert_path.exists():
                    break
                time.sleep(0.1)
            proc.terminate()
            proc.wait()
            return cert_path.exists()
        except Exception as e:
            self.append_log(f"[ERROR] Failed to generate certificate: {e}\n")
            return False

    def install_cert_automatically(self) -> None:
        cert_path = Path(os.path.expandvars(r"%USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.cer"))
        if not cert_path.exists():
            if not self.generate_certificate():
                self.append_log("[ERROR] Certificate file not found and could not generate. Please run proxy manually first.\n")
                messagebox.showerror("Error", "Certificate file not found and could not be generated automatically.")
                return
        self.append_log(f"[INFO] Installing certificate: {cert_path}...\n")
        def work():
            cmd = ["certutil", "-addstore", "-user", "root", str(cert_path)]
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                output = []
                if proc.stdout:
                    for line in proc.stdout:
                        output.append(line)
                proc.wait()
                if proc.returncode == 0:
                    self.append_log("[INFO] Certificate successfully trusted in root store.\n")
                    self.after(0, lambda: messagebox.showinfo("Success", "Certificate successfully trusted!"))
                else:
                    self.append_log(f"[ERROR] certutil exited with error code: {proc.returncode}\n")
                    self.append_log("".join(output) + "\n")
                    self.after(0, lambda: messagebox.showerror("Error", f"certutil failed with code {proc.returncode}"))
            except Exception as e:
                self.append_log(f"[ERROR] Failed to run certutil: {e}\n")
                self.after(0, lambda err=e: messagebox.showerror("Error", f"Failed to run certutil: {err}"))
        threading.Thread(target=work, daemon=True).start()

    def toggle_proxy(self) -> None:
        if self.proxy_running:
            self.stop_proxy()
        else:
            self.start_proxy()

    def start_proxy(self) -> None:
        if self.proxy_running:
            return
        # Verify peeker script exists
        if not ADDON_PATH.exists():
            self.append_log(f"[ERROR] chest_peeker.py not found at: {ADDON_PATH}\n")
            return
        self.btn_proxy.configure(text="Stopping Proxy...", state="disabled")
        def work():
            # Get configured port from config.json if available
            port = 8877
            config_path = ROOT / "config.json"
            if config_path.exists():
                try:
                    pdata = json.loads(config_path.read_text(encoding="utf-8-sig"))
                    port = int(pdata.get("listen_port", 8877))
                except Exception:
                    pass
            # Automatically clean up any leftover processes listening on this port before starting
            try:
                if os.name == 'nt':
                    netstat_cmd = f"netstat -ano | findstr LISTENING | findstr :{port}"
                    p = subprocess.run(
                        ["cmd", "/c", netstat_cmd],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if p.returncode == 0 and p.stdout:
                        pids = set()
                        for line in p.stdout.strip().split("\n"):
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                pid = parts[-1]
                                if pid.isdigit() and int(pid) > 0 and int(pid) != os.getpid():
                                    pids.add(int(pid))
                        for pid in pids:
                            self.append_log(f"[PROXY] Cleaning up leftover process on port {port} (PID: {pid})...\n")
                            subprocess.run(
                                ["taskkill", "/f", "/t", "/pid", str(pid)],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                            time.sleep(0.5)
            except Exception as pe:
                self.log_gui_error(f"Failed to clear port {port}: {pe}")
            # Run mitmdump directly to prevent grandchild process pipe issues
            mitmdump_bin = shutil.which("mitmdump")
            common_args = [
                "-q",
                "-s",
                str(ADDON_PATH),
                "--listen-port",
                str(port),
                "--flow-detail",
                "0",
                "--set",
                "block_global=false",
                "--ignore-hosts",
                r".*\.steampowered\.com|.*\.steamcommunity\.com|.*\.steamgames\.com|.*\.steamcontent\.com|.*\.steamstatic\.com|.*\.steamusercontent\.com|.*\.steam-chat\.com|.*\.valvesoftware\.com|.*\.akamaihd\.net"
            ]
            if mitmdump_bin:
                cmd = [mitmdump_bin, *common_args]
            else:
                cmd = [
                    sys.executable,
                    "-u",
                    "-c",
                    "from mitmproxy.tools.main import mitmdump; mitmdump()",
                    *common_args
                ]
            try:
                env = os.environ.copy()
                env["PYTHONUTF8"] = "1"
                self.proxy_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    cwd=str(ROOT),
                    env=env
                )
                self.proxy_running = True
                # Update UI inside main thread
                def ready_ui():
                    self.btn_proxy.configure(text="Stop Peeker Proxy", fg_color=COLOR_PRIMARY, text_color="#ff0000", state="normal")
                    self.lbl_proxy_status.configure(text=f"Status: Active (listening on port {port})", text_color="#0f8304")
                    self.append_log(f"[PROXY] Proxy process started successfully.\n")
                self.after(0, ready_ui)
                # Read output stream line by line
                if self.proxy_process.stdout:
                    for line in self.proxy_process.stdout:
                        self.parse_stdout_line(line)
            except Exception as e:
                self.log_gui_error(f"Failed to launch proxy: {e}")
            finally:
                self.proxy_running = False
                def stopped_ui():
                    self.btn_proxy.configure(text="Start Peeker Proxy", fg_color=COLOR_PRIMARY, state="normal")
                    self.lbl_proxy_status.configure(text="Status: Stopped", text_color=COLOR_MUTED)
                    self.append_log("[PROXY] Proxy process finished.\n")
                self.after(0, stopped_ui)
        threading.Thread(target=work, daemon=True).start()

    def stop_proxy(self) -> None:
        if not self.proxy_running:
            return
        self.append_log("[PROXY] Shutting down proxy...\n")
        # Restore system proxy (chest_peeker restores it automatically on exit, but let's make sure)
        import winreg
        try:
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            # Notify Windows settings changed
            INTERNET_OPTION_SETTINGS_CHANGED = 39
            INTERNET_OPTION_REFRESH = 37
            try:
                internet_set_option = ctypes.windll.wininet.InternetSetOptionW
                internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
                internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)
            except Exception:
                pass
        except Exception:
            pass
        if self.proxy_process:
            try:
                # Forcefully terminate the process and all of its children (/t) on Windows
                if os.name == 'nt':
                    subprocess.run(
                        ["taskkill", "/f", "/t", "/pid", str(self.proxy_process.pid)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    self.proxy_process.terminate()
                    self.proxy_process.wait(timeout=2)
            except Exception:
                pass
            self.proxy_process = None

    def log_gui_error(self, msg: str) -> None:
        self.after(0, lambda: self.append_log(f"[ERROR] {msg}\n"))

    def parse_stdout_line(self, line: str) -> None:
        # Standard stdout forwarding
        cleaned = line.strip()
        # Check for structured GUI tags
        if cleaned.startswith("__PEEK_RESULT__:"):
            parts = cleaned.split(":", 2)
            if len(parts) >= 3:
                res_type = parts[1]
                data_json = parts[2]
                try:
                    parsed_data = json.loads(data_json)
                    self.after(0, lambda: self.process_peek_result(res_type, parsed_data))
                except Exception as e:
                    self.log_gui_error(f"Failed to parse result payload: {e}")
            return
        # Debug traffic lines from proxy — show in log for traffic analysis
        if cleaned.startswith("__PEEK_DEBUG__:"):
            parts = cleaned.split(":", 2)
            if len(parts) >= 3:
                body_size = parts[1]
                preview = parts[2][:120]
                self.after(0, lambda: self.append_log(f"[TRAFFIC] Response ({body_size} bytes): {preview}...\n"))
            return
        # Filter out ANSI sequences from terminal lines before appending to text area
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        plain_line = ansi_escape.sub('', line)
        if plain_line.strip() and not plain_line.startswith("=") and not plain_line.startswith(" Chest:") and not plain_line.startswith("    └─ Drop:"):
            self.after(0, lambda: self.append_log(plain_line))

    def process_peek_result(self, res_type: str, data: Any) -> None:
        """Triggers UI layout displaying the items and checks filters for relogger."""
        try:
            self._process_peek_result_impl(res_type, data)
        except Exception as e:
            import traceback
            self.append_log(f"\n[CRITICAL ERROR] Error in process_peek_result: {e}\n{traceback.format_exc()}\n")

    def _process_peek_result_impl(self, res_type: str, data: Any) -> None:
        self.dashboard_scans_done += 1
        self.dashboard_last_activity = f"Scan {self.dashboard_scans_done}"
        self.update_dashboard_stats()
        # Handle 'seen' results silently — these are item IDs from any server response.
        # If a target match is found while a countdown is running, auto-trigger safety relog.
        if res_type == "seen":
            seen_ids = data if isinstance(data, list) else []
            # Desempilhar itens da fila sequencialmente para manter o controle de progresso
            for item_id in seen_ids:
                if hasattr(self, 'current_stage_queue') and self.current_stage_queue and item_id in self.current_stage_queue:
                    try:
                        idx = self.current_stage_queue.index(item_id)
                        # Desempilhar até o item atual (inclusive)
                        for _ in range(idx + 1):
                            popped_id = self.current_stage_queue.pop(0)
                            if hasattr(self, 'current_chest_queue') and self.current_chest_queue:
                                self.current_chest_queue.pop(0)
                            popped_info = self.get_item_info_by_id(popped_id)
                            popped_name = self.get_item_name(popped_info, f"Item ({popped_id})")
                            self.append_log(f"[QUEUE] Chest opened: {popped_name}. Remaining drops: {len(self.current_stage_queue)}\n")
                            # Atualizar visual do card se for um item importante sendo coletado
                            if popped_info:
                                grade = popped_info.get("grade", "COMMON").upper()
                                is_soulstone = "soulstone" in popped_name.lower() or "soul stone" in popped_name.lower()
                                card_key = "SOULSTONE" if is_soulstone else grade
                                if hasattr(self, 'upcoming_card_widgets') and card_key in self.upcoming_card_widgets:
                                    widgets = self.upcoming_card_widgets[card_key]
                                    current_display_name = widgets["lbl_name"].cget("text")
                                    if current_display_name and popped_name in current_display_name and not current_display_name.startswith("✓"):
                                        widgets["lbl_name"].configure(text=f"✓ Coletado: {popped_name}", text_color="#7f8c8d")
                                        widgets["card"].configure(border_color="#2c3e50")
                    except Exception:
                        pass
            if not self.relogger_active:
                return
            # Only act if a paused countdown is running (we found a target and are waiting)
            if not (hasattr(self, 'paused_countdown_id') and self.paused_countdown_id):
                return
            # Don't re-trigger if already in safety countdown
            if self.safety_countdown_active:
                return
            for item_id in seen_ids:
                # Skip if in ignore list
                if item_id in getattr(self, "ignored_items", []):
                    continue
                # Check specific item targets
                if item_id in self.target_items:
                    info = self.get_item_info_by_id(item_id) or {}
                    name = self.get_item_name(info, f"Item ({item_id})")
                    self.append_log(f"\n[LIVE DETECT] 🎯 Target item '{name}' (ID: {item_id}) detected in server response!\n")
                    self.append_log(f"[LIVE DETECT] Item has been collected! Switching to anti-rollback safety delay...\n")
                    self.skip_to_safety_relog()
                    return
                # Check grade targets
                info = self.get_item_info_by_id(item_id)
                if info:
                    grade = info.get("grade", "COMMON").upper()
                    if grade in self.target_grades:
                        name = self.get_item_name(info, "").lower()
                        if "soulstone" in name or "soul stone" in name:
                            continue
                        display_name = self.get_item_name(info, f"Item ({item_id})")
                        self.append_log(f"\n[LIVE DETECT] 🎯 Target grade '{grade}' item '{display_name}' (ID: {item_id}) detected in server response!\n")
                        self.append_log(f"[LIVE DETECT] Item has been collected! Switching to anti-rollback safety delay...\n")
                        self.skip_to_safety_relog()
                        return
            return
        # Handle server/auth errors with progressive backoff
        if res_type == "error":
            self.consecutive_errors += 1
            error_code = str(data)
            # Progressive backoff: 10s first, +5s each consecutive error, max 30s
            backoff = min(10 + (self.consecutive_errors - 1) * 5, 30)
            self.append_log(f"\n[ERROR] ⚠ Server error detected (HTTP {error_code})! Error #{self.consecutive_errors}\n")
            self.append_log(f"[ERROR] Backing off {backoff}s to let server/Steam session recover...\n")
            if self.relogger_active and self.relogger_method == "process_restart":
                self.reentry_in_progress = False
                def error_recovery():
                    time.sleep(1)
                    try:
                        subprocess.run(
                            ["taskkill", "/f", "/im", "TaskBarHero.exe"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        self._kill_trainer_elevated()
                    except Exception:
                        pass
                    # Delay watchdog relaunch by manipulating last_launch_time
                    self.last_launch_time = time.time() + backoff - 20.0
                    self.after(0, lambda: self.append_log(f"[WATCHDOG] Game killed. Will relaunch in ~{backoff}s...\n"))
                threading.Thread(target=error_recovery, daemon=True).start()
            return
        # Valid game data received — reset error counter
        self.consecutive_errors = 0
        found_item_ids = []
        found_item_indices = []
        found_chest_ids = []
        found_item_keys = []
        if res_type == "chests":
            left_list = []
            right_list = []
            for idx, (chest_id, reward_id, item_key) in enumerate(data, 1):
                c_info = self.get_item_info_by_id(chest_id) or {}
                r_info = self.get_item_info_by_id(reward_id) or {}
                c_name = self.get_item_name(c_info, f"Chest ({chest_id})")
                r_name = self.get_item_name(r_info, f"Reward ({reward_id})")
                r_grade = r_info.get("grade", "COMMON")
                c_grade = c_info.get("grade", "COMMON")
                is_boss_chest = "stageboss" in c_name.lower()
                if is_boss_chest:
                    c_grade = "BOSS"
                item_data = {
                    "idx": idx,
                    "c_name": c_name,
                    "c_grade": c_grade,
                    "r_name": r_name,
                    "r_grade": r_grade,
                    "item_key": str(item_key)
                }
                if is_boss_chest:
                    left_list.append(item_data)
                else:
                    right_list.append(item_data)
                found_item_ids.append(reward_id)
                found_item_indices.append(idx)
                found_chest_ids.append(chest_id)
                found_item_keys.append(str(item_key))
            # Render side-by-side columns
            col_width = 56
            self.append_log(f"\n================================================================================================\n")
            self.append_log(f"                               [PEEK FEED] DETECTED MAP DATA LOADED (CHESTS)\n")
            self.append_log(f"================================================================================================\n")
            header_left = " StageBoss Chests (Raros)"
            header_right = " Normal Chests (Uncommon)"
            divider = " │ "
            self.append_log(header_left.ljust(col_width) + divider + header_right + "\n")
            self.append_log("-" * col_width + "┼" + "-" * 38 + "\n")
            num_rows = max(len(left_list), len(right_list))
            for i in range(num_rows):
                # --- LINE 1: Chest Info ---
                # Left side
                if i < len(left_list):
                    item = left_list[i]
                    lbl = f" [{i+1}] Chest: "
                    val = f"{item['c_name']} [{item['c_grade']}]"
                    self.txt_log.insert("end", lbl)
                    tag_name = f"grade_{item['c_grade'].upper()}"
                    self.txt_log.tag_config(tag_name, foreground=GRADE_COLORS.get(item['c_grade'].upper(), COLOR_TEXT))
                    self.txt_log.insert("end", val, tag_name)
                    curr_len = len(lbl) + len(val)
                    if curr_len < col_width:
                        self.txt_log.insert("end", " " * (col_width - curr_len))
                else:
                    self.txt_log.insert("end", " " * col_width)
                # Divider
                self.txt_log.insert("end", divider)
                # Right side
                if i < len(right_list):
                    item = right_list[i]
                    lbl = f" [{i+1}] Chest: "
                    val = f"{item['c_name']} [{item['c_grade']}]"
                    self.txt_log.insert("end", lbl)
                    tag_name = f"grade_{item['c_grade'].upper()}"
                    self.txt_log.tag_config(tag_name, foreground=GRADE_COLORS.get(item['c_grade'].upper(), COLOR_TEXT))
                    self.txt_log.insert("end", val, tag_name)
                self.txt_log.insert("end", "\n")
                # --- LINE 2: Drop Info ---
                # Left side
                if i < len(left_list):
                    item = left_list[i]
                    lbl = "   └─ Drop: "
                    val = f"{item['r_name']} [{item['r_grade']}]"
                    self.txt_log.insert("end", lbl)
                    tag_name = f"grade_{item['r_grade'].upper()}"
                    self.txt_log.tag_config(tag_name, foreground=GRADE_COLORS.get(item['r_grade'].upper(), COLOR_TEXT))
                    self.txt_log.insert("end", val, tag_name)
                    curr_len = len(lbl) + len(val)
                    if curr_len < col_width:
                        self.txt_log.insert("end", " " * (col_width - curr_len))
                else:
                    self.txt_log.insert("end", " " * col_width)
                # Divider
                self.txt_log.insert("end", divider)
                # Right side
                if i < len(right_list):
                    item = right_list[i]
                    lbl = "   └─ Drop: "
                    val = f"{item['r_name']} [{item['r_grade']}]"
                    self.txt_log.insert("end", lbl)
                    tag_name = f"grade_{item['r_grade'].upper()}"
                    self.txt_log.tag_config(tag_name, foreground=GRADE_COLORS.get(item['r_grade'].upper(), COLOR_TEXT))
                    self.txt_log.insert("end", val, tag_name)
                self.txt_log.insert("end", "\n")
            self.append_log(f"================================================================================================\n\n")
        else:
            self.append_log(f"\n======================================================\n")
            self.append_log(f"   [PEEK FEED] DETECTED MAP DATA LOADED ({res_type.upper()})\n")
            self.append_log(f"======================================================\n")
            if res_type == "direct":
                # list of item_ids
                for idx, item_id in enumerate(data, 1):
                    info = self.get_item_info_by_id(item_id) or {}
                    name = self.get_item_name(info, f"Drop ({item_id})")
                    grade = info.get("grade", "COMMON")
                    self.append_colored_drop(idx, name, grade, is_chest=False)
                    found_item_ids.append(item_id)
                    found_item_indices.append(1)
                    found_chest_ids.append(None)
            elif res_type == "synthesis":
                # single item_id
                item_id = int(data)
                info = self.get_item_info_by_id(item_id) or {}
                name = self.get_item_name(info, f"Drop ({item_id})")
                grade = info.get("grade", "COMMON")
                self.append_colored_drop(1, name, grade, is_chest=False)
                found_item_ids.append(item_id)
                found_item_indices.append(1)
                found_chest_ids.append(None)
            self.append_log(f"======================================================\n\n")
        self.dashboard_loots_observed += len(found_item_ids)
        self.dashboard_last_activity = f"Observed {len(found_item_ids)} loot(s)"
        self.update_dashboard_stats()
        # Save last found items so we can re-evaluate them immediately if relogger starts
        self.last_found_item_ids = found_item_ids
        self.last_found_item_indices = found_item_indices
        self.last_found_chest_ids = found_chest_ids
        self.last_found_res_type = res_type
        self.evaluate_filters_and_relog(found_item_ids, res_type, found_item_indices, found_chest_ids, found_item_keys)

    def evaluate_filters_and_relog(self, found_item_ids: list[int], res_type: str = "chests", item_indices: list[int] | None = None, chest_ids: list[int | None] | None = None, item_keys: list[str] | None = None) -> None:
        try:
            self._evaluate_filters_and_relog_impl(found_item_ids, res_type, item_indices, chest_ids, item_keys)
        except Exception as e:
            import traceback
            self.append_log(f"\n[CRITICAL ERROR] Error in evaluate_filters_and_relog: {e}\n{traceback.format_exc()}\n")

    def _evaluate_filters_and_relog_impl(self, found_item_ids: list[int], res_type: str = "chests", item_indices: list[int] | None = None, chest_ids: list[int | None] | None = None, item_keys: list[str] | None = None) -> None:
        if res_type == "chests":
            self.current_stage_queue = list(found_item_ids)
            self.current_chest_queue = list(chest_ids) if chest_ids else [None] * len(found_item_ids)
            self.target_chest_index = None
            self.stageboss_chest_dropped_this_run = False
            
            self.stageboss_chest_queue = []
            self.normal_chest_queue = []
            
            if chest_ids and item_keys:
                for item_id, chest_id, item_key in zip(found_item_ids, chest_ids, item_keys):
                    chest_id_str = str(chest_id)
                    is_boss = chest_id_str.startswith("92") or chest_id_str.startswith("93")
                    drop_info = {
                        "item_id": item_id,
                        "chest_id": chest_id,
                        "item_key": item_key,
                        "is_unreachable": False
                    }
                    if is_boss:
                        self.stageboss_chest_queue.append(drop_info)
                    else:
                        self.normal_chest_queue.append(drop_info)
            else:
                for item_id in found_item_ids:
                    self.stageboss_chest_queue.append({"item_id": item_id, "chest_id": None, "is_unreachable": False})
            
            # Mark unreachable chests using Real-Time Residual Cooldown Extrapolation
            total_normal = len(self.normal_chest_queue)
            
            boss_cd = 420
            norm_cd = 240
            try:
                boss_cd = int(self.boss_cooldown_var.get())
                norm_cd = int(self.normal_cooldown_var.get())
            except:
                pass
                
            now = time.time()
            last_norm = getattr(self, "last_normal_drop_time", None) or now
            last_boss = getattr(self, "last_boss_drop_time", None) or now
            
            # Stage ends when the last normal chest drops (+ small 60s buffer for completion/save write)
            stage_end_time = last_norm + (total_normal * norm_cd) + 60
            
            for idx, item in enumerate(self.stageboss_chest_queue):
                # Target drop time for this specific boss chest index
                target_drop_time = last_boss + ((idx + 1) * boss_cd)
                if target_drop_time > stage_end_time:
                    item["is_unreachable"] = True
                    # Only log unreachable status if we are actually using real extrapolated data (not just fallback 'now')
                    if getattr(self, "last_boss_drop_time", None):
                        diff_boss = int((target_drop_time - now)/60)
                        diff_stage = int((stage_end_time - now)/60)
                        self.append_log(f"[PROXY] Boss Chest #{idx+1} marked UNREACHABLE (Extrapolated Drop: ~{diff_boss}m > Stage End: ~{diff_stage}m).\n")
                    
            # Build unified timeline sorted by drop time (240s for Normal, 420s for StageBoss)
            unified = []
            for i, item in enumerate(self.normal_chest_queue):
                unified.append({
                    "time": 240 * (i + 1),
                    "is_normal": True,
                    "orig_idx": i,
                    "item_id": item["item_id"],
                    "item_info": item
                })
            for j, item in enumerate(self.stageboss_chest_queue):
                unified.append({
                    "time": 420 * (j + 1),
                    "is_normal": False,
                    "orig_idx": j,
                    "item_id": item["item_id"],
                    "item_info": item
                })
            self.unified_timeline = sorted(unified, key=lambda x: x["time"])
            
            # Reset baselines for the new scan/run
            self.initial_use_list = None
            self.collected_run_cids = set()
            self.boss_chests_in_slots = 0
            

            
            self.after(0, self.update_loot_progress_ui)
        # Check if any target item is present (independent of relogger_active)
        target_found = False
        found_target_id = None
        if item_indices is None:
            item_indices = [1] * len(found_item_ids)
        for item_id, index in zip(found_item_ids, item_indices):
            if item_id in getattr(self, "ignored_items", []):
                continue
                
            # 1. Check specific item targets
            if item_id in self.target_items:
                # Reachability Check
                is_unreachable = False
                for idx, item in enumerate(self.stageboss_chest_queue):
                    if item["item_id"] == item_id and item.get("is_unreachable", False):
                        is_unreachable = True
                        break
                if is_unreachable:
                    self.append_log(f"[RELOGGER] Target item ID {item_id} found, but it is UNREACHABLE. Skipping...\n")
                    continue
                target_found = True
                found_target_id = item_id
                break
                
            # 2. Check grade targets
            if index > self.max_chest_index:
                continue
            info = self.get_item_info_by_id(item_id)
            if info:
                grade = info.get("grade", "COMMON").upper()
                if grade in self.target_grades:
                    name = self.get_item_name(info, "").lower()
                    if "soulstone" in name or "soul stone" in name:
                        continue
                    # Reachability Check
                    is_unreachable = False
                    for idx, item in enumerate(self.stageboss_chest_queue):
                        if item["item_id"] == item_id and item.get("is_unreachable", False):
                            is_unreachable = True
                            break
                    if is_unreachable:
                        self.append_log(f"[RELOGGER] Target grade item '{name}' is UNREACHABLE. Skipping...\n")
                        continue
                    target_found = True
                    found_target_id = item_id
                    break
        # Always update the Upcoming Important Drops cards on every scan
        self.update_upcoming_drops(found_item_ids, found_target_id if target_found else None, chest_ids)
        if target_found:
            info = self.get_item_info_by_id(found_target_id) or {}
            name = self.get_item_name(info, "Unknown")
            grade = info.get("grade", "COMMON")
            self.dashboard_targets_found += 1
            self.dashboard_last_activity = f"Target matched: {name}"
            # Update the alert banner
            self.update_dashboard_alert(name, grade, item_id=found_target_id)
            self.update_dashboard_stats()
            # Send Discord Notification if enabled
            self.notify_discord_match(found_target_id, name, grade, res_type)
            # Play alert sound in a separate thread so it doesn't freeze the GUI
            def play_alert():
                if winsound:
                    for _ in range(3):
                        winsound.Beep(1200, 300)
                        time.sleep(0.1)
            threading.Thread(target=play_alert, daemon=True).start()
            # Auto-launch trainer if enabled
            if self.trainer_auto_launch and self.trainer_path:
                trainer_exe = Path(self.trainer_path)
                if trainer_exe.exists():
                    try:
                        # Start trainer with --auto argument (requires Administrator)
                        ctypes.windll.shell32.ShellExecuteW(
                            None, "runas", str(trainer_exe), "--auto", str(trainer_exe.parent), 1
                        )
                        self.append_log(f"[AUTO] Target item found! Launching trainer as Admin: {trainer_exe}\n")
                    except Exception as e:
                        self.append_log(f"[ERROR] Failed to launch trainer: {e}\n")
                else:
                    self.append_log(f"[ERROR] Trainer not found at path: {trainer_exe}\n")
                    
            # Stage Switcher Pause logic
            if getattr(self, "switcher_active", False) and not getattr(self, "switcher_paused_for_drop", False):
                self.start_switcher_paused_countdown()
            
            # Auto-Relogger specific actions
            if self.relogger_active:
                if res_type == "chests":
                    # Calculate dynamic cooldown (queue-aware)
                    wait_duration = self.pause_duration
                    try:
                        # Find in StageBoss queue first
                        target_idx = None
                        is_boss_q = False
                        for idx, item in enumerate(self.stageboss_chest_queue):
                            if item["item_id"] == found_target_id:
                                target_idx = idx
                                is_boss_q = True
                                break
                        if target_idx is None:
                            # Search in Normal queue
                            for idx, item in enumerate(self.normal_chest_queue):
                                if item["item_id"] == found_target_id:
                                    target_idx = idx
                                    is_boss_q = False
                                    break
                                    
                        if target_idx is not None:
                            self.target_chest_index = target_idx + 1
                            cooldown = self.rare_chest_cooldown if is_boss_q else self.uncommon_chest_cooldown
                            estimated_secs = (target_idx + 1) * cooldown + 120
                            wait_duration = max(self.pause_duration, estimated_secs)
                        else:
                            self.target_chest_index = None
                    except Exception:
                        self.target_chest_index = None
                    self.append_log(f"[RELOGGER] TARGET ITEM FOUND in upcoming chests: {name} (ID: {found_target_id})!\n")
                    if self.target_chest_index is not None:
                        self.append_log(f"[RELOGGER] Target is at index #{self.target_chest_index} of sequence. Estimating wait time: {wait_duration // 60}m {wait_duration % 60}s ({wait_duration}s).\n")
                    else:
                        self.append_log(f"[RELOGGER] Pausing automatic re-entry to let the game clear the stage and collect it. Will relaunch in {wait_duration} seconds.\n")
                    # Start the paused countdown timer
                    self.start_paused_countdown(wait_duration, name)
                else:
                    # target collected (res_type is direct or synthesis), restart to search next target!
                    self.append_log(f"[RELOGGER] TARGET ITEM COLLECTED: {name} (ID: {found_target_id}) via {res_type.upper()}!\n")
                    # Cancel any pending paused countdown from a previous chest detection
                    if hasattr(self, 'paused_countdown_id') and self.paused_countdown_id:
                        try:
                            self.after_cancel(self.paused_countdown_id)
                        except Exception:
                            pass
                        self.paused_countdown_id = None
                    # Play quick alert sound
                    def play_collect_alert():
                        if winsound:
                            for _ in range(2):
                                winsound.Beep(1600, 200)
                                time.sleep(0.05)
                    threading.Thread(play_collect_alert, daemon=True).start()
                    # Wait safety delay before relogging to prevent server rollback
                    if self.relog_safety_delay > 0:
                        self.append_log(f"[RELOGGER] Waiting {self.relog_safety_delay}s anti-rollback safety delay before re-entry...\n")
                        self.start_paused_countdown(self.relog_safety_delay, f"{name} (collected, anti-rollback)")
                    else:
                        self.append_log("[RELOGGER] Initiating immediate re-entry (safety delay = 0)...\n")
                        self.lbl_bot_status.configure(
                            text="Relogger Status: ACTIVE (Logging stages...)\n[F9] to EMERGENCY STOP at any time",
                            text_color="#00FF00"
                        )
                        if not self.reentry_in_progress:
                            self.reentry_in_progress = True
                            threading.Thread(target=self.run_reentry_clicks, daemon=True).start()
        else:
            # If no target found, reset/clear the alert banner so it reflects the current scan
            self.set_dashboard_alert("Alert: No active alerts.", "info")
            # Relogger specific actions when no target is found
            if self.relogger_active:
                # If a paused countdown is already active (we found a target in chests
                # and are waiting to collect), do NOT cancel it
                if hasattr(self, 'paused_countdown_id') and self.paused_countdown_id:
                    return
                self.lbl_bot_status.configure(
                    text="Relogger Status: ACTIVE (Logging stages...)\n[F9] to EMERGENCY STOP at any time",
                    text_color="#00FF00"
                )
                if self.reentry_in_progress:
                    return
                self.reentry_in_progress = True
                self.append_log("[RELOGGER] Target item not found in drops. Initiating automatic re-entry...\n")
                threading.Thread(target=self.run_reentry_clicks, daemon=True).start()