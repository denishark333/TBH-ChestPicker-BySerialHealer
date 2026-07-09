import time
import threading
from pathlib import Path
import pyautogui


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

class SwitcherMixin:
    def toggle_stage_switcher(self):
        if getattr(self, "macro_is_running", False):
            self.append_log("[SWITCHER] Cannot start Stage Switcher while Auto-Relogger is active.\n")
            return
            
        if not self.switcher_active:
            if not self.stage_1_clicks or not self.stage_2_clicks:
                messagebox.showerror("Error", "Please calibrate both Stage 1 and Stage 2 clicks in Settings first.")
                return
            
            try:
                self.switcher_interval = int(self.entry_switcher_interval.get())
            except ValueError:
                self.switcher_interval = 20
                self.entry_switcher_interval.delete(0, 'end')
                self.entry_switcher_interval.insert(0, "20")
                
            self.switcher_active = True
            self.current_switcher_stage = 1
            self.switcher_paused_for_drop = False
            self.switcher_last_action_time = 0.0
            self.btn_toggle_switcher.configure(text="STOP STAGE SWITCHER", fg_color="#e74c3c", hover_color="#c0392b")
            if hasattr(self, "btn_bot"): self.btn_bot.configure(state="disabled")
            self.append_log(f"[SWITCHER] Started Stage Switcher mode. Interval: {self.switcher_interval}s.\n")
            self.stage_switcher_tick()
        else:
            self.switcher_active = False
            self.switcher_paused_for_drop = False
            self.btn_toggle_switcher.configure(text="START STAGE SWITCHER", fg_color="#2ecc71", hover_color="#27ae60")
            if hasattr(self, "btn_bot"): self.btn_bot.configure(state="normal")
            self.lbl_switcher_status.configure(text="Status: Stopped")
            self.append_log("[SWITCHER] Stopped.\n")

    def stage_switcher_tick(self):
        if not getattr(self, "switcher_active", False):
            return
            
        if self.switcher_paused_for_drop:
            self.lbl_switcher_status.configure(text="Status: Target Found! Paused.")
            self.after(1000, self.stage_switcher_tick)
            return
            
        now = time.time()
        elapsed = now - self.switcher_last_action_time
        
        if elapsed >= self.switcher_interval:
            # Time to act
            self.execute_stage_macro(self.current_switcher_stage)
            self.switcher_last_action_time = time.time()
            # Toggle for next time
            self.current_switcher_stage = 2 if self.current_switcher_stage == 1 else 1
            elapsed = 0
            
        remaining = int(self.switcher_interval - elapsed)
        self.lbl_switcher_status.configure(text=f"Status: Waiting {remaining}s (Next: Stage {self.current_switcher_stage})")
        self.after(1000, self.stage_switcher_tick)

    def start_switcher_paused_countdown(self):
        if not getattr(self, "switcher_active", False):
            return
            
        self.append_log(f"[SWITCHER] Target item detected! Paused indefinitely until capture.\\n")
        self.switcher_paused_for_drop = True
        self.lbl_switcher_status.configure(text="Status: Paused (Waiting for capture)")
        
        # Show manual resume button
        try:
            self.btn_switcher_item_collected.pack_forget()
            self.btn_switcher_item_collected.pack(fill="x", padx=10, pady=(0, 6), before=self.lbl_switcher_status)
        except Exception:
            pass

    def skip_to_switcher_safety_resume(self):
        self.append_log("[SWITCHER] Target item collected! Activating safety delay before resume...\\n")
        try:
            self.btn_switcher_item_collected.pack_forget()
        except Exception:
            pass
        self.start_switcher_safety_countdown(self.relog_safety_delay)

    def start_switcher_safety_countdown(self, seconds_left: int):
        if not getattr(self, "switcher_active", False):
            return
            
        if seconds_left <= 0:
            self.append_log(f"[SWITCHER] Safety delay finished. Resuming Stage Switcher!\n")
            self.switcher_paused_for_drop = False
            self.switcher_last_action_time = time.time()  # Reset timer so it waits full interval before clicking
            return
            
        self.lbl_switcher_status.configure(text=f"Status: Target Found! Paused (Resuming in {seconds_left}s)")
        self.after(1000, self.start_switcher_safety_countdown, seconds_left - 1)

    def execute_stage_macro(self, stage_idx):
        clicks = self.stage_1_clicks if stage_idx == 1 else self.stage_2_clicks
        self.append_log(f"[SWITCHER] Executing Stage {stage_idx} macro ({len(clicks)} clicks)...\n")
        
        def macro_thread():
            for (x, y) in clicks:
                if not self.switcher_active:
                    break
                with getattr(self, 'mouse_lock', threading.Lock()):
                    pyautogui.click(x=x, y=y)
                time.sleep(0.6)
                
        threading.Thread(target=macro_thread, daemon=True).start()
