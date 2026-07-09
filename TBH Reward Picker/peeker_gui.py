import os
import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from typing import Any
import re
import urllib.request
import urllib.parse
import base64
import ctypes

import customtkinter as ctk
from tkinter import filedialog
from PIL import Image

try:
    from pynput import mouse, keyboard
except ImportError:
    pass

try:
    import pyautogui
except ImportError:
    pass

try:
    import pygetwindow as gw
except ImportError:
    pass

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    pass

# Import the extracted mixins
from core.config_mixin import ConfigMixin
from core.database_mixin import DatabaseMixin
from core.save_parser_mixin import SaveParserMixin
from network.steam_mixin import SteamMixin
from network.discord_mixin import DiscordMixin
from network.proxy_mixin import ProxyMixin
from automation.switcher_mixin import SwitcherMixin
from automation.mouse_mixin import MouseMixin
from automation.relogger_mixin import ReloggerMixin
from automation.inventory_cleaner_mixin import InventoryCleanerMixin
from gui.gui_mixin import GuiMixin

ROOT = Path(__file__).parent.resolve()

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class PeekerGUI(ctk.CTk, ConfigMixin, DatabaseMixin, SaveParserMixin, 
                SteamMixin, DiscordMixin, ProxyMixin, 
                SwitcherMixin, MouseMixin, ReloggerMixin, InventoryCleanerMixin, GuiMixin):
    
    def __init__(self) -> None:
        super().__init__()
        
        self.title("TBH Reward Picker 2.5.6 - By SerialHealer")
        self.geometry("1100x650")
        self.minsize(1000, 600)
        self.mouse_lock = threading.Lock()
        
        # Initialize basic state
        self.items_db = []
        self.target_items = []
        self.ignored_items = []
        self.target_grades = []
        self.relogger_method = "process_restart"
        self.cleaner_active = False
        self.cleaner_clicks = [(None, None), (None, None), (None, None)]
        self.calibrating_cleaner_idx = None
        self.game_path = r"C:\Program Files (x86)\Steam\steamapps\common\TaskbarHero\TaskBarHero.exe"
        self.pause_duration = 110
        self.relog_safety_delay = 45
        self.coords = {}
        self.discord_notify_enabled = False
        self.discord_webhook_url = ""
        self.discord_user_id = ""
        
        # State for tabs
        self.save_file_path = ""
        self.save_watcher_thread = None
        self.stop_save_watcher = False
        self.last_save_mtime = 0
        
        # Stage Switcher state
        self.stage_switcher_active = False
        self.switcher_interval = 20
        self.stage_1_clicks = []
        self.stage_2_clicks = []
        self.stage_switcher_thread = None
        self.stage_switcher_paused = False
        
        # Unreachable calculation state
        self.rare_chest_cooldown = 420
        self.uncommon_chest_cooldown = 240
        
        # Load state
        self.last_found_item_ids = []
        self.last_found_item_indices = []
        self.last_found_chest_ids = []
        self.last_found_res_type = "chests"
        self.paused_countdown_id = None
        self.trainer_auto_launch = False
        self.trainer_path = str(ROOT / "TBH Trainer.exe")
        self.max_chest_index = 43
        self.last_save_use_list_len = -1
        self.running = True
        self.switcher_active = False
        self.current_switcher_stage = 1
        self.switcher_paused_for_drop = False
        self.switcher_last_action_time = 0.0
        self.macro_mouse_listener = None
        self.seen_get_chest_ids = set()
        self.seen_use_chest_ids = set()
        self.chest_id_to_drop_map = {}
        self.boss_chests_in_slots = 0
        self.boss_chest_dropped_this_run = False
        self.last_stage_wave = 0
        self.unified_timeline = []
        self.initial_use_list = None
        self.collected_run_cids = set()
        self.seen_inventory_item_ids = set()
        self.stageboss_chest_queue = []
        self.normal_chest_queue = []
        self.stageboss_progress_widgets = []
        self.normal_progress_widgets = []
        self.stageboss_chest_dropped_this_run = False
        self.dashboard_scans_done = 0
        self.dashboard_loots_observed = 0
        self.dashboard_targets_found = 0
        self.dashboard_last_activity = "N/A"
        self.sprite_mapping = {}
        self.market_price_cache = {}
        self.proxy_running = False
        self.calibrating_key = None
        self.watchdog_token = 0
        self.reentry_in_progress = False
        self.safety_countdown_active = False
        self.consecutive_errors = 0
        self.last_launch_time = 0
        self.current_stage_queue = []
        self.current_chest_queue = []
        self.target_chest_index = -1
        
        self.load_items_db()
        self.load_peeker_config()
        self.load_market_cache()
        self.load_or_build_sprite_mapping()
        
        # Proxy state
        self.proxy_process = None
        self.proxy_thread = None
        self.stop_proxy_flag = False
        
        # Relogger state
        self.relogger_active = False
        self.relogger_thread = None
        self.relogger_watchdog_thread = None
        self.stop_relogger_flag = False
        self.cancel_pause_flag = False
        
        # Build UI
        self.create_widgets()
        
        # Start Save Watcher
        if self.save_file_path:
            self.start_save_watcher()
            
    def on_closing(self) -> None:
        self.save_peeker_config()
        self.save_market_cache()
        if self.proxy_process:
            self.stop_proxy()
        self.stop_relogger_flag = True
        self.cancel_pause_flag = True
        self.stage_switcher_active = False
        self.stop_save_watcher = True
        self.destroy()

if __name__ == "__main__":
    app = PeekerGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


