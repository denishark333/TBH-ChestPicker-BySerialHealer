import os
import time
import json
import threading
from typing import Any
import re

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

class SaveParserMixin:
    def on_save_path_typed(self, event: Any) -> None:
        self.save_file_path = self.entry_save_path.get().strip()
        self.save_peeker_config()
        self.initialize_save_tracking()

    def browse_save_path(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select SaveFile_Live.es3",
            filetypes=[("ES3 Save Files", "*.es3"), ("All Files", "*.*")]
        )
        if path:
            self.save_file_path = os.path.normpath(path)
            self.entry_save_path.delete(0, "end")
            self.entry_save_path.insert(0, self.save_file_path)
            self.save_peeker_config()
            self.append_log(f"[CONFIG] Save file path updated to: {self.save_file_path}\n")
            self.initialize_save_tracking()

    def decrypt_es3_file(self, file_path: str, password: str) -> dict | None:
        import time
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        for attempt in range(5):
            try:
                if not os.path.exists(file_path):
                    return None
                with open(file_path, "rb") as f:
                    data = f.read()
                if len(data) < 32:
                    return None
                iv = data[:16]
                ciphertext = data[16:]
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA1(),
                    length=16,
                    salt=iv,
                    iterations=100,
                    backend=default_backend()
                )
                key = kdf.derive(password.encode('utf-8'))
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
                decryptor = cipher.decryptor()
                decrypted_bytes = decryptor.update(ciphertext) + decryptor.finalize()
                pad_len = decrypted_bytes[-1]
                if 1 <= pad_len <= 16:
                    decrypted_bytes = decrypted_bytes[:-pad_len]
                decrypted_text = decrypted_bytes.decode('utf-8', errors='ignore')
                return json.loads(decrypted_text)
            except PermissionError:
                # File is locked, wait 100ms and retry
                time.sleep(0.1)
                continue
            except Exception as e:
                self.log_gui_error(f"Error decrypting save file: {e}")
                return None
        return None

    def initialize_save_tracking(self) -> None:
        self.seen_get_chest_ids = set()
        self.seen_use_chest_ids = set()
        self.chest_id_to_drop_map = {}
        self.boss_chests_in_slots = 0
        self.boss_chest_dropped_this_run = False
        self.last_stage_wave = 0
        self.unified_timeline = []
        self.initial_use_list = None
        self.collected_run_cids = set()
        self.expected_items_from_chests = set()
        self.seen_inventory_item_ids = set()
        self.stageboss_chest_queue = []
        self.normal_chest_queue = []
        self.stageboss_progress_widgets = []
        self.normal_progress_widgets = []
        self.stageboss_chest_dropped_this_run = False
        self.last_save_mtime = 0
        if hasattr(self, 'save_file_path') and self.save_file_path and os.path.exists(self.save_file_path):
            try:
                save_data = self.decrypt_es3_file(self.save_file_path, "emuMqG3bLYJ938ZDCfieWJ")
                if save_data:
                    player_save_str = save_data.get("PlayerSaveData", {}).get("value", "")
                    if player_save_str:
                        player_data = json.loads(player_save_str)
                        get_list = player_data.get("BoxBucketGetBoxList", [])
                        use_list = player_data.get("BoxBucketUseBoxList", [])
                        items = player_data.get("itemSaveDatas", [])
                        for cid in get_list:
                            self.seen_get_chest_ids.add(str(cid))
                        for cid in use_list:
                            self.seen_use_chest_ids.add(str(cid))
                        for item in items:
                            uid = item.get("UniqueId")
                            if uid:
                                self.seen_inventory_item_ids.add(str(uid))
                        self.last_save_mtime = os.path.getmtime(self.save_file_path)
                        self.append_log(f"[SAVE WATCH] Tracking initialized. Seen Get: {len(self.seen_get_chest_ids)}, Use: {len(self.seen_use_chest_ids)} chests, Items: {len(self.seen_inventory_item_ids)}.\n")
            except Exception as e:
                self.append_log(f"[SAVE WATCH] Initialization failed: {e}\n")

    def update_widget_collected(self, w) -> None:
        w["lbl_status"].configure(text="[✔️]", text_color="#2ecc71")
        w["lbl_name"].configure(text_color="#7f8c8d")
        w["card"].configure(border_width=1, border_color="#2c3e50")

    def update_widget_dropped(self, w) -> None:
        w["lbl_status"].configure(text="[📦]", text_color=COLOR_PRIMARY)
        w["lbl_name"].configure(text_color=w.get("color", COLOR_TEXT))
        w["card"].configure(border_width=1, border_color=COLOR_PRIMARY)

    def update_widget_pending(self, w) -> None:
        w["lbl_status"].configure(text="[  ]", text_color=COLOR_MUTED)
        w["lbl_name"].configure(text_color=w.get("color", COLOR_TEXT))
        w["card"].configure(border_width=0)

    def start_save_watcher(self) -> None:
        self.initialize_save_tracking()
        def watcher_loop():
            while getattr(self, "running", True):
                time.sleep(0.5)
                if not self.save_file_path or not os.path.exists(self.save_file_path):
                    continue
                try:
                    mtime = os.path.getmtime(self.save_file_path)
                    if mtime != self.last_save_mtime:
                        save_data = self.decrypt_es3_file(self.save_file_path, "emuMqG3bLYJ938ZDCfieWJ")
                        if not save_data:
                            self.last_save_mtime = mtime
                            continue
                            
                        player_save_str = save_data.get("PlayerSaveData", {}).get("value", "")
                        if not player_save_str:
                            self.last_save_mtime = mtime
                            continue
                            
                        player_data = json.loads(player_save_str)
                        get_list = [str(cid) for cid in player_data.get("BoxBucketGetBoxList", [])]
                        use_list = [str(cid) for cid in player_data.get("BoxBucketUseBoxList", [])]
                        items = player_data.get("itemSaveDatas", [])
                        
                        # Account/character switch recovery
                        new_chests_count = len([cid for cid in get_list if cid not in self.seen_get_chest_ids])
                        new_items_count = len([item.get("UniqueId") for item in items if str(item.get("UniqueId")) not in self.seen_inventory_item_ids])
                        if new_chests_count > 3 or new_items_count > 10:
                            self.after(0, self.initialize_save_tracking)
                            self.last_save_mtime = mtime
                            continue
                            
                        # Update seen sets to prevent false account switch recovery triggering
                        self.seen_get_chest_ids.update(get_list)
                        self.seen_use_chest_ids.update(use_list)
                            
                        # Reset drop flags on stage/wave restarts (Do NOT reset baseline to preserve historical checks)
                        wave = player_data.get("commonSaveData", {}).get("currentStageWave", 0)
                        if wave == 0 and getattr(self, "last_stage_wave", 0) > 0:
                            self.boss_chest_dropped_this_run = False
                        self.last_stage_wave = wave
                        # Initialize run baselines if not already set
                        if self.initial_use_list is None:
                            self.initial_use_list = set(use_list)
                            self.collected_run_cids = set()
                            self.chest_id_to_type_map = {}
                            self.append_log(f"[SAVE WATCH] Baseline set: {len(get_list)} in slots, {len(self.initial_use_list)} opened.\n")
                            self.last_save_mtime = mtime
                            continue
                            
                        # Calculate active and opened chest IDs for the current session (not filtered by get_list baseline)
                        current_run_get = list(get_list)
                        current_run_use = [cid for cid in use_list if cid not in self.initial_use_list]
                        current_run_all = list(set(current_run_get + current_run_use))
                        
                        # Build mapping from Queue items to their generated cids using perfect suffix matching (Primary Key mapping)
                        boss_cids = []
                        for item in self.stageboss_chest_queue:
                            item_key_str = str(item.get("item_key", ""))
                            matched_cid = None
                            for cid in current_run_all:
                                if item_key_str.endswith(str(cid)):
                                    matched_cid = cid
                                    break
                            if matched_cid:
                                boss_cids.append(matched_cid)
                                
                        normal_cids = []
                        for item in self.normal_chest_queue:
                            item_key_str = str(item.get("item_key", ""))
                            matched_cid = None
                            for cid in current_run_all:
                                if item_key_str.endswith(str(cid)):
                                    matched_cid = cid
                                    break
                            if matched_cid:
                                normal_cids.append(matched_cid)
                        
                        # Real-time residual cooldown tracking
                        if not hasattr(self, "tracked_timestamp_boss_cids"): self.tracked_timestamp_boss_cids = set()
                        if not hasattr(self, "tracked_timestamp_normal_cids"): self.tracked_timestamp_normal_cids = set()
                        
                        new_boss_chests = [cid for cid in boss_cids if cid not in self.tracked_timestamp_boss_cids]
                        if new_boss_chests:
                            self.last_boss_drop_time = time.time()
                            self.tracked_timestamp_boss_cids.update(new_boss_chests)
                            
                        new_normal_chests = [cid for cid in normal_cids if cid not in self.tracked_timestamp_normal_cids]
                        if new_normal_chests:
                            self.last_normal_drop_time = time.time()
                            self.tracked_timestamp_normal_cids.update(new_normal_chests)
                        
                        expected_items_from_chests = set()
                        
                        # 1. Update StageBoss Column (Direct Key-to-CID mapping)
                        for idx, item in enumerate(self.stageboss_chest_queue):
                            widgets_ref = self.stageboss_progress_widgets
                            item_key_str = str(item.get("item_key", ""))
                            cid = None
                            for run_cid in current_run_all:
                                if item_key_str.endswith(str(run_cid)):
                                    cid = run_cid
                                    break
                                    
                            if cid is not None:
                                is_opened = cid in current_run_use
                                if is_opened:
                                    self.after(0, lambda w=widgets_ref[idx]: self.update_widget_collected(w))
                                    if cid not in self.collected_run_cids:
                                        self.collected_run_cids.add(cid)
                                        expected_items_from_chests.add(item["item_id"])
                                        
                                        info = self.get_item_info_by_id(item["item_id"]) or {}
                                        name = self.get_item_name(info, f"Item ({item['item_id']})")
                                        self.append_log(f"[SAVE] 🔓 Collected: {name} (StageBoss Chest ...{cid[-6:]})\n")
                                        
                                        if item["item_id"] in self.target_items:
                                            self.append_log(f"[SAVE WATCH] 🎯 TARGET ITEM COLLECTED! Relog safety delay activating...\n")
                                            if self.relogger_active:
                                                self.skip_to_safety_relog()
                                            elif getattr(self, "switcher_active", False) and getattr(self, "switcher_paused_for_drop", False):
                                                self.skip_to_switcher_safety_resume()
                                            if getattr(self, "cleaner_active", False):
                                                self.append_log("[SAVE WATCH] Target Found! Applying 15-minute cooldown to Auto-Stash...\n")
                                                self.cleaner_timeout_until = __import__("time").time() + 900
                                else:
                                    self.after(0, lambda w=widgets_ref[idx]: self.update_widget_dropped(w))
                            else:
                                self.after(0, lambda w=widgets_ref[idx]: self.update_widget_pending(w))
                                
                        # 2. Update Normal Column (Direct Key-to-CID mapping)
                        for idx, item in enumerate(self.normal_chest_queue):
                            widgets_ref = self.normal_progress_widgets
                            item_key_str = str(item.get("item_key", ""))
                            cid = None
                            for run_cid in current_run_all:
                                if item_key_str.endswith(str(run_cid)):
                                    cid = run_cid
                                    break
                                    
                            if cid is not None:
                                is_opened = cid in current_run_use
                                if is_opened:
                                    self.after(0, lambda w=widgets_ref[idx]: self.update_widget_collected(w))
                                    if cid not in self.collected_run_cids:
                                        self.collected_run_cids.add(cid)
                                        expected_items_from_chests.add(item["item_id"])
                                        
                                        info = self.get_item_info_by_id(item["item_id"]) or {}
                                        name = self.get_item_name(info, f"Item ({item['item_id']})")
                                        self.append_log(f"[SAVE] 🔓 Collected: {name} (Normal Chest ...{cid[-6:]})\n")
                                        
                                        if item["item_id"] in self.target_items:
                                            self.append_log(f"[SAVE WATCH] 🎯 TARGET ITEM COLLECTED! Relog safety delay activating...\n")
                                            if self.relogger_active:
                                                self.skip_to_safety_relog()
                                            elif getattr(self, "switcher_active", False) and getattr(self, "switcher_paused_for_drop", False):
                                                self.skip_to_switcher_safety_resume()
                                            if getattr(self, "cleaner_active", False):
                                                self.append_log("[SAVE WATCH] Target Found! Applying 15-minute cooldown to Auto-Stash...\n")
                                                self.cleaner_timeout_until = __import__("time").time() + 900
                                else:
                                    self.after(0, lambda w=widgets_ref[idx]: self.update_widget_dropped(w))
                            else:
                                self.after(0, lambda w=widgets_ref[idx]: self.update_widget_pending(w))
                                
                        # Check for direct inventory additions
                        new_items = []
                        for item in items:
                            uid = item.get("UniqueId")
                            if uid:
                                uid_str = str(uid)
                                if uid_str not in self.seen_inventory_item_ids:
                                    self.seen_inventory_item_ids.add(uid_str)
                                    item_key = item.get("ItemKey")
                                    if item_key:
                                        if not str(item_key).startswith(("91", "92", "93")):
                                            new_items.append(item_key)
                                            
                        # Log direct acquisitions (Cube, offering, etc.)
                        for k in new_items:
                            if k in expected_items_from_chests:
                                expected_items_from_chests.remove(k)
                            else:
                                self.after(0, lambda item_key=k: self.handle_direct_item_acquired(item_key))
                                
                        self.last_save_mtime = mtime
                except Exception as e:
                    self.append_log(f"[SAVE WATCH] Loop error: {e}\n")
                    
        import threading
        t = threading.Thread(target=watcher_loop, daemon=True)
        t.start()
    def handle_direct_item_acquired(self, item_key: int) -> None:
        info = self.get_item_info_by_id(item_key) or {}
        name = self.get_item_name(info, f"Item ({item_key})")
        self.append_log(f"[SAVE] 👑 Obtained: {name} (Direct/Synthesis/Offering)\n")
        
        if getattr(self, "target_items", []) and item_key in self.target_items:
            self.append_log(f"[SAVE WATCH] 🎯 TARGET ITEM SYNTHESIZED! Suspending tasks...\n")
            if getattr(self, "switcher_active", False):
                self.stop_switcher()
            if getattr(self, "relogger_active", False):
                self.stop_relogger()
            if getattr(self, "cleaner_active", False):
                self.append_log("[SAVE WATCH] Target Found! Applying 15-minute cooldown to Auto-Stash...\n")
                self.cleaner_timeout_until = __import__("time").time() + 900
            if hasattr(self, 'play_alert'):
                self.play_alert()






