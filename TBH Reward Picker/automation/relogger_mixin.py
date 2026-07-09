import os
import sys
import time
import threading
import subprocess
import pygetwindow as gw
import random
import ctypes
try:
    import winsound
except ImportError:
    winsound = None


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

class ReloggerMixin:
    def toggle_relogger(self) -> None:
        if self.relogger_active:
            self.stop_relogger("Stopped by User")
        else:
            self.start_relogger()

    def start_relogger(self) -> None:
        if self.relogger_method == "mouse_clicks":
            # Check coordinates calibration
            missing = [k for k, v in self.coords.items() if v is None]
            if missing:
                missing_labels = {
                    "menu": "Menu Button",
                    "exit": "Back to Title Button",
                    "stage_icon": "Tap to Start Button",
                    "confirm_enter": "Enter Stage Button"
                }
                labels_str = ", ".join(missing_labels[k] for k in missing)
                self.append_log(f"[ERROR] Cannot start relogger. Please calibrate: {labels_str}\n")
                return
        else:
            # Check game path exists
            if not self.game_path or not os.path.exists(self.game_path):
                self.append_log(f"[ERROR] Cannot start relogger. TaskbarHero.exe not found at path: {self.game_path}\n")
                return
        if not self.proxy_running:
            self.append_log("[ERROR] Please start the Peeker Proxy before running the relogger.\n")
            return
        self.relogger_active = True
        self.btn_bot.configure(text="Stop Auto-Relogger", fg_color=COLOR_PRIMARY, hover_color=COLOR_HOVER)
        self.lbl_bot_status.configure(
            text="Relogger Status: ACTIVE (Logging stages...)\n[F9] to EMERGENCY STOP at any time",
            text_color="#00FF00"
        )
        self.append_log(f"[RELOGGER] Auto-Relogger enabled ({'Process Restart' if self.relogger_method == 'process_restart' else 'Mouse Clicks'}). Checking upcoming drops...\n")
        if self.relogger_method == "process_restart":
            self.last_launch_time = 0
            self.watchdog_token += 1
            threading.Thread(target=self.relogger_watchdog_loop, args=(self.watchdog_token,), daemon=True).start()
        # Evaluate last loaded drops immediately if they exist
        if self.last_found_item_ids:
            self.append_log("[RELOGGER] Evaluating currently loaded stage drops immediately...\n")
            self.evaluate_filters_and_relog(
                self.last_found_item_ids, 
                self.last_found_res_type, 
                self.last_found_item_indices,
                getattr(self, 'last_found_chest_ids', None)
            )

    def stop_relogger(self, reason: str = "") -> None:
        self.relogger_active = False
        self.last_found_item_ids = []
        self.last_found_item_indices = []
        self.last_found_chest_ids = []
        self.last_found_res_type = "chests"
        self.reentry_in_progress = False
        # Cancel countdown if active
        if hasattr(self, 'paused_countdown_id') and self.paused_countdown_id:
            try:
                self.after_cancel(self.paused_countdown_id)
            except Exception:
                pass
            self.paused_countdown_id = None
        # Hide the collected button
        self.btn_item_collected.pack_forget()
        self.btn_bot.configure(text="Start Auto-Relogger", fg_color="#2ecc71", hover_color="#27ae60")
        self.lbl_bot_status.configure(
            text="Relogger Status: Inactive\n[F9] to EMERGENCY STOP at any time",
            text_color=COLOR_MUTED
        )
        reason_str = f" ({reason})" if reason else ""
        self.append_log(f"[RELOGGER] Auto-Relogger disabled{reason_str}.\n")
        if winsound:
            winsound.Beep(400, 250)

    def skip_to_safety_relog(self) -> None:
        """User clicked 'Item Collected' — cancel long countdown, apply safety delay, then relog."""
        self.append_log("[RELOGGER] User confirmed item collected!\n")
        # Cancel the long countdown
        if hasattr(self, 'paused_countdown_id') and self.paused_countdown_id:
            try:
                self.after_cancel(self.paused_countdown_id)
            except Exception:
                pass
            self.paused_countdown_id = None
        # Hide the collected button
        self.btn_item_collected.pack_forget()
        # Apply safety delay before relogging
        if self.relog_safety_delay > 0:
            self.safety_countdown_active = True
            self.append_log(f"[RELOGGER] Waiting {self.relog_safety_delay}s anti-rollback safety delay before re-entry...\n")
            self.start_paused_countdown(self.relog_safety_delay, "Anti-rollback safety delay")
        else:
            self.append_log("[RELOGGER] Safety delay = 0, relogging immediately...\n")
            self.force_relaunch_game()

    def force_relaunch_game(self) -> None:
        self.append_log("[RELOGGER] Force Relaunch requested by user...\n")
        self.last_found_item_ids = []
        self.last_found_item_indices = []
        self.last_found_chest_ids = []
        self.last_found_res_type = "chests"
        self.reentry_in_progress = False
        # Cancel countdown if active
        if hasattr(self, 'paused_countdown_id') and self.paused_countdown_id:
            try:
                self.after_cancel(self.paused_countdown_id)
            except Exception:
                pass
            self.paused_countdown_id = None
        # Hide the collected button
        self.btn_item_collected.pack_forget()
        self.safety_countdown_active = False
        if self.relogger_active:
            self.lbl_bot_status.configure(
                text="Relogger Status: ACTIVE (Logging stages...)\n[F9] to EMERGENCY STOP at any time",
                text_color="#00FF00"
            )
        # Kill the game process and trainer
        self.append_log("[RELOGGER] Terminating TaskbarHero.exe...\n")
        try:
            subprocess.run(
                ["taskkill", "/f", "/im", "TaskBarHero.exe"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self._kill_trainer_elevated()
        except Exception as e:
            self.append_log(f"[ERROR] Failed to kill process: {e}\n")
        self.last_launch_time = 0
        # If relogger is not active, launch the game manually
        if not self.relogger_active:
            try:
                if "steam" in self.game_path.lower():
                    self.append_log("[RELOGGER] Launching via Steam protocol natively...\n")
                    os.startfile("steam://run/3678970")
                else:
                    self.append_log(f"[RELOGGER] Launching game from path: {self.game_path}...\n")
                    os.startfile(self.game_path)
            except Exception as e:
                self.append_log(f"[ERROR] Failed to launch game: {e}\n")

    def start_paused_countdown(self, seconds_left: int, item_name: str) -> None:
        # Cancel any existing countdown first
        if hasattr(self, 'paused_countdown_id') and self.paused_countdown_id:
            try:
                self.after_cancel(self.paused_countdown_id)
            except Exception:
                pass
            self.paused_countdown_id = None
        if not self.relogger_active:
            return
        if seconds_left <= 0:
            self.append_log(f"[RELOGGER] Countdown finished. Auto-relaunching game now...\n")
            self.btn_item_collected.pack_forget()
            self.force_relaunch_game()
            return
        # Show the "Item Collected" button so user can skip the long countdown
        # (only during the main wait, not during safety countdown)
        if not self.safety_countdown_active:
            try:
                self.btn_item_collected.pack_forget()
                self.btn_item_collected.pack(fill="x", padx=15, pady=(0, 8), before=self.lbl_bot_status)
            except Exception:
                pass
        hours = seconds_left // 3600
        minutes = (seconds_left % 3600) // 60
        secs = seconds_left % 60
        time_str = f"{hours:02d}:{minutes:02d}:{secs:02d}"
        
        self.lbl_bot_status.configure(
            text=f"Relogger Status: ACTIVE (PAUSED - Found {item_name})\nRelaunching game in {time_str}...",
            text_color="#f1c40f"
        )
        # Schedule the next tick
        self.paused_countdown_id = self.after(
            1000, 
            lambda: self.start_paused_countdown(seconds_left - 1, item_name)
        )

    def _kill_trainer_elevated(self) -> None:
        """Kill TBH Trainer.exe even when it runs as Admin."""
        try:
            p = subprocess.run(
                ["tasklist", "/fi", "imagename eq TBH Trainer.exe", "/fo", "csv", "/nh"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in p.stdout.strip().split('\n'):
                if 'TBH Trainer' in line:
                    pid = int(line.split(',')[1].strip('"'))
                    PROCESS_TERMINATE = 0x0001
                    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
                    if handle:
                        ctypes.windll.kernel32.TerminateProcess(handle, 1)
                        ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            pass

    def run_reentry_clicks(self) -> None:
        """Fires simulated mouse clicks or restarts process to exit and re-enter stage."""
        try:
            if self.relogger_method == "process_restart":
                # Add a randomized delay before killing the game to simulate human reaction
                import random
                pre_kill_delay = random.uniform(2.0, 4.0)
                time.sleep(pre_kill_delay)
                if not self.relogger_active: return
                 # 1. Kill TaskbarHero.exe and TBH Trainer.exe
                self.append_log("[RELOGGER] Terminating TaskbarHero.exe...\n")
                try:
                    subprocess.run(
                        ["taskkill", "/f", "/im", "TaskBarHero.exe"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    self._kill_trainer_elevated()
                except Exception as e:
                    self.append_log(f"[WARNING] Failed to kill process: {e}\n")
                # Clear cached drops so they are not evaluated on next startup
                self.last_found_item_ids = []
                self.last_found_item_indices = []
                self.last_found_chest_ids = []
                self.last_found_res_type = "chests"
                # Add a randomized cooldown delay before launching again to avoid bot pattern detection
                post_kill_delay = random.uniform(4.0, 8.0)
                self.append_log(f"[RELOGGER] Safety cooldown of {post_kill_delay:.1f}s before next launch...\n")
                self.last_launch_time = time.time() - (20.0 - post_kill_delay)
            else:
                # 1. Wait for game loading / stable screen
                time.sleep(1.2)
                if not self.relogger_active: return
                # 2. Click Menu Button
                self.append_log("[RELOGGER] Clicking Menu...\n")
                self.click_coordinate("menu")
                time.sleep(0.6)
                if not self.relogger_active: return
                # 3. Click Back to Title / Logout
                self.append_log("[RELOGGER] Clicking Back to Title...\n")
                self.click_coordinate("exit")
                # Wait for game to return to title screen (takes longer)
                time.sleep(3.0)
                if not self.relogger_active: return
                # 4. Click Tap to Start / Login
                self.append_log("[RELOGGER] Clicking Tap to Start / Login...\n")
                self.click_coordinate("stage_icon")
                # Wait for game to load main screen / world map
                time.sleep(4.0)
                if not self.relogger_active: return
                # 5. Click Enter Stage
                self.append_log("[RELOGGER] Clicking Enter Stage...\n")
                self.click_coordinate("confirm_enter")
                self.append_log("[RELOGGER] Waiting for stage load...\n")
        finally:
            self.reentry_in_progress = False

    def relogger_watchdog_loop(self, token: int) -> None:
        """Watchdog loop to ensure the game is always running when the relogger is active."""
        self.append_log("[RELOGGER] Watchdog loop started.\n")
        while self.relogger_active and self.watchdog_token == token and self.relogger_method == "process_restart":
            # Check if game is running
            running = False
            try:
                p = subprocess.run(
                    ["tasklist", "/fi", "imagename eq TaskBarHero.exe"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                running = "taskbarhero.exe" in p.stdout.lower()
            except Exception:
                pass
            if not running:
                current_time = time.time()
                # Only launch if we haven't launched in the last 20 seconds to allow Steam to load
                if current_time - self.last_launch_time > 20.0:
                    self.append_log("[WATCHDOG] Game is not running. Launching TaskbarHero...\n")
                    try:
                        if "steam" in self.game_path.lower():
                            self.append_log("[WATCHDOG] Steam path detected. Launching via Steam protocol natively (AppID 3678970)...\n")
                            os.startfile("steam://run/3678970")
                        else:
                            os.startfile(self.game_path)
                        self.last_launch_time = current_time
                    except Exception as e:
                        self.append_log(f"[WATCHDOG] Failed to launch game: {e}\n")
            time.sleep(3.0)