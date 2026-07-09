import time
import threading
import pyautogui
import ctypes

class InventoryCleanerMixin:
    """Mixin for the Inventory Cleaner / Auto-Synthesis automation."""

    
    def toggle_cleaner(self):
        if not self.cleaner_active:
            # Check if clicks are set
            valid_clicks = [c for c in self.cleaner_clicks if c[0] is not None and c[1] is not None]
            if not valid_clicks:
                self.append_log("[CLEANER] Please configure at least one click coordinate (F10) before starting.\n")
                return
            
            try:
                self.cleaner_interval = int(self.entry_cleaner_interval.get())
                if hasattr(self, "save_peeker_config"):
                    self.save_peeker_config()
            except ValueError:
                self.append_log("[CLEANER] Invalid interval value. Using default 600s.\n")
                self.cleaner_interval = 600
                
            self.cleaner_active = True
            self.btn_toggle_cleaner.configure(text="Stop Inventory Cleaner", fg_color="#e74c3c", hover_color="#c0392b")
            self.append_log(f"[CLEANER] Started! Will click every {self.cleaner_interval} seconds.\n")
            
            # Start background thread
            threading.Thread(target=self.cleaner_loop, daemon=True).start()
        else:
            self.cleaner_active = False
            self.btn_toggle_cleaner.configure(text="Start Inventory Cleaner", fg_color="#27ae60", hover_color="#2ecc71")
            self.append_log("[CLEANER] Stopped.\n")

    def cleaner_loop(self):
        while self.cleaner_active:
            for _ in range(self.cleaner_interval):
                if not self.cleaner_active:
                    return
                time.sleep(1)
            
            if not self.cleaner_active:
                return
                
            # Check for Target Drop Cooldown
            timeout_until = getattr(self, "cleaner_timeout_until", 0)
            if time.time() < timeout_until:
                remaining = int(timeout_until - time.time())
                self.append_log(f"[CLEANER] Auto-Stash paused due to Target Drop. Resuming in {remaining}s...\n")
                while time.time() < getattr(self, "cleaner_timeout_until", 0):
                    if not self.cleaner_active:
                        return
                    time.sleep(1)
            
            self.append_log("[CLEANER] Running scheduled inventory cleanup...\n")
            
            valid_clicks = [c for c in self.cleaner_clicks if c[0] is not None and c[1] is not None]
            if valid_clicks:
                with getattr(self, "mouse_lock", threading.Lock()):
                    for (x, y) in valid_clicks:
                        if not self.cleaner_active:
                            break
                        pyautogui.click(x=x, y=y)
                        time.sleep(0.6)

    def trigger_cleaner_calibration(self, idx: int):
        if getattr(self, "macro_mouse_listener", None) and self.macro_mouse_listener.running:
            self.append_log("[CLEANER] Calibration already in progress.\n")
            return
            
        self.calibrating_cleaner_idx = idx
        self.append_log(f"[CLEANER] Calibrating Click {idx + 1}. Left Click to save point, Right Click to Cancel.\n")
        
        def on_click(x, y, button, pressed):
            if pressed:
                if button == __import__("pynput").mouse.Button.left:
                    self.cleaner_clicks[idx] = (int(x), int(y))
                    self.calibrating_cleaner_idx = None
                    if hasattr(self, "save_peeker_config"):
                        self.save_peeker_config()
                    if hasattr(self, "lbl_cleaner_cal_status"):
                        self.lbl_cleaner_cal_status.configure(text=f"Click {idx+1} Set: ({int(x)}, {int(y)})", text_color="#2ecc71")
                    self.append_log(f"[CLEANER] Calibrated Click {idx+1} to coordinates: {int(x)}, {int(y)}\n")
                    try:
                        __import__("winsound").Beep(700, 200)
                    except:
                        pass
                    return False
                elif button == __import__("pynput").mouse.Button.right:
                    self.calibrating_cleaner_idx = None
                    self.append_log(f"[CLEANER] Calibration Canceled.\n")
                    return False
                    
        def listener_thread():
            with __import__("pynput").mouse.Listener(on_click=on_click) as listener:
                self.macro_mouse_listener = listener
                listener.join()
                
        __import__("threading").Thread(target=listener_thread, daemon=True).start()







