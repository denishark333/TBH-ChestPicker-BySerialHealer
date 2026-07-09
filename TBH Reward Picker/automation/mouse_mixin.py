import time
import threading
from pynput import mouse, keyboard
import pyautogui
import ctypes
try:
    import winsound
except ImportError:
    winsound = None

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


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

class MouseMixin:
    def calibrate_stage(self, stage_idx):
        if self.macro_mouse_listener and self.macro_mouse_listener.running:
            self.append_log("[SWITCHER] Calibration already in progress.\n")
            return
            
        btn = self.btn_calib_1 if stage_idx == 1 else self.btn_calib_2
        btn.configure(text="Recording... (Right Click to Stop)", fg_color="#e74c3c", hover_color="#c0392b")
        self.append_log(f"[SWITCHER] Calibrating Stage {stage_idx}. Left click to save points, Right click to finish.\n")
        
        clicks = []
        
        def on_click(x, y, button, pressed):
            if pressed:
                if button == mouse.Button.left:
                    clicks.append((int(x), int(y)))
                    self.append_log(f"[SWITCHER] Point saved: ({int(x)}, {int(y)})\n")
                elif button == mouse.Button.right:
                    return False # Stop listener
                    
        def listener_thread():
            with mouse.Listener(on_click=on_click) as listener:
                self.macro_mouse_listener = listener
                listener.join()
            
            # Update state
            if stage_idx == 1:
                self.stage_1_clicks = clicks
                text = f"Stage 1: {len(clicks)} clicks saved"
                self.lbl_calib_1_status.configure(text=text)
            else:
                self.stage_2_clicks = clicks
                text = f"Stage 2: {len(clicks)} clicks saved"
                self.lbl_calib_2_status.configure(text=text)
                
            self.after(0, lambda: btn.configure(text=f"Calibrate Stage {stage_idx}", fg_color=COLOR_PRIMARY, hover_color=COLOR_HOVER))
            self.append_log(f"[SWITCHER] Calibration finished for Stage {stage_idx}. {len(clicks)} points saved.\n")
            self.save_peeker_config()

        threading.Thread(target=listener_thread, daemon=True).start()

    def start_calibration(self, key: str) -> None:
        self.calibrating_key = key
        label_map = {
            "menu": "Menu Button",
            "exit": "Back to Title Button",
            "stage_icon": "Tap to Start Button",
            "confirm_enter": "Enter Stage Button"
        }
        self.lbl_cal_status.configure(
            text=f"CALIBRATING: Hover over '{label_map[key]}' and press [F8] key!",
            text_color="#e74c3c"
        )
        # Play tiny beep to confirm mode start
        if winsound:
            winsound.Beep(600, 150)

    def check_hotkeys(self) -> None:
        # Check F8 Calibration key (VK code: 0x77)
        if self.calibrating_key:
            # Check if F8 is pressed
            if (ctypes.windll.user32.GetAsyncKeyState(0x77) & 0x8000) != 0:
                pt = POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                self.coords[self.calibrating_key] = [pt.x, pt.y]
                self.calibrating_key = None
                self.save_peeker_config()
                self.update_cal_labels()
                self.lbl_cal_status.configure(text_color=COLOR_MUTED)
                self.append_log(f"[CALIB] Calibrated {self.calibrating_key} to coordinates: {pt.x}, {pt.y}\n")
                if winsound:
                    winsound.Beep(1000, 250)
                # Debounce: wait until key released
                while (ctypes.windll.user32.GetAsyncKeyState(0x77) & 0x8000) != 0:
                    time.sleep(0.05)
        # Check F9 Emergency Stop key (VK code: 0x78)
        if hasattr(self, 'relogger_active') and self.relogger_active:
            if (ctypes.windll.user32.GetAsyncKeyState(0x78) & 0x8000) != 0:
                self.stop_relogger("EMERGENCY STOP (F9 Pressed)")
                while (ctypes.windll.user32.GetAsyncKeyState(0x78) & 0x8000) != 0:
                    time.sleep(0.05)
        
        self.after(50, self.check_hotkeys)

    def click_coordinate(self, key: str) -> None:
        pos = self.coords.get(key)
        if not pos:
            return
        x, y = pos[0], pos[1]
        
        import threading
        with getattr(self, 'mouse_lock', threading.Lock()):
            # Set cursor and left mouse click down/up
            ctypes.windll.user32.SetCursorPos(x, y)
            time.sleep(0.02)
            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0) # mouse left down
            time.sleep(0.05)
            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)

