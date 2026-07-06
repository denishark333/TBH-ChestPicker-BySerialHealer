from __future__ import annotations
 
import json
import os
import re
import sys
import time
import shutil
import subprocess
import threading
import warnings
import ctypes
from pathlib import Path
from typing import Any
 
# Silence deprecation and user warnings to keep the console clean
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
 
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from PIL import Image

from telegram_notifier import TelegramNotifier
 
# Import winsound on Windows for alerts
try:
    import winsound
except ImportError:
    winsound = None
 
# =====================================================================
# Constants & Colors (Matching tbh_reward_hook.py style)
# =====================================================================
COLOR_BG = "#0b0b0b"          # Deep charcoal background
COLOR_FRAME = "#141414"       # Dark panel surface
COLOR_PRIMARY = "#c8a24b"     # Soft muted gold accent
COLOR_HOVER = "#f2c94c"       # Lighter gold hover
COLOR_SECONDARY = "#1d1d1d"   # Charcoal card background
COLOR_SEC_HOVER = "#2a2a2a"   # Lighter charcoal hover
COLOR_TEXT = "#e8e8e8"        # Light text for the dashboard
COLOR_MUTED = "#b8b8b8"       # Softer muted text
COLOR_ENTRY_BG = "#111111"    # Dark entry background
COLOR_BORDER = "#2f2f2f"      # Soft border color
 
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
    "BOSS": "#00a8ff",          # Bright blue/cyan for Stage Boss Box
    "SOULSTONE": "#e74c3c"      # Red/crimson for Soulstone card
}
 
ROOT = Path(__file__).resolve().parent
PEEKER_CONFIG_PATH = ROOT / "peeker_config.json"
ITEMS_PATH = ROOT / "items.json"
ADDON_PATH = ROOT / "chest_peeker.py"
 
# Windows POINT structure for mouse positioning
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
 
# =====================================================================
# GUI Application Class
# =====================================================================
class PeekerGUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
 
        self.title("TBH Picker - Auto Relogger")
        self.geometry("1100x780")
        self.minsize(960, 640)
        self.configure(fg_color=COLOR_BG)
        ctk.set_appearance_mode("dark")
 
        # Load Items database
        self.items_db: list[dict[str, Any]] = []
        self.load_items_db()
 
        # State configurations
        self.coords = {
            "menu": None,
            "exit": None,
            "stage_icon": None,
            "confirm_enter": None
        }
        self.target_items: list[int] = []
        self.ignored_items: list[int] = []
        self.target_grades: list[str] = ["BEYOND", "IMMORTAL", "ARCANA", "CELESTIAL", "DIVINE", "COSMIC"]
        self.relogger_method = "process_restart"
        self.game_path = r"C:\Program Files (x86)\Steam\steamapps\common\TaskbarHero\TaskBarHero.exe"
        self.last_found_item_ids: list[int] = []
        self.last_found_item_indices: list[int] = []
        self.last_found_chest_ids: list[int | None] = []
        self.last_found_res_type: str = "chests"
        self.pause_duration = 110
        self.paused_countdown_id = None
        self.discord_notify_enabled = False
        self.discord_webhook_url = ""
        self.discord_user_id = ""
        self.telegram_notify_enabled = False
        self.telegram_bot_token = ""
        self.telegram_chat_id = ""
        self.trainer_auto_launch = False
        self.trainer_path = str(ROOT / "TBH Trainer.exe")
        self.relog_safety_delay = 45  # seconds to wait after collecting item before relogging (anti-rollback)
        self.max_chest_index = 43  # default max chest index to match grade filters
        self.rare_chest_cooldown = 420  # StageBoss chest cooldown (s)
        self.uncommon_chest_cooldown = 240  # Normal chest cooldown (s)
        self.dashboard_scans_done = 0
        self.dashboard_loots_observed = 0
        self.dashboard_targets_found = 0
        self.dashboard_last_activity = "Ready"
        self.sprite_mapping = {}
        self.load_peeker_config()
        self.market_price_cache = {}
        self.load_market_cache()
 
        # Execution state
        self.proxy_process: subprocess.Popen | None = None
        self.proxy_running = False
        self.relogger_active = False
        self.calibrating_key = None
        self.watchdog_token = 0
        self.reentry_in_progress = False
        self.safety_countdown_active = False
        self.consecutive_errors = 0
        self.last_launch_time = 0
        self.current_stage_queue = []
        self.current_chest_queue = []
        self.target_chest_index = None
        self.load_or_build_sprite_mapping()
        
        # Build UI
        self.create_widgets()
        
        # Bind close protocol handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start state check loop (hotkeys and logs)
        self.after(50, self.check_hotkeys)
        self.after(100, self.start_proxy) # Auto-start proxy on startup!
        self.append_log("[INFO] Peeker GUI loaded. Ready.\n")
 
    # =====================================================================
    # Config & Database Loading
    # =====================================================================
    def load_items_db(self) -> None:
        if ITEMS_PATH.exists():
            try:
                with open(ITEMS_PATH, "r", encoding="utf-8") as f:
                    self.items_db = json.load(f)
            except Exception as e:
                print(f"Error loading items.json: {e}")
        
    def load_peeker_config(self) -> None:
        if PEEKER_CONFIG_PATH.exists():
            try:
                data = json.loads(PEEKER_CONFIG_PATH.read_text(encoding="utf-8-sig"))
                self.coords = data.get("coords", self.coords)
                self.target_items = data.get("target_items", [])
                self.ignored_items = data.get("ignored_items", [])
                self.target_grades = data.get("target_grades", self.target_grades)
                self.relogger_method = data.get("relogger_method", "process_restart")
                self.game_path = data.get("game_path", r"C:\Program Files (x86)\Steam\steamapps\common\TaskbarHero\TaskBarHero.exe")
                self.pause_duration = data.get("pause_duration", 110)
                self.discord_notify_enabled = data.get("discord_notify_enabled", False)
                self.discord_webhook_url = data.get("discord_webhook_url", "")
                self.discord_user_id = data.get("discord_user_id", "")
                self.telegram_notify_enabled = data.get("telegram_notify_enabled", False)
                self.telegram_bot_token = data.get("telegram_bot_token", "")
                self.telegram_chat_id = data.get("telegram_chat_id", "")
                self.trainer_auto_launch = data.get("trainer_auto_launch", False)
                self.trainer_path = data.get("trainer_path", str(ROOT / "TBH Trainer.exe"))
                self.relog_safety_delay = data.get("relog_safety_delay", 45)
                self.max_chest_index = data.get("max_chest_index", 43)
                self.rare_chest_cooldown = data.get("rare_chest_cooldown", 420)
                self.uncommon_chest_cooldown = data.get("uncommon_chest_cooldown", 240)
            except Exception:
                pass
 
    def save_peeker_config(self) -> None:
        try:
            data = {
                "coords": self.coords,
                "target_items": self.target_items,
                "ignored_items": self.ignored_items,
                "target_grades": self.target_grades,
                "relogger_method": self.relogger_method,
                "game_path": self.game_path,
                "pause_duration": self.pause_duration,
                "discord_notify_enabled": self.discord_notify_enabled,
                "discord_webhook_url": self.discord_webhook_url,
                "discord_user_id": self.discord_user_id,
                "telegram_notify_enabled": self.telegram_notify_enabled,
                "telegram_bot_token": self.telegram_bot_token,
                "telegram_chat_id": self.telegram_chat_id,
                "trainer_auto_launch": self.trainer_auto_launch,
                "trainer_path": self.trainer_path,
                "relog_safety_delay": self.relog_safety_delay,
                "max_chest_index": self.max_chest_index,
                "rare_chest_cooldown": self.rare_chest_cooldown,
                "uncommon_chest_cooldown": self.uncommon_chest_cooldown
            }
            PEEKER_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            self.append_log(f"[ERROR] Failed to save config: {e}\n")

    def load_market_cache(self) -> None:
        """Carrega o cache de preÃ§os do arquivo local."""
        self.market_price_cache = {}
        cache_path = ROOT / "market_cache.json"
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    self.market_price_cache = json.load(f)
            except Exception:
                pass

    def save_market_cache(self) -> None:
        """Salva o cache de preÃ§os no arquivo local."""
        cache_path = ROOT / "market_cache.json"
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(self.market_price_cache, f, indent=2)
        except Exception:
            pass

    def fetch_steam_market_price(self, item_name: str, callback) -> None:
        """Busca o preÃ§o do item, respeitando o cooldown incondicional de 12 horas."""
        now = time.time()
        max_cache_age = 12 * 3600  # 12 horas em segundos
        
        # Se o item jÃ¡ foi consultado (com sucesso, erro ou indisponÃ­vel) dentro de 12h, 
        # usa a resposta do cache de forma incondicional.
        if item_name in self.market_price_cache:
            item_data = self.market_price_cache[item_name]
            cached_time = item_data.get("timestamp", 0)
            cached_price = item_data.get("price", "N/A")
            
            if now - cached_time < max_cache_age:
                callback(cached_price)
                return

        # Caso contrÃ¡rio, dispara a thread para consultar a Steam
        def worker():
            import urllib.request
            import urllib.parse
            import json
            
            price_str = "N/A"
            try:
                encoded_name = urllib.parse.quote(item_name)
                url = f"https://steamcommunity.com/market/priceoverview/?appid=3678970&currency=7&market_hash_name={encoded_name}"
                
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )
                with urllib.request.urlopen(req, timeout=6) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get("success"):
                        price_str = data.get("lowest_price", data.get("median_price", "N/A"))
            except Exception:
                price_str = "N/A"
            
            # Salva o resultado (preÃ§o real ou N/A) no cache com o timestamp atual
            self.market_price_cache[item_name] = {
                "price": price_str,
                "timestamp": now
            }
            self.save_market_cache()
            
            self.after(0, lambda: callback(price_str))

        threading.Thread(target=worker, daemon=True).start()
 
    # =====================================================================
    # UI Layout & Construction
    # =====================================================================
    def create_widgets(self) -> None:
        # Title Header
        self.title_label = ctk.CTkLabel(
            self,
            text="TBH Picker - Auto Relogger",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        self.title_label.pack(pady=(20, 2), padx=20, anchor="w")
 
        self.subtitle_label = ctk.CTkLabel(
            self,
            text="Peeks at stage rewards and automates re-entry until target items are found.",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=COLOR_MUTED
        )
        self.subtitle_label.pack(pady=(0, 15), padx=20, anchor="w")
 
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self.main_container, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1, width=220)
        self.sidebar.pack(side="left", fill="y", padx=(0, 12))
        self.sidebar.pack_propagate(False)

        self.sidebar_title = ctk.CTkLabel(self.sidebar, text="Navigation", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        self.sidebar_title.pack(anchor="w", padx=16, pady=(16, 12))

        self.sidebar_buttons = {}
        for name in ["Dashboard", "Targets & Alerts", "Settings", "Console Log"]:
            btn = ctk.CTkButton(
                self.sidebar,
                text=name,
                fg_color="transparent",
                hover_color=COLOR_SECONDARY,
                border_width=1,
                border_color=COLOR_BORDER,
                height=38,
                command=lambda n=name: self.show_tab(n)
            )
            btn.pack(fill="x", padx=12, pady=(0, 8))
            self.sidebar_buttons[name] = btn

        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_area.pack(side="left", fill="both", expand=True)

        self.tab_frames = {}
        self.tab_dashboard = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.tab_targets = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.tab_settings = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.tab_console = ctk.CTkFrame(self.content_area, fg_color="transparent")

        self.tab_frames["Dashboard"] = self.tab_dashboard
        self.tab_frames["Targets & Alerts"] = self.tab_targets
        self.tab_frames["Settings"] = self.tab_settings
        self.tab_frames["Console Log"] = self.tab_console

        for frame in self.tab_frames.values():
            frame.pack(fill="both", expand=True)
            frame.pack_forget()

        # Proxy Controller inside Sidebar (at the bottom)
        self.proxy_frame = ctk.CTkFrame(self.sidebar, fg_color=COLOR_SECONDARY, border_color=COLOR_BORDER, border_width=1)
        self.proxy_frame.pack(side="bottom", fill="x", padx=12, pady=12)
        
        lbl = ctk.CTkLabel(self.proxy_frame, text="Proxy Controller", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT)
        lbl.pack(anchor="w", padx=10, pady=(6, 8))
        
        self.btn_proxy = ctk.CTkButton(self.proxy_frame, text="Start Peeker Proxy", fg_color=COLOR_PRIMARY, hover_color=COLOR_HOVER, text_color=COLOR_TEXT, font=ctk.CTkFont(size=11, weight="bold"), command=self.toggle_proxy, height=32)
        self.btn_proxy.pack(fill="x", padx=10, pady=(0, 6))
        
        self.btn_trust_cert = ctk.CTkButton(self.proxy_frame, text="Trust CA Certificate", fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER, text_color=COLOR_TEXT, font=ctk.CTkFont(size=10, weight="bold"), command=self.install_cert_automatically, height=24)
        self.btn_trust_cert.pack(fill="x", padx=10, pady=(0, 6))
        
        self.lbl_proxy_status = ctk.CTkLabel(self.proxy_frame, text="Status: Stopped", text_color=COLOR_MUTED, font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_proxy_status.pack(anchor="w", padx=10, pady=(0, 6))

        self.build_dashboard_tab()
        self.build_targets_tab()
        self.build_settings_tab()
        self.build_console_tab()
        self.update_dashboard_stats()
        self.show_tab("Dashboard")
 
    def build_dashboard_tab(self) -> None:
        self.dashboard_scroll = ctk.CTkScrollableFrame(
            self.tab_dashboard,
            fg_color="transparent",
            scrollbar_button_color=COLOR_PRIMARY,
            scrollbar_button_hover_color=COLOR_HOVER
        )
        self.dashboard_scroll.pack(fill="both", expand=True, padx=12, pady=12)

        self.dashboard_content = ctk.CTkFrame(self.dashboard_scroll, fg_color="transparent")
        self.dashboard_content.pack(fill="both", expand=True)
        self.dashboard_content.grid_columnconfigure(0, weight=1)
        self.dashboard_content.grid_columnconfigure(1, weight=1)
        self.dashboard_content.grid_rowconfigure(0, weight=0)
        self.dashboard_content.grid_rowconfigure(1, weight=0)
        self.dashboard_content.grid_rowconfigure(2, weight=1)
        self.dashboard_content.grid_rowconfigure(3, weight=0)

        # Create placeholder PIL image and CTkImage to prevent layout shift
        self.placeholder_pil = Image.new("RGBA", (32, 32), (26, 26, 30, 255))
        self.placeholder_image = ctk.CTkImage(self.placeholder_pil, size=(32, 32))
        
        self.placeholder_chest_pil = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        self.placeholder_chest_image = ctk.CTkImage(self.placeholder_chest_pil, size=(16, 16))

        # Alert banner with dynamic height and icon container
        self.alert_banner = ctk.CTkFrame(self.dashboard_content, fg_color="#121212", border_color=COLOR_PRIMARY, border_width=1, height=75)
        self.alert_banner.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        self.alert_banner.pack_propagate(False)
        
        alert_content = ctk.CTkFrame(self.alert_banner, fg_color="transparent")
        alert_content.pack(expand=True, padx=20, pady=10)
        
        self.lbl_alert_icon = ctk.CTkLabel(alert_content, text="", width=32, height=32, fg_color="#1a1a1e", corner_radius=4, image=self.placeholder_image)
        self.lbl_alert_icon.pack(side="left", padx=(0, 12))
        self.lbl_alert_icon._my_image_ref = self.placeholder_image
        
        self.alert_banner_label = ctk.CTkLabel(alert_content, text="Alert: No active alerts.", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_MUTED, wraplength=600, justify="left", anchor="w")
        self.alert_banner_label.pack(side="left", fill="both", expand=True)

        self.upcoming_banner = ctk.CTkFrame(self.dashboard_content, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1, height=265)
        self.upcoming_banner.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        self.upcoming_banner.pack_propagate(False)
        
        ctk.CTkLabel(self.upcoming_banner, text="Upcoming Important Drops", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT).pack(anchor="w", padx=16, pady=(12, 8))
        self.upcoming_cards = ctk.CTkFrame(self.upcoming_banner, fg_color="transparent")
        self.upcoming_cards.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.upcoming_cards.grid_columnconfigure(0, weight=1)
        self.upcoming_cards.grid_columnconfigure(1, weight=1)
        self.upcoming_cards.grid_columnconfigure(2, weight=1)
        self.upcoming_cards.grid_rowconfigure(0, weight=1, minsize=90)
        self.upcoming_cards.grid_rowconfigure(1, weight=1, minsize=90)

        self.upcoming_card_vars = {}
        self.upcoming_card_widgets = {}
        for idx, rarity in enumerate(["IMMORTAL", "LEGENDARY", "RARE", "BEYOND", "ARCANA", "SOULSTONE"]):
            card = ctk.CTkFrame(self.upcoming_cards, fg_color="#161616", border_color=COLOR_BORDER, border_width=1)
            card.grid(row=idx // 3, column=idx % 3, sticky="nsew", padx=6, pady=6)
            color = GRADE_COLORS.get(rarity, COLOR_PRIMARY)
            card.configure(border_color=color)
            
            # Header
            ctk.CTkLabel(card, text=rarity, font=ctk.CTkFont(size=11, weight="bold"), text_color=color).pack(anchor="w", padx=10, pady=(6, 2))
            
            # Horizontal layout container
            content_frame = ctk.CTkFrame(card, fg_color="transparent")
            content_frame.pack(fill="both", expand=True, padx=8, pady=(2, 6))
            
            # Item Icon on the left
            lbl_item_icon = ctk.CTkLabel(content_frame, text="", width=32, height=32, fg_color="#1a1a1e", corner_radius=4, image=self.placeholder_image)
            lbl_item_icon.pack(side="left", padx=(0, 8), anchor="n")
            lbl_item_icon._my_image_ref = self.placeholder_image
            
            # Details column on the right
            details_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            details_frame.pack(side="left", fill="both", expand=True)
            
            # Sub-frame for name and price side-by-side
            name_price_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
            name_price_frame.pack(fill="x", anchor="w")

            lbl_name = ctk.CTkLabel(name_price_frame, text="No drop yet", font=ctk.CTkFont(family="Inter", size=15, weight="bold"), text_color=COLOR_TEXT, wraplength=120, justify="left", anchor="w")
            lbl_name.pack(side="left")

            lbl_price = ctk.CTkLabel(name_price_frame, text="", font=ctk.CTkFont(family="Inter", size=17, weight="bold"), text_color=COLOR_PRIMARY, justify="left", anchor="w")
            lbl_price.pack(side="left", padx=(6, 0))
            
            # Chest info row (hidden by default)
            chest_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
            chest_frame.pack(fill="x", anchor="w", pady=(2, 0))
            chest_frame.pack_forget()
            
            lbl_from = ctk.CTkLabel(chest_frame, text="In: ", font=ctk.CTkFont(size=9), text_color=COLOR_MUTED, anchor="w")
            lbl_from.pack(side="left")
            
            lbl_chest_icon = ctk.CTkLabel(chest_frame, text="", width=16, height=16, fg_color="transparent", image=self.placeholder_chest_image)
            lbl_chest_icon.pack(side="left", padx=(1, 4))
            lbl_chest_icon._my_image_ref = self.placeholder_chest_image
            
            lbl_chest_name = ctk.CTkLabel(chest_frame, text="", font=ctk.CTkFont(size=9, slant="italic"), text_color=COLOR_MUTED, anchor="w")
            lbl_chest_name.pack(side="left", fill="x", expand=True)
            
            # Save references
            self.upcoming_card_widgets[rarity] = {
                "card": card,
                "lbl_name": lbl_name,
                "lbl_price": lbl_price,
                "lbl_item_icon": lbl_item_icon,
                "chest_frame": chest_frame,
                "lbl_from": lbl_from,
                "lbl_chest_icon": lbl_chest_icon,
                "lbl_chest_name": lbl_chest_name
            }

        self.bot_frame = ctk.CTkFrame(self.dashboard_content, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.bot_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 8), pady=(8, 0))
        lbl_bot = ctk.CTkLabel(self.bot_frame, text="Auto-Relogger Controls", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl_bot.pack(anchor="w", padx=15, pady=(8, 10))
        self.btn_bot = ctk.CTkButton(self.bot_frame, text="Start Auto-Relogger", fg_color="#2ecc71", hover_color="#27ae60", text_color=COLOR_TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=self.toggle_relogger, height=36)
        self.btn_bot.pack(fill="x", padx=15, pady=(0, 8))
        self.btn_force_relaunch = ctk.CTkButton(self.bot_frame, text="Force Relaunch Game", fg_color="#3498db", hover_color="#2980b9", text_color=COLOR_TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=self.force_relaunch_game, height=36)
        self.btn_force_relaunch.pack(fill="x", padx=15, pady=(0, 8))
        self.btn_item_collected = ctk.CTkButton(self.bot_frame, text="âœ… Item Collected â†’ Relog Now", fg_color="#e67e22", hover_color="#d35400", text_color=COLOR_TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=self.skip_to_safety_relog, height=36)
        self.btn_item_collected.pack(fill="x", padx=15, pady=(0, 8))
        self.btn_item_collected.pack_forget()

        # Manual cooldown settings in Auto-Relogger Controls
        cooldowns_container = ctk.CTkFrame(self.bot_frame, fg_color="transparent")
        cooldowns_container.pack(fill="x", padx=15, pady=(8, 4))
        cooldowns_container.grid_columnconfigure(0, weight=1)
        cooldowns_container.grid_columnconfigure(1, weight=1)
        
        # StageBoss (Rare) Cooldown
        rare_col = ctk.CTkFrame(cooldowns_container, fg_color="transparent")
        rare_col.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkLabel(rare_col, text="StageBoss (Rare) Cooldown (s):", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_MUTED, anchor="w").pack(fill="x")
        self.entry_rare_cooldown = ctk.CTkEntry(rare_col, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT, font=ctk.CTkFont(size=11), height=24)
        self.entry_rare_cooldown.pack(fill="x", pady=(2, 0))
        self.entry_rare_cooldown.insert(0, str(self.rare_chest_cooldown))
        self.entry_rare_cooldown.bind("<KeyRelease>", self.on_rare_cooldown_typed)
        
        # Normal (Uncommon) Cooldown
        uncommon_col = ctk.CTkFrame(cooldowns_container, fg_color="transparent")
        uncommon_col.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        ctk.CTkLabel(uncommon_col, text="Normal (Uncommon) Cooldown (s):", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_MUTED, anchor="w").pack(fill="x")
        self.entry_uncommon_cooldown = ctk.CTkEntry(uncommon_col, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT, font=ctk.CTkFont(size=11), height=24)
        self.entry_uncommon_cooldown.pack(fill="x", pady=(2, 0))
        self.entry_uncommon_cooldown.insert(0, str(self.uncommon_chest_cooldown))
        self.entry_uncommon_cooldown.bind("<KeyRelease>", self.on_uncommon_cooldown_typed)

        self.lbl_bot_status = ctk.CTkLabel(self.bot_frame, text="Relogger Status: Inactive\n[F9] to EMERGENCY STOP at any time", text_color=COLOR_MUTED, font=ctk.CTkFont(size=11, weight="bold"), justify="left")
        self.lbl_bot_status.pack(anchor="w", padx=15, pady=(0, 8))

        self.telemetry_frame = ctk.CTkFrame(self.dashboard_content, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.telemetry_frame.grid(row=2, column=1, sticky="nsew", padx=(8, 0), pady=(8, 0))
        telemetry_title = ctk.CTkLabel(self.telemetry_frame, text="Session Telemetry", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        telemetry_title.pack(anchor="w", padx=15, pady=(10, 8))

        self.telemetry_grid = ctk.CTkFrame(self.telemetry_frame, fg_color="transparent")
        self.telemetry_grid.pack(fill="x", padx=15, pady=(0, 8))
        self.telemetry_grid.grid_columnconfigure(0, weight=1)
        self.telemetry_grid.grid_columnconfigure(1, weight=1)

        self.telemetry_scans_var = ctk.StringVar(value="0")
        self.telemetry_loots_var = ctk.StringVar(value="0")
        self.telemetry_targets_var = ctk.StringVar(value="0")
        self.telemetry_last_var = ctk.StringVar(value="Idle")

        self.telemetry_cards = []
        for idx, (label_text, var) in enumerate([("Scans", self.telemetry_scans_var), ("Loots", self.telemetry_loots_var), ("Targets", self.telemetry_targets_var), ("Last", self.telemetry_last_var)]):
            card = ctk.CTkFrame(self.telemetry_grid, fg_color="#181818", border_color=COLOR_BORDER, border_width=1)
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=4, pady=4)
            ctk.CTkLabel(card, text=label_text, font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED).pack(anchor="w", padx=10, pady=(8, 2))
            ctk.CTkLabel(card, textvariable=var, font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_TEXT).pack(anchor="w", padx=10, pady=(0, 8))
            self.telemetry_cards.append(card)

        self.next_drop_banner = ctk.CTkFrame(self.telemetry_frame, fg_color="#171717", border_color=COLOR_BORDER, border_width=1)
        self.next_drop_banner.pack(fill="x", padx=15, pady=(8, 12))
        ctk.CTkLabel(self.next_drop_banner, text="Next Valuable Drop", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT).pack(anchor="w", padx=10, pady=(8, 2))
        
        # Horizontal container for Next Valuable Drop details to prevent layout shift
        next_drop_content = ctk.CTkFrame(self.next_drop_banner, fg_color="transparent")
        next_drop_content.pack(fill="x", padx=10, pady=(0, 10))
        
        # Icon on the left
        self.lbl_next_drop_icon = ctk.CTkLabel(next_drop_content, text="", width=32, height=32, fg_color="#1a1a1e", corner_radius=4, image=self.placeholder_image)
        self.lbl_next_drop_icon.pack(side="left", padx=(0, 8), anchor="center")
        self.lbl_next_drop_icon._my_image_ref = self.placeholder_image
        
        self.next_drop_var = ctk.StringVar(value="Waiting for scan...")
        self.lbl_next_drop = ctk.CTkLabel(next_drop_content, textvariable=self.next_drop_var, font=ctk.CTkFont(family="Inter", size=15, weight="bold"), text_color=COLOR_MUTED, wraplength=200, justify="left", anchor="w")
        self.lbl_next_drop.pack(side="left")
        
        self.next_drop_price_var = ctk.StringVar(value="")
        self.lbl_next_drop_price = ctk.CTkLabel(next_drop_content, textvariable=self.next_drop_price_var, font=ctk.CTkFont(family="Inter", size=17, weight="bold"), text_color=COLOR_PRIMARY, justify="left", anchor="w")
        self.lbl_next_drop_price.pack(side="left", padx=(6, 0))

        footer = ctk.CTkLabel(self.dashboard_content, text="Powered by: SH", font=ctk.CTkFont(size=11), text_color=COLOR_MUTED)
        footer.grid(row=3, column=0, columnspan=2, sticky="s", pady=(12, 0))

    def build_targets_tab(self) -> None:
        self.targets_scroll = ctk.CTkScrollableFrame(
            self.tab_targets,
            fg_color="transparent",
            scrollbar_button_color=COLOR_PRIMARY,
            scrollbar_button_hover_color=COLOR_HOVER
        )
        self.targets_scroll.pack(fill="both", expand=True, padx=12, pady=12)

        # Themed container frame for targets to match dashboard layout
        self.targets_container = ctk.CTkFrame(
            self.targets_scroll,
            fg_color=COLOR_FRAME,
            border_color=COLOR_BORDER,
            border_width=1
        )
        self.targets_container.pack(fill="both", expand=True, padx=4, pady=4)

        # Title for the container
        lbl_title = ctk.CTkLabel(
            self.targets_container, 
            text="Targets & Alerts Configuration", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color=COLOR_TEXT
        )
        lbl_title.pack(anchor="w", padx=16, pady=(12, 4))

        self.filter_tabview = ctk.CTkTabview(
            self.targets_container,
            fg_color="transparent",  # Make transparent so it uses container's COLOR_FRAME
            segmented_button_selected_color=COLOR_PRIMARY,
            segmented_button_selected_hover_color=COLOR_HOVER,
            segmented_button_unselected_color=COLOR_SECONDARY,
            segmented_button_unselected_hover_color=COLOR_SEC_HOVER,
            text_color=COLOR_TEXT
        )
        self.filter_tabview.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.tab_items = self.filter_tabview.add("Item Targets")
        self.tab_grades = self.filter_tabview.add("Grade Targets")
        self.tab_notifications = self.filter_tabview.add("Notifications")

        self.build_item_filters_tab()
        self.build_grade_filters_tab()
        self.build_notifications_tab()

    def build_settings_tab(self) -> None:
        self.settings_scroll = ctk.CTkScrollableFrame(
            self.tab_settings,
            fg_color="transparent",
            scrollbar_button_color=COLOR_PRIMARY,
            scrollbar_button_hover_color=COLOR_HOVER
        )
        self.settings_scroll.pack(fill="both", expand=True, padx=12, pady=12)

        self.calib_frame = ctk.CTkFrame(self.settings_scroll, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.calib_frame.pack(fill="both", expand=True, padx=4, pady=4)

        lbl_cal = ctk.CTkLabel(self.calib_frame, text="Auto-Relogger Setup", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl_cal.pack(anchor="w", padx=15, pady=(8, 5))

        self.relogger_method_var = ctk.StringVar(value="Process Restart" if self.relogger_method == "process_restart" else "Mouse Clicks")
        self.seg_method = ctk.CTkSegmentedButton(
            self.calib_frame,
            values=["Process Restart", "Mouse Clicks"],
            variable=self.relogger_method_var,
            command=self.on_relogger_method_changed,
            selected_color=COLOR_PRIMARY,
            selected_hover_color=COLOR_HOVER,
            unselected_color=COLOR_SECONDARY,
            unselected_hover_color=COLOR_SEC_HOVER,
            text_color=COLOR_TEXT
        )
        self.seg_method.pack(fill="x", padx=15, pady=5)

        self.restart_container = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        lbl_path = ctk.CTkLabel(self.restart_container, text="TaskbarHero.exe Path:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED)
        lbl_path.pack(anchor="w", padx=0, pady=(5, 2))
        path_row = ctk.CTkFrame(self.restart_container, fg_color="transparent")
        path_row.pack(fill="x")
        self.entry_game_path = ctk.CTkEntry(
            path_row,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11)
        )
        self.entry_game_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_game_path.insert(0, self.game_path)
        self.entry_game_path.bind("<KeyRelease>", self.on_game_path_typed)
        self.btn_browse = ctk.CTkButton(
            path_row,
            text="Browse",
            width=60,
            height=28,
            fg_color=COLOR_SECONDARY,
            hover_color=COLOR_SEC_HOVER,
            command=self.browse_game_path
        )
        self.btn_browse.pack(side="right")

        self.clicks_container = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        lbl_inst = ctk.CTkLabel(
            self.clicks_container,
            text="Click a button below, hover over the game item, then press F8 to save.",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color=COLOR_MUTED,
            wraplength=350,
            justify="left"
        )
        lbl_inst.pack(anchor="w", padx=0, pady=(0, 5))

        grid = ctk.CTkFrame(self.clicks_container, fg_color="transparent")
        grid.pack(fill="x", pady=2)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        self.btn_cal_menu = ctk.CTkButton(grid, text="1. Menu Button", fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER, command=lambda: self.start_calibration("menu"), height=26)
        self.btn_cal_menu.grid(row=0, column=0, padx=(0, 3), pady=2, sticky="ew")
        self.btn_cal_exit = ctk.CTkButton(grid, text="2. Back to Title", fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER, command=lambda: self.start_calibration("exit"), height=26)
        self.btn_cal_exit.grid(row=0, column=1, padx=(3, 0), pady=2, sticky="ew")
        self.btn_cal_stage = ctk.CTkButton(grid, text="3. Tap to Start", fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER, command=lambda: self.start_calibration("stage_icon"), height=26)
        self.btn_cal_stage.grid(row=1, column=0, padx=(0, 3), pady=2, sticky="ew")
        self.btn_cal_confirm = ctk.CTkButton(grid, text="4. Enter Stage", fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER, command=lambda: self.start_calibration("confirm_enter"), height=26)
        self.btn_cal_confirm.grid(row=1, column=1, padx=(3, 0), pady=2, sticky="ew")

        self.lbl_cal_status = ctk.CTkLabel(self.clicks_container, text="", font=ctk.CTkFont(size=10), text_color=COLOR_MUTED, wraplength=350, justify="left")
        self.lbl_cal_status.pack(anchor="w", padx=0, pady=(2, 2))

        delay_row = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        delay_row.pack(fill="x", padx=15, pady=(5, 5))
        lbl_delay = ctk.CTkLabel(delay_row, text="Pause Delay (seconds):", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED)
        lbl_delay.pack(side="left", padx=(0, 10))
        self.entry_pause_delay = ctk.CTkEntry(delay_row, width=60, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT, font=ctk.CTkFont(size=11))
        self.entry_pause_delay.pack(side="left")
        self.entry_pause_delay.insert(0, str(self.pause_duration))
        self.entry_pause_delay.bind("<KeyRelease>", self.on_pause_delay_typed)

        safety_row = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        safety_row.pack(fill="x", padx=15, pady=(2, 5))
        lbl_safety = ctk.CTkLabel(safety_row, text="Anti-Rollback Delay (s):", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED)
        lbl_safety.pack(side="left", padx=(0, 10))
        self.entry_safety_delay = ctk.CTkEntry(safety_row, width=60, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT, font=ctk.CTkFont(size=11))
        self.entry_safety_delay.pack(side="left")
        self.entry_safety_delay.insert(0, str(self.relog_safety_delay))
        self.entry_safety_delay.bind("<KeyRelease>", self.on_safety_delay_typed)

        max_idx_row = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        max_idx_row.pack(fill="x", padx=15, pady=(2, 5))
        lbl_max_idx = ctk.CTkLabel(max_idx_row, text="Max Chest Index (Grade Match):", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED)
        lbl_max_idx.pack(side="left", padx=(0, 10))
        self.entry_max_chest_index = ctk.CTkEntry(max_idx_row, width=60, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT, font=ctk.CTkFont(size=11))
        self.entry_max_chest_index.pack(side="left")
        self.entry_max_chest_index.insert(0, str(self.max_chest_index))
        self.entry_max_chest_index.bind("<KeyRelease>", self.on_max_chest_index_typed)

        self.update_relogger_ui_visibility()

    def build_console_tab(self) -> None:
        self.console_frame = ctk.CTkFrame(self.tab_console, fg_color="transparent")
        self.console_frame.pack(fill="both", expand=True, padx=12, pady=12)

        self.feed_frame = ctk.CTkFrame(self.console_frame, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.feed_frame.pack(fill="both", expand=True)

        lbl = ctk.CTkLabel(self.feed_frame, text="Live Peek Feed", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT)
        lbl.pack(anchor="w", padx=15, pady=(10, 5))

        log_container = ctk.CTkFrame(self.feed_frame, fg_color=COLOR_BG, border_color=COLOR_BORDER, border_width=1)
        log_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.txt_log = tk.Text(
            log_container,
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            selectbackground=COLOR_PRIMARY,
            selectforeground=COLOR_TEXT,
            bd=0,
            highlightthickness=0,
            font=("Consolas", 9)
        )
        self.txt_log.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)

        scrollbar = ctk.CTkScrollbar(log_container, command=self.txt_log.yview, button_color=COLOR_PRIMARY, button_hover_color=COLOR_HOVER)
        scrollbar.pack(side="right", fill="y", padx=(5, 5), pady=10)
        self.txt_log.configure(yscrollcommand=scrollbar.set)

    def update_dashboard_stats(self) -> None:
        if hasattr(self, "telemetry_scans_var"):
            self.telemetry_scans_var.set(str(self.dashboard_scans_done))
        if hasattr(self, "telemetry_loots_var"):
            self.telemetry_loots_var.set(str(self.dashboard_loots_observed))
        if hasattr(self, "telemetry_targets_var"):
            self.telemetry_targets_var.set(str(self.dashboard_targets_found))
        if hasattr(self, "telemetry_last_var"):
            self.telemetry_last_var.set(self.dashboard_last_activity)

    def set_dashboard_alert(self, message: str, severity: str = "info") -> None:
        if not hasattr(self, "alert_banner_label"):
            return
        color_map = {
            "info": COLOR_MUTED,
            "warning": "#f39c12",
            "success": "#2ecc71",
            "error": COLOR_PRIMARY,
        }
        self.alert_banner_label.configure(text=message, text_color=color_map.get(severity, COLOR_MUTED))
        if hasattr(self, "lbl_alert_icon") and hasattr(self, "placeholder_image"):
            self.lbl_alert_icon.configure(image=self.placeholder_image)
            try:
                self.lbl_alert_icon._label.configure(image="")
            except Exception:
                pass
            self.lbl_alert_icon._my_image_ref = self.placeholder_image

    def update_dashboard_alert(self, item_name: str, grade: str | None = None, rarity_color: str | None = None, item_id: int | None = None) -> None:
        if not hasattr(self, "alert_banner") or not hasattr(self, "alert_banner_label"):
            return
        color = rarity_color or GRADE_COLORS.get((grade or "").upper(), COLOR_PRIMARY)
        self.alert_banner.configure(border_color=color, fg_color="#151515")
        self.alert_banner_label.configure(text=f"Alert: {item_name or 'Target detected'} â€¢ {(grade or 'UNKNOWN').upper()}", text_color=color)
        if hasattr(self, "lbl_alert_icon"):
            if item_id is not None:
                self.get_sprite_image(item_id, callback=lambda pil, w=self.lbl_alert_icon: self.set_widget_image(w, pil, (32, 32)))
            elif hasattr(self, "placeholder_image"):
                self.lbl_alert_icon.configure(image=self.placeholder_image)
                try:
                    self.lbl_alert_icon._label.configure(image="")
                except Exception:
                    pass
                self.lbl_alert_icon._my_image_ref = self.placeholder_image

    def load_or_build_sprite_mapping(self) -> None:
        """Loads the ID-to-sprite mapping from a local JSON file or builds it in a background thread."""
        mapping_path = ROOT / "id_to_sprite.json"
        if mapping_path.exists():
            try:
                with open(mapping_path, "r", encoding="utf-8") as f:
                    self.sprite_mapping = json.load(f)
                return
            except Exception:
                pass

        # If not found or failed, build it in a background thread
        def build_thread():
            try:
                self.append_log("[SPRITES] Database mapping 'id_to_sprite.json' not found or invalid. Building from tbh.city...\n")
                import urllib.request
                req = urllib.request.Request(
                    'https://tbh.city/items', 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    html = response.read().decode('utf-8')
                
                chunks = re.split(r'\\\"id\\\"\s*:\s*', html)
                if len(chunks) <= 1:
                    chunks = re.split(r'\"id\"\s*:\s*', html)
                
                mapping = {}
                for chunk in chunks[1:]:
                    id_match = re.match(r'^(\d+)', chunk)
                    if id_match:
                        item_id = int(id_match.group(1))
                        icon_match = re.search(r'\\\"icon\\\"\s*:\s*\\\"sprites/sharedassets0/([^\\\"]+?)\\\"', chunk)
                        if not icon_match:
                            icon_match = re.search(r'\"icon\"\s*:\s*\"sprites/sharedassets0/([^\"\s]+?)\"', chunk)
                        if icon_match:
                            sprite_name = icon_match.group(1)
                            mapping[item_id] = sprite_name
                
                if mapping:
                    with open(mapping_path, "w", encoding="utf-8") as f:
                        json.dump(mapping, f, indent=4)
                    self.sprite_mapping = mapping
                    self.after(0, lambda: self.append_log(f"[SPRITES] Database mapping successfully built with {len(mapping)} items!\n"))
            except Exception as e:
                self.after(0, lambda err=e: self.append_log(f"[WARNING] Failed to build sprite database: {err}\n"))

        threading.Thread(target=build_thread, daemon=True).start()

    def get_sprite_name(self, item_id: int) -> str:
        s_id = str(item_id)
        if hasattr(self, "sprite_mapping") and s_id in self.sprite_mapping:
            return self.sprite_mapping[s_id]

        if s_id.startswith('910'):
            return "Item_910011.png"
        elif s_id.startswith('920'):
            return "Item_920011.png"
        elif s_id.startswith('930'):
            return "Item_930011.png"
        return f"Item_{item_id}.png"

    def set_widget_image(self, widget: ctk.CTkLabel, pil_img: Image.Image, size: tuple[int, int]) -> None:
        """Safely creates a CTkImage in the main thread and configures the widget, storing a reference."""
        try:
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
            widget.configure(image=ctk_img)
            widget._my_image_ref = ctk_img
        except Exception as e:
            self.append_log(f"[WARNING] Failed to set widget image: {e}\n")

    def get_sprite_image(self, item_id: int, callback = None) -> None:
        """Asynchronously loads an item sprite from tbh.city or local cache and returns a PIL Image."""
        sprite_name = self.get_sprite_name(item_id)
        cache_dir = ROOT / "cache_sprites"
        cache_dir.mkdir(exist_ok=True)
        local_path = cache_dir / sprite_name
        
        # 1. If it exists in cache, load immediately
        if local_path.exists():
            try:
                pil_img = Image.open(local_path)
                pil_img.load()  # Read pixel data into memory immediately
                if callback:
                    callback(pil_img)
                return
            except Exception:
                try:
                    local_path.unlink()
                except Exception:
                    pass

        # 2. Download from tbh.city in a background thread
        def download_thread():
            url = f"https://tbh.city/sprites/sharedassets0/{sprite_name}"
            try:
                import urllib.request
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = response.read()
                
                local_path.write_bytes(data)
                
                pil_img = Image.open(local_path)
                pil_img.load()  # Load data into memory before switching threads
                if callback:
                    self.after(0, lambda: callback(pil_img))
            except Exception:
                pass

        threading.Thread(target=download_thread, daemon=True).start()

    def update_upcoming_drops(self, all_item_ids: list[int] | None = None, triggered_item_id: int | None = None, chest_ids: list[int | None] | None = None) -> None:
        """Update the Upcoming Important Drops cards with items from the current roll.
        
        Extracts important items from the roll that match the tracked rarities (IMMORTAL, LEGENDARY, RARE, BEYOND, ARCANA).
        Also displays the highest-grade Soulstone in the SOULSTONE card with its count.
        """
        if not hasattr(self, "upcoming_card_widgets"):
            return
        
        try:
            # Reset all cards to "No drop yet" to ensure dynamism
            for rarity, widgets in self.upcoming_card_widgets.items():
                widgets["lbl_name"].configure(text="No drop yet")
                if "lbl_price" in widgets:
                    widgets["lbl_price"].configure(text="")
                
                # Reset card border color
                color = GRADE_COLORS.get(rarity, COLOR_BORDER)
                widgets["card"].configure(border_color=color)
                
                # Clear image from CTk widget and set to placeholder
                widgets["lbl_item_icon"].configure(image=self.placeholder_image, text="")
                # CRITICAL: Force clear the underlying standard Tkinter label's image reference
                try:
                    widgets["lbl_item_icon"]._label.configure(image="")
                except Exception:
                    pass
                widgets["lbl_item_icon"]._my_image_ref = self.placeholder_image
                
                # Clear chest image from CTk widget and set to placeholder
                widgets["lbl_chest_icon"].configure(image=self.placeholder_chest_image, text="")
                # CRITICAL: Force clear the underlying standard Tkinter label's image reference
                try:
                    widgets["lbl_chest_icon"]._label.configure(image="")
                except Exception:
                    pass
                widgets["lbl_chest_icon"]._my_image_ref = self.placeholder_chest_image
                
                # Restore elements in chest frame
                if "lbl_from" in widgets:
                    widgets["lbl_from"].pack(side="left")
                if "lbl_chest_icon" in widgets:
                    widgets["lbl_chest_icon"].pack(side="left", padx=(1, 4))
                widgets["lbl_chest_name"].configure(text="", font=ctk.CTkFont(size=9, slant="italic"), text_color=COLOR_MUTED)
                
                widgets["chest_frame"].pack_forget()

            if hasattr(self, "next_drop_var"):
                self.next_drop_var.set("No valuable drops")
                if hasattr(self, "next_drop_price_var"):
                    self.next_drop_price_var.set("")
                if hasattr(self, "lbl_next_drop"):
                    self.lbl_next_drop.configure(text_color=COLOR_MUTED)
                if hasattr(self, "lbl_next_drop_icon"):
                    self.lbl_next_drop_icon.configure(image=self.placeholder_image)
                    try:
                        self.lbl_next_drop_icon._label.configure(image="")
                    except Exception:
                        pass
                    self.lbl_next_drop_icon._my_image_ref = self.placeholder_image

            if not all_item_ids:
                return
                
            if not chest_ids or len(chest_ids) != len(all_item_ids):
                chest_ids = [None] * len(all_item_ids)
            
            # Track which rarities have been filled (to avoid duplicates)
            filled_rarities = set()
            grade_values = {
                "COMMON": 0, "UNCOMMON": 1, "RARE": 2, "LEGENDARY": 3,
                "BEYOND": 4, "IMMORTAL": 5, "ARCANA": 6, "CELESTIAL": 7,
                "DIVINE": 8, "COSMIC": 9
            }
            
            # 1. Process standard cards (excluding Soulstones)
            for item_id, chest_id in zip(all_item_ids, chest_ids):
                info = self.get_item_info_by_id(item_id) or {}
                grade = info.get("grade", "COMMON").upper()
                name = self.get_item_name(info, "")
                
                # Check if it is a Soulstone
                is_soulstone = "soulstone" in name.lower() or "soul stone" in name.lower()
                
                # Only process if this grade is one of our tracked rarities, not already filled, and not a soulstone
                if grade in self.upcoming_card_widgets and grade not in filled_rarities and not is_soulstone:
                    # Update the card for this rarity
                    item_name = self.get_item_name(info, "Unknown")
                    widgets = self.upcoming_card_widgets[grade]
                    widgets["lbl_name"].configure(text=item_name)
                    
                    # Fetch price in background and update card price label
                    if "lbl_price" in widgets:
                        def make_card_price_callback(w_price):
                            return lambda price: w_price.configure(text=f"|  {price}" if price and price != "N/A" else "|  N/A")
                        self.fetch_steam_market_price(item_name, make_card_price_callback(widgets["lbl_price"]))
                    
                    # Fetch and load item sprite (main thread instantiation)
                    self.get_sprite_image(item_id, callback=lambda pil, w=widgets["lbl_item_icon"]: self.set_widget_image(w, pil, (32, 32)))
                    
                    # If chest info is present, display chest sprite and name
                    if chest_id is not None:
                        c_info = self.get_item_info_by_id(chest_id) or {}
                        c_name = self.get_item_name(c_info, "Unknown Chest")
                        widgets["lbl_chest_name"].configure(text=c_name)
                        self.get_sprite_image(chest_id, callback=lambda pil, w=widgets["lbl_chest_icon"]: self.set_widget_image(w, pil, (16, 16)))
                        widgets["chest_frame"].pack(side="left", fill="x", anchor="w", pady=(2, 0))
                    
                    filled_rarities.add(grade)

            # 2. Process Soulstone card (SOULSTONE)
            best_soulstone_id = None
            best_soulstone_info = None
            best_soulstone_val = -1
            
            for item_id in all_item_ids:
                info = self.get_item_info_by_id(item_id) or {}
                name = self.get_item_name(info, "")
                if "soulstone" in name.lower() or "soul stone" in name.lower():
                    grade = info.get("grade", "COMMON").upper()
                    val = grade_values.get(grade, 0)
                    if val > best_soulstone_val:
                        best_soulstone_val = val
                        best_soulstone_id = item_id
                        best_soulstone_info = info
            
            if best_soulstone_id is not None and "SOULSTONE" in self.upcoming_card_widgets:
                widgets = self.upcoming_card_widgets["SOULSTONE"]
                grade = best_soulstone_info.get("grade", "COMMON").upper()
                color = GRADE_COLORS.get(grade, "#e74c3c")
                
                # Update border color of the card to match soulstone rarity
                widgets["card"].configure(border_color=color)
                
                # Update item name
                widgets["lbl_name"].configure(text=self.get_item_name(best_soulstone_info, "Unknown"))
                
                # Fetch price in background and update card price label
                if "lbl_price" in widgets:
                    s_name = self.get_item_name(best_soulstone_info, "Unknown")
                    def make_card_price_callback(w_price):
                        return lambda price: w_price.configure(text=f"|  {price}" if price and price != "N/A" else "|  N/A")
                    self.fetch_steam_market_price(s_name, make_card_price_callback(widgets["lbl_price"]))
                
                # Load item sprite (main thread instantiation)
                self.get_sprite_image(best_soulstone_id, callback=lambda pil, w=widgets["lbl_item_icon"]: self.set_widget_image(w, pil, (32, 32)))
                
                # Show count
                count = all_item_ids.count(best_soulstone_id)
                if "lbl_from" in widgets:
                    widgets["lbl_from"].pack_forget()
                if "lbl_chest_icon" in widgets:
                    widgets["lbl_chest_icon"].pack_forget()
                widgets["lbl_chest_name"].configure(
                    text=f"Quantity: x{count}", 
                    font=ctk.CTkFont(size=10, weight="bold"), 
                    text_color=color
                )
                widgets["chest_frame"].pack(side="left", fill="x", anchor="w", pady=(2, 0))

            # Update Next Valuable Drop banner based on the highest grade found in the current scan
            highest_grade_item = None
            highest_grade_val = -1
            for item_id in all_item_ids:
                info = self.get_item_info_by_id(item_id) or {}
                name = self.get_item_name(info, "").lower()
                if "soulstone" in name or "soul stone" in name:
                    continue
                grade = info.get("grade", "COMMON").upper()
                val = grade_values.get(grade, 0)
                if val > highest_grade_val:
                    highest_grade_val = val
                    highest_grade_item = info

            if highest_grade_item and hasattr(self, "next_drop_var"):
                name = self.get_item_name(highest_grade_item, "Unknown")
                grade = highest_grade_item.get("grade", "COMMON")
                item_id = highest_grade_item.get("id")
                self.next_drop_var.set(name)
                if hasattr(self, "lbl_next_drop"):
                    color = GRADE_COLORS.get(grade.upper(), COLOR_TEXT)
                    self.lbl_next_drop.configure(text_color=color)
                if hasattr(self, "lbl_next_drop_icon") and item_id is not None:
                    self.get_sprite_image(item_id, callback=lambda pil, w=self.lbl_next_drop_icon: self.set_widget_image(w, pil, (32, 32)))
                     # Fetch price in background and update price label
                def update_price_callback(price):
                    if price and price != "N/A":
                        self.next_drop_price_var.set(f"|  {price}")
                    else:
                        self.next_drop_price_var.set("|  N/A")
                
                self.fetch_steam_market_price(name, update_price_callback)
            elif hasattr(self, "next_drop_var"):
                self.next_drop_var.set("No valuable drops")
                if hasattr(self, "next_drop_price_var"):
                    self.next_drop_price_var.set("")
                if hasattr(self, "lbl_next_drop"):
                    self.lbl_next_drop.configure(text_color=COLOR_MUTED)
                if hasattr(self, "lbl_next_drop_icon"):
                    self.lbl_next_drop_icon.configure(image=self.placeholder_image)
                    try:
                        self.lbl_next_drop_icon._label.configure(image="")
                    except Exception:
                        pass
                    self.lbl_next_drop_icon._my_image_ref = self.placeholder_image
        except Exception as e:
            import traceback
            self.append_log(f"\n[CRITICAL ERROR] Error in update_upcoming_drops: {e}\n{traceback.format_exc()}\n")

    def show_tab(self, name: str) -> None:
        for key, frame in self.tab_frames.items():
            frame.pack_forget()
        self.tab_frames[name].pack(fill="both", expand=True)
        for btn_name, btn in self.sidebar_buttons.items():
            if btn_name == name:
                btn.configure(
                    fg_color=COLOR_PRIMARY,
                    text_color="#0b0b0b",  # Dark text for high contrast on gold
                    border_color=COLOR_PRIMARY,
                    hover_color=COLOR_HOVER
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLOR_TEXT,
                    border_color=COLOR_BORDER,
                    hover_color=COLOR_SECONDARY
                )

    def build_left_panel(self) -> None:
        self.left_content_frame.grid_columnconfigure(0, weight=1)
        self.left_content_frame.grid_columnconfigure(1, weight=1)
        self.left_content_frame.grid_rowconfigure(0, weight=0)
        self.left_content_frame.grid_rowconfigure(1, weight=1, minsize=360)

        # 1. Proxy Controls Panel
        self.proxy_frame = ctk.CTkFrame(self.left_content_frame, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.proxy_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 12))
 
        lbl = ctk.CTkLabel(self.proxy_frame, text="Proxy Controller", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl.pack(anchor="w", padx=15, pady=(8, 10))
 
        self.btn_proxy = ctk.CTkButton(
            self.proxy_frame,
            text="Start Peeker Proxy",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.toggle_proxy,
            height=36
        )
        self.btn_proxy.pack(fill="x", padx=15, pady=(0, 8))
 
        self.btn_trust_cert = ctk.CTkButton(
            self.proxy_frame,
            text="Trust CA Certificate",
            fg_color=COLOR_SECONDARY,
            hover_color=COLOR_SEC_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.install_cert_automatically,
            height=28
        )
 
        self.lbl_proxy_status = ctk.CTkLabel(
            self.proxy_frame,
            text="Status: Stopped",
            text_color=COLOR_MUTED,
            font=ctk.CTkFont(size=12, slant="italic")
        )
        self.lbl_proxy_status.pack(anchor="w", padx=15, pady=(0, 4))
        self.btn_trust_cert.pack(fill="x", padx=15, pady=(0, 8))
 
        # 2. Relogger Setup Panel
        self.calib_frame = ctk.CTkFrame(self.left_content_frame, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.calib_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 12))
 
        lbl_cal = ctk.CTkLabel(self.calib_frame, text="Auto-Relogger Setup", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl_cal.pack(anchor="w", padx=15, pady=(8, 5))
 
        # Relogger Method Selector
        self.relogger_method_var = ctk.StringVar(value="Process Restart" if self.relogger_method == "process_restart" else "Mouse Clicks")
        
        self.seg_method = ctk.CTkSegmentedButton(
            self.calib_frame,
            values=["Process Restart", "Mouse Clicks"],
            variable=self.relogger_method_var,
            command=self.on_relogger_method_changed,
            selected_color=COLOR_PRIMARY,
            selected_hover_color=COLOR_HOVER,
            unselected_color=COLOR_SECONDARY,
            unselected_hover_color=COLOR_SEC_HOVER,
            text_color=COLOR_TEXT
        )
        self.seg_method.pack(fill="x", padx=15, pady=5)
 
        # 2a. Process Restart UI Container
        self.restart_container = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        
        lbl_path = ctk.CTkLabel(self.restart_container, text="TaskbarHero.exe Path:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED)
        lbl_path.pack(anchor="w", padx=0, pady=(5, 2))
        
        path_row = ctk.CTkFrame(self.restart_container, fg_color="transparent")
        path_row.pack(fill="x")
        
        self.entry_game_path = ctk.CTkEntry(
            path_row,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11)
        )
        self.entry_game_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_game_path.insert(0, self.game_path)
        self.entry_game_path.bind("<KeyRelease>", self.on_game_path_typed)
        
        self.btn_browse = ctk.CTkButton(
            path_row,
            text="Browse",
            width=60,
            height=28,
            fg_color=COLOR_SECONDARY,
            hover_color=COLOR_SEC_HOVER,
            command=self.browse_game_path
        )
        self.btn_browse.pack(side="right")
 
        # 2b. Mouse Clicks UI Container
        self.clicks_container = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        
        lbl_inst = ctk.CTkLabel(
            self.clicks_container,
            text="Click a button below, hover over the game item, then press F8 to save.",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color=COLOR_MUTED,
            wraplength=350,
            justify="left"
        )
        lbl_inst.pack(anchor="w", padx=0, pady=(0, 5))
 
        grid = ctk.CTkFrame(self.clicks_container, fg_color="transparent")
        grid.pack(fill="x", pady=2)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
 
        self.btn_cal_menu = ctk.CTkButton(
            grid, text="1. Menu Button", fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER,
            command=lambda: self.start_calibration("menu"), height=26
        )
        self.btn_cal_menu.grid(row=0, column=0, padx=(0, 3), pady=2, sticky="ew")
 
        self.btn_cal_exit = ctk.CTkButton(
            grid, text="2. Back to Title", fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER,
            command=lambda: self.start_calibration("exit"), height=26
        )
        self.btn_cal_exit.grid(row=0, column=1, padx=(3, 0), pady=2, sticky="ew")
 
        self.btn_cal_stage = ctk.CTkButton(
            grid, text="3. Tap to Start", fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER,
            command=lambda: self.start_calibration("stage_icon"), height=26
        )
        self.btn_cal_stage.grid(row=1, column=0, padx=(0, 3), pady=2, sticky="ew")
 
        self.btn_cal_confirm = ctk.CTkButton(
            grid, text="4. Enter Stage", fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER,
            command=lambda: self.start_calibration("confirm_enter"), height=26
        )
        self.btn_cal_confirm.grid(row=1, column=1, padx=(3, 0), pady=2, sticky="ew")
 
        self.lbl_cal_status = ctk.CTkLabel(
            self.clicks_container,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=COLOR_MUTED,
            wraplength=350,
            justify="left"
        )
        self.lbl_cal_status.pack(anchor="w", padx=0, pady=(2, 2))
        
        # 2c. Pause Delay Input
        delay_row = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        delay_row.pack(fill="x", padx=15, pady=(5, 5))
        
        lbl_delay = ctk.CTkLabel(
            delay_row, text="Pause Delay (seconds):", 
            font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED
        )
        lbl_delay.pack(side="left", padx=(0, 10))
        
        self.entry_pause_delay = ctk.CTkEntry(
            delay_row,
            width=60,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11)
        )
        self.entry_pause_delay.pack(side="left")
        self.entry_pause_delay.insert(0, str(self.pause_duration))
        self.entry_pause_delay.bind("<KeyRelease>", self.on_pause_delay_typed)
        
        # 2d. Safety Delay Input (anti-rollback)
        safety_row = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        safety_row.pack(fill="x", padx=15, pady=(2, 5))
        
        lbl_safety = ctk.CTkLabel(
            safety_row, text="Anti-Rollback Delay (s):", 
            font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED
        )
        lbl_safety.pack(side="left", padx=(0, 10))
        
        self.entry_safety_delay = ctk.CTkEntry(
            safety_row,
            width=60,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11)
        )
        self.entry_safety_delay.pack(side="left")
        self.entry_safety_delay.insert(0, str(self.relog_safety_delay))
        self.entry_safety_delay.bind("<KeyRelease>", self.on_safety_delay_typed)
        
        # 2e. Max Chest Index Input
        max_idx_row = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        max_idx_row.pack(fill="x", padx=15, pady=(2, 5))
        
        lbl_max_idx = ctk.CTkLabel(
            max_idx_row, text="Max Chest Index (Grade Match):", 
            font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED
        )
        lbl_max_idx.pack(side="left", padx=(0, 10))
        
        self.entry_max_chest_index = ctk.CTkEntry(
            max_idx_row,
            width=60,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11)
        )
        self.entry_max_chest_index.pack(side="left")
        self.entry_max_chest_index.insert(0, str(self.max_chest_index))
        self.entry_max_chest_index.bind("<KeyRelease>", self.on_max_chest_index_typed)
        
        # Show/Hide correct container initially
        self.update_relogger_ui_visibility()
 
        # 3. Auto-Relogger Actions Frame
        self.bot_frame = ctk.CTkFrame(self.left_content_frame, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.bot_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 12))
        self.bot_frame.configure(height=360)
 
        lbl_bot = ctk.CTkLabel(self.bot_frame, text="Auto-Relogger Controls", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl_bot.pack(anchor="w", padx=15, pady=(8, 10))
 
        self.btn_bot = ctk.CTkButton(
            self.bot_frame,
            text="Start Auto-Relogger",
            fg_color="#2ecc71",
            hover_color="#27ae60",
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.toggle_relogger,
            height=36
        )
        self.btn_bot.pack(fill="x", padx=15, pady=(0, 8))
 
        self.btn_force_relaunch = ctk.CTkButton(
            self.bot_frame,
            text="Force Relaunch Game",
            fg_color="#3498db",
            hover_color="#2980b9",
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.force_relaunch_game,
            height=36
        )
        self.btn_force_relaunch.pack(fill="x", padx=15, pady=(0, 8))
 
        self.btn_item_collected = ctk.CTkButton(
            self.bot_frame,
            text="âœ… Item Collected â†’ Relog Now",
            fg_color="#e67e22",
            hover_color="#d35400",
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.skip_to_safety_relog,
            height=36
        )
        # Hidden by default, shown when countdown is active
        self.btn_item_collected.pack(fill="x", padx=15, pady=(0, 8))
        self.btn_item_collected.pack_forget()
 
        self.lbl_bot_status = ctk.CTkLabel(
            self.bot_frame,
            text="Relogger Status: Inactive\n[F9] to EMERGENCY STOP at any time",
            text_color=COLOR_MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
            justify="left"
        )
        self.lbl_bot_status.pack(anchor="w", padx=15, pady=(0, 8))
 
        # 4. Tabbed Filter Panel (Specific Items vs Grade Rarity)
        self.filter_tabview = ctk.CTkTabview(
            self.left_content_frame,
            fg_color=COLOR_FRAME,
            segmented_button_selected_color=COLOR_PRIMARY,
            segmented_button_selected_hover_color=COLOR_HOVER,
            segmented_button_unselected_color=COLOR_SECONDARY,
            segmented_button_unselected_hover_color=COLOR_SEC_HOVER,
            text_color=COLOR_TEXT
        )
        self.filter_tabview.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(0, 12))
        self.filter_tabview.grid_propagate(False)
        self.filter_tabview.configure(height=360)
        
        self.tab_items = self.filter_tabview.add("Item Targets")
        self.tab_grades = self.filter_tabview.add("Grade Targets")
        self.tab_notifications = self.filter_tabview.add("Notifications")
 
        self.build_item_filters_tab()
        self.build_grade_filters_tab()
        self.build_notifications_tab()
 
    def build_item_filters_tab(self) -> None:
        # Main content area for the tab, expanded to fill the full panel height
        scroll_frame = ctk.CTkFrame(
            self.tab_items,
            fg_color="transparent"
        )
        self.tab_items.configure(height=360)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Search box
        search_box = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        search_box.pack(fill="x", padx=5, pady=(5, 5))

        self.entry_search = ctk.CTkEntry(
            search_box, placeholder_text="Item Name (e.g. Dimensional)",
            fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT
        )
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_search = ctk.CTkButton(
            search_box, text="Search", width=65, fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER,
            command=self.search_items
        )
        self.btn_search.pack(side="right")

        # Search Results Selection Area
        self.combo_results = ctk.CTkComboBox(
            scroll_frame, values=["Search and select an item..."],
            fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT,
            dropdown_fg_color=COLOR_FRAME, dropdown_hover_color=COLOR_SECONDARY
        )
        self.combo_results.pack(fill="x", padx=5, pady=5)

        # Actions Frame (Add to Targets / Add to Ignore List side-by-side)
        actions_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        actions_frame.pack(fill="x", padx=5, pady=(5, 10))
        actions_frame.grid_columnconfigure(0, weight=1)
        actions_frame.grid_columnconfigure(1, weight=1)

        self.btn_add_filter = ctk.CTkButton(
            actions_frame, text="Add to Targets ðŸŽ¯",
            fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER,
            command=self.add_target_item
        )
        self.btn_add_filter.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.btn_add_ignore = ctk.CTkButton(
            actions_frame, text="Add to Ignore List â›”",
            fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER,
            command=self.add_ignored_item
        )
        self.btn_add_ignore.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Split Container for Targets vs Ignores side-by-side
        split_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        split_frame.pack(fill="both", expand=True, padx=5, pady=5)
        split_frame.grid_columnconfigure(0, weight=1)
        split_frame.grid_columnconfigure(1, weight=1)

        # ----------------------------------------------------
        # COLUMN 0: TARGETS PANEL
        # ----------------------------------------------------
        targets_panel = ctk.CTkFrame(split_frame, fg_color="#141414", border_color=COLOR_BORDER, border_width=1)
        targets_panel.grid(row=0, column=0, padx=(0, 6), pady=5, sticky="nsew")

        lbl_t_title = ctk.CTkLabel(targets_panel, text="Active Target List ðŸŽ¯", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_PRIMARY)
        lbl_t_title.pack(anchor="w", padx=12, pady=(10, 5))

        self.target_box_container = ctk.CTkFrame(targets_panel, fg_color="transparent", height=130)
        self.target_box_container.pack(fill="x", padx=12, pady=(0, 5))
        self.target_box_container.pack_propagate(False)

        self.target_box = ctk.CTkTextbox(
            self.target_box_container, fg_color=COLOR_BG, border_color=COLOR_BORDER, border_width=1,
            text_color=COLOR_TEXT, font=ctk.CTkFont(size=11), height=18
        )
        self.target_box.pack(fill="both", expand=True)

        remove_t_frame = ctk.CTkFrame(targets_panel, fg_color="transparent")
        remove_t_frame.pack(fill="x", padx=12, pady=(5, 5))

        self.combo_active_targets = ctk.CTkComboBox(
            remove_t_frame, values=["Select a target to remove..."],
            fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT,
            dropdown_fg_color=COLOR_FRAME, dropdown_hover_color=COLOR_SECONDARY
        )
        self.combo_active_targets.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_remove_target = ctk.CTkButton(
            remove_t_frame, text="Remove",
            fg_color="#e67e22", hover_color="#d35400",
            text_color=COLOR_TEXT,
            command=self.remove_target_item,
            width=80
        )
        self.btn_remove_target.pack(side="right")

        self.btn_clear_filters = ctk.CTkButton(
            targets_panel, text="Clear Target List",
            fg_color="#e74c3c", hover_color="#c0392b",
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.clear_target_items,
            height=28
        )
        self.btn_clear_filters.pack(fill="x", padx=12, pady=(5, 10))

        # ----------------------------------------------------
        # COLUMN 1: IGNORES PANEL
        # ----------------------------------------------------
        ignores_panel = ctk.CTkFrame(split_frame, fg_color="#141414", border_color=COLOR_BORDER, border_width=1)
        ignores_panel.grid(row=0, column=1, padx=(6, 0), pady=5, sticky="nsew")

        lbl_i_title = ctk.CTkLabel(ignores_panel, text="Active Ignore List â›”", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_PRIMARY)
        lbl_i_title.pack(anchor="w", padx=12, pady=(10, 5))

        self.ignore_box_container = ctk.CTkFrame(ignores_panel, fg_color="transparent", height=130)
        self.ignore_box_container.pack(fill="x", padx=12, pady=(0, 5))
        self.ignore_box_container.pack_propagate(False)

        self.ignore_box = ctk.CTkTextbox(
            self.ignore_box_container, fg_color=COLOR_BG, border_color=COLOR_BORDER, border_width=1,
            text_color=COLOR_TEXT, font=ctk.CTkFont(size=11), height=18
        )
        self.ignore_box.pack(fill="both", expand=True)

        remove_i_frame = ctk.CTkFrame(ignores_panel, fg_color="transparent")
        remove_i_frame.pack(fill="x", padx=12, pady=(5, 5))

        self.combo_active_ignores = ctk.CTkComboBox(
            remove_i_frame, values=["Select an item to un-ignore..."],
            fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT,
            dropdown_fg_color=COLOR_FRAME, dropdown_hover_color=COLOR_SECONDARY
        )
        self.combo_active_ignores.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_remove_ignore = ctk.CTkButton(
            remove_i_frame, text="Un-ignore",
            fg_color="#e67e22", hover_color="#d35400",
            text_color=COLOR_TEXT,
            command=self.remove_ignored_item,
            width=80
        )
        self.btn_remove_ignore.pack(side="right")

        self.btn_clear_ignores = ctk.CTkButton(
            ignores_panel, text="Clear Ignore List",
            fg_color="#e74c3c", hover_color="#c0392b",
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.clear_ignored_items,
            height=28
        )
        self.btn_clear_ignores.pack(fill="x", padx=12, pady=(5, 10))

        self.update_target_box()
 
    def build_grade_filters_tab(self) -> None:
        # Main content area for the tab, expanded to fill the full panel height
        scroll_frame = ctk.CTkFrame(
            self.tab_grades,
            fg_color="transparent"
        )
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
 
        lbl_grade_title = ctk.CTkLabel(
            scroll_frame,
            text="Stop relogger if ANY item of checked rarity drops:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT
        )
        lbl_grade_title.pack(anchor="w", padx=5, pady=(5, 10))
 
        # Checkboxes for grades
        self.grade_vars = {}
        grades_list = ["RARE", "BEYOND", "LEGENDARY", "IMMORTAL", "ARCANA", "CELESTIAL", "DIVINE", "COSMIC"]
        
        for g in grades_list:
            var = ctk.BooleanVar(value=(g in self.target_grades))
            self.grade_vars[g] = var
            
            cb = ctk.CTkCheckBox(
                scroll_frame,
                text=g.capitalize(),
                variable=var,
                command=self.save_grades_config,
                fg_color=COLOR_PRIMARY,
                hover_color=COLOR_HOVER,
                border_color=COLOR_BORDER,
                text_color=COLOR_TEXT
            )
            cb.pack(anchor="w", padx=15, pady=5)
 
        lbl_except = ctk.CTkLabel(
            scroll_frame,
            text="âš ï¸ Note: Soulstones are automatically EXCLUDED from grade-based matching to prevent useless stops.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color=COLOR_PRIMARY,
            wraplength=300,
            justify="left"
        )
        lbl_except.pack(anchor="w", padx=5, pady=(15, 5))
 
    def build_notifications_tab(self) -> None:
        # Main content area for the tab, expanded to fill the full panel height
        scroll_frame = ctk.CTkFrame(
            self.tab_notifications,
            fg_color="transparent"
        )
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
 
        lbl_discord_title = ctk.CTkLabel(
            scroll_frame,
            text="Discord Webhook Notifications",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT
        )
        lbl_discord_title.pack(anchor="w", padx=5, pady=(5, 10))
 
        # Checkbox to enable/disable Discord alerts
        self.discord_notify_var = ctk.BooleanVar(value=self.discord_notify_enabled)
        cb_notify = ctk.CTkCheckBox(
            scroll_frame,
            text="Enable Discord Notifications",
            variable=self.discord_notify_var,
            command=self.on_discord_notify_toggled,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_HOVER,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT
        )
        cb_notify.pack(anchor="w", padx=15, pady=5)
 
        # Discord Webhook URL Entry
        lbl_webhook_url = ctk.CTkLabel(
            scroll_frame,
            text="Discord Webhook URL:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_MUTED
        )
        lbl_webhook_url.pack(anchor="w", padx=5, pady=(10, 2))
 
        self.entry_webhook_url = ctk.CTkEntry(
            scroll_frame,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="https://discord.com/api/webhooks/...",
            font=ctk.CTkFont(size=11)
        )
        self.entry_webhook_url.pack(fill="x", padx=5, pady=5)
        self.entry_webhook_url.insert(0, self.discord_webhook_url)
        self.entry_webhook_url.bind("<KeyRelease>", self.on_webhook_url_typed)
 
        # Discord User ID Entry (for @mention)
        lbl_user_id = ctk.CTkLabel(
            scroll_frame,
            text="Discord User ID (for @mention):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_MUTED
        )
        lbl_user_id.pack(anchor="w", padx=5, pady=(5, 2))
 
        self.entry_discord_user_id = ctk.CTkEntry(
            scroll_frame,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="Right-click profile â†’ Copy User ID",
            font=ctk.CTkFont(size=11)
        )
        self.entry_discord_user_id.pack(fill="x", padx=5, pady=2)
        self.entry_discord_user_id.insert(0, self.discord_user_id)
        self.entry_discord_user_id.bind("<KeyRelease>", self.on_discord_user_id_typed)
 
        # Test notification button
        self.btn_test_webhook = ctk.CTkButton(
            scroll_frame,
            text="Send Test Notification",
            fg_color=COLOR_SECONDARY,
            hover_color=COLOR_SEC_HOVER,
            command=self.send_test_discord_notification
        )
        self.btn_test_webhook.pack(fill="x", padx=5, pady=(15, 5))
 
        telegram_divider = ctk.CTkFrame(scroll_frame, height=2, fg_color=COLOR_BORDER)
        telegram_divider.pack(fill="x", pady=15)
 
        lbl_telegram_title = ctk.CTkLabel(
            scroll_frame,
            text="Telegram Bot Notifications",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT
        )
        lbl_telegram_title.pack(anchor="w", padx=5, pady=(5, 10))
 
        self.telegram_notify_var = ctk.BooleanVar(value=self.telegram_notify_enabled)
        cb_telegram = ctk.CTkCheckBox(
            scroll_frame,
            text="Enable Telegram Notifications",
            variable=self.telegram_notify_var,
            command=self.on_telegram_notify_toggled,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_HOVER,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT
        )
        cb_telegram.pack(anchor="w", padx=15, pady=5)
 
        lbl_telegram_token = ctk.CTkLabel(
            scroll_frame,
            text="Telegram BotFather Token:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_MUTED
        )
        lbl_telegram_token.pack(anchor="w", padx=5, pady=(10, 2))
 
        self.entry_telegram_bot_token = ctk.CTkEntry(
            scroll_frame,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="123456789:AA...",
            font=ctk.CTkFont(size=11),
            show="*"
        )
        self.entry_telegram_bot_token.pack(fill="x", padx=5, pady=5)
        self.entry_telegram_bot_token.insert(0, self.telegram_bot_token)
        self.entry_telegram_bot_token.bind("<KeyRelease>", self.on_telegram_bot_token_typed)
 
        lbl_telegram_chat = ctk.CTkLabel(
            scroll_frame,
            text="Telegram Chat ID:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_MUTED
        )
        lbl_telegram_chat.pack(anchor="w", padx=5, pady=(5, 2))
 
        self.entry_telegram_chat_id = ctk.CTkEntry(
            scroll_frame,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="Send /start to the bot, then click Detect Chat ID",
            font=ctk.CTkFont(size=11)
        )
        self.entry_telegram_chat_id.pack(fill="x", padx=5, pady=2)
        self.entry_telegram_chat_id.insert(0, self.telegram_chat_id)
        self.entry_telegram_chat_id.bind("<KeyRelease>", self.on_telegram_chat_id_typed)
 
        telegram_buttons = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        telegram_buttons.pack(fill="x", padx=5, pady=(10, 5))
 
        self.btn_detect_telegram_chat = ctk.CTkButton(
            telegram_buttons,
            text="Detect Chat ID",
            fg_color=COLOR_SECONDARY,
            hover_color=COLOR_SEC_HOVER,
            command=self.detect_telegram_chat_id
        )
        self.btn_detect_telegram_chat.pack(side="left", fill="x", expand=True, padx=(0, 5))
 
        self.btn_test_telegram = ctk.CTkButton(
            telegram_buttons,
            text="Send Telegram Test",
            fg_color=COLOR_SECONDARY,
            hover_color=COLOR_SEC_HOVER,
            command=self.send_test_telegram_notification
        )
        self.btn_test_telegram.pack(side="left", fill="x", expand=True, padx=(5, 0))
 
        # Divider Line
        divider = ctk.CTkFrame(scroll_frame, height=2, fg_color=COLOR_BORDER)
        divider.pack(fill="x", pady=15)
 
        lbl_trainer_title = ctk.CTkLabel(
            scroll_frame,
            text="TBH Trainer Automation",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT
        )
        lbl_trainer_title.pack(anchor="w", padx=5, pady=(5, 10))
 
        # Checkbox to enable/disable Trainer Auto Launch
        self.trainer_auto_launch_var = ctk.BooleanVar(value=self.trainer_auto_launch)
        cb_trainer = ctk.CTkCheckBox(
            scroll_frame,
            text="Auto-launch Trainer on Target Found",
            variable=self.trainer_auto_launch_var,
            command=self.on_trainer_auto_launch_toggled,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_HOVER,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT
        )
        cb_trainer.pack(anchor="w", padx=15, pady=5)
 
        # Trainer Path Entry
        lbl_trainer_path = ctk.CTkLabel(
            scroll_frame,
            text="TBH Trainer.exe Path:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_MUTED
        )
        lbl_trainer_path.pack(anchor="w", padx=5, pady=(10, 2))
 
        trainer_path_row = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        trainer_path_row.pack(fill="x", padx=5)
 
        self.entry_trainer_path = ctk.CTkEntry(
            trainer_path_row,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11)
        )
        self.entry_trainer_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_trainer_path.insert(0, self.trainer_path)
        self.entry_trainer_path.bind("<KeyRelease>", self.on_trainer_path_typed)
 
        self.btn_browse_trainer = ctk.CTkButton(
            trainer_path_row,
            text="Browse",
            width=60,
            height=28,
            fg_color=COLOR_SECONDARY,
            hover_color=COLOR_SEC_HOVER,
            command=self.browse_trainer_path
        )
        self.btn_browse_trainer.pack(side="right")
 
    def on_trainer_auto_launch_toggled(self) -> None:
        self.trainer_auto_launch = self.trainer_auto_launch_var.get()
        self.save_peeker_config()
        self.append_log(f"[CONFIG] Trainer auto-launch enabled: {self.trainer_auto_launch}\n")
 
    def on_trainer_path_typed(self, event: Any) -> None:
        self.trainer_path = self.entry_trainer_path.get().strip()
        self.save_peeker_config()
 
    def browse_trainer_path(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select TBH Trainer.exe",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if path:
            self.trainer_path = os.path.normpath(path)
            self.entry_trainer_path.delete(0, "end")
            self.entry_trainer_path.insert(0, self.trainer_path)
            self.save_peeker_config()
            self.append_log(f"[CONFIG] Trainer path updated to: {self.trainer_path}\n")
 
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
 
    def on_telegram_notify_toggled(self) -> None:
        self.telegram_notify_enabled = self.telegram_notify_var.get()
        self.save_peeker_config()
        self.append_log(f"[TELEGRAM] Telegram notification enabled: {self.telegram_notify_enabled}\n")
 
    def on_telegram_bot_token_typed(self, event: Any) -> None:
        self.telegram_bot_token = self.entry_telegram_bot_token.get().strip()
        self.save_peeker_config()
 
    def on_telegram_chat_id_typed(self, event: Any) -> None:
        self.telegram_chat_id = self.entry_telegram_chat_id.get().strip()
        self.save_peeker_config()
 
    def detect_telegram_chat_id(self) -> None:
        token = self.entry_telegram_bot_token.get().strip()
        if not token:
            self.append_log("[TELEGRAM] Cannot detect Chat ID: bot token is empty.\n")
            return
 
        self.append_log("[TELEGRAM] Detecting Chat ID from recent bot messages...\n")
 
        def run_detect():
            success, msg, chat_id = TelegramNotifier(token).detect_chat_id()
            if not success:
                self.after(0, lambda: self.append_log(f"[TELEGRAM] [ERROR] Failed to detect Chat ID: {msg}\n"))
                return
 
            def apply_chat_id():
                self.telegram_chat_id = chat_id
                self.entry_telegram_chat_id.delete(0, "end")
                self.entry_telegram_chat_id.insert(0, chat_id)
                self.save_peeker_config()
                self.append_log(f"[TELEGRAM] Chat ID detected and saved: {chat_id}\n")
 
            self.after(0, apply_chat_id)
 
        threading.Thread(target=run_detect, daemon=True).start()
 
    def send_test_telegram_notification(self) -> None:
        token = self.entry_telegram_bot_token.get().strip()
        chat_id = self.entry_telegram_chat_id.get().strip()
        if not token or not chat_id:
            self.append_log("[TELEGRAM] Cannot send test notification: token or Chat ID is empty.\n")
            return
 
        self.telegram_bot_token = token
        self.telegram_chat_id = chat_id
        self.save_peeker_config()
        self.append_log("[TELEGRAM] Sending test notification...\n")
 
        def run_test():
            success, msg = TelegramNotifier(token, chat_id).send_message(
                "TBH Chest Peeker test notification. Telegram alerts are working."
            )
            if success:
                self.after(0, lambda: self.append_log("[TELEGRAM] Test notification sent successfully!\n"))
            else:
                self.after(0, lambda: self.append_log(f"[TELEGRAM] [ERROR] Failed to send test notification: {msg}\n"))
 
        threading.Thread(target=run_test, daemon=True).start()
 
    def notify_telegram_match(self, item_id: int, item_name: str, grade: str, action_type: str) -> None:
        if not self.telegram_notify_enabled or not self.telegram_bot_token or not self.telegram_chat_id:
            return
 
        token = self.telegram_bot_token
        chat_id = self.telegram_chat_id
 
        def run_notify():
            success, msg = TelegramNotifier(token, chat_id).send_target_alert(item_id, item_name, grade, action_type)
            if not success:
                self.after(0, lambda: self.append_log(f"[TELEGRAM] [ERROR] Failed to send alert: {msg}\n"))
 
        threading.Thread(target=run_notify, daemon=True).start()
    def send_test_discord_notification(self) -> None:
        url = self.entry_webhook_url.get().strip()
        if not url:
            self.append_log("[DISCORD] Cannot send test notification: Webhook URL is empty.\n")
            return
        
        self.append_log("[DISCORD] Sending test notification...\n")
        
        def run_test():
            payload = {
                "username": "TBH Chest Peeker",
                "content": "ðŸ”” This is a test notification from your TBH Chest Peeker! Your Webhook configuration is working correctly."
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
        
        title = "ðŸŽ¯ Target Item Filter Matched!"
        if action_type == "chests":
            desc = f"**Item Found in Upcoming Chests!**\n\nâ€¢ **Name**: {item_name}\nâ€¢ **ID**: {item_id}\nâ€¢ **Grade**: {grade}\n\n*The relogger has paused to let you collect it.*"
        elif action_type == "direct":
            desc = f"**Item Collected (Direct Drop)!**\n\nâ€¢ **Name**: {item_name}\nâ€¢ **ID**: {item_id}\nâ€¢ **Grade**: {grade}\n\n*The relogger is resuming automated re-entry.*"
        elif action_type == "synthesis":
            desc = f"**Item Collected (Synthesis)!**\n\nâ€¢ **Name**: {item_name}\nâ€¢ **ID**: {item_id}\nâ€¢ **Grade**: {grade}\n\n*The relogger is resuming automated re-entry.*"
        else:
            desc = f"**Item Detected!**\n\nâ€¢ **Name**: {item_name}\nâ€¢ **ID**: {item_id}\nâ€¢ **Grade**: {grade}"
            
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
 
    def build_right_panel(self) -> None:
        # Live Stage Peek Feed
        self.feed_frame = ctk.CTkFrame(self.right_frame, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.feed_frame.pack(fill="both", expand=True, pady=(0, 10))
 
        lbl = ctk.CTkLabel(
            self.feed_frame, 
            text="Live Peek Feed", 
            font=ctk.CTkFont(size=16, weight="bold"), 
            text_color=COLOR_TEXT
        )
        lbl.pack(anchor="w", padx=15, pady=(10, 5))
 
        # Standard Tkinter Text wrapped in CTkFrame for styling, and scrolled with CTkScrollbar
        log_container = ctk.CTkFrame(self.feed_frame, fg_color=COLOR_BG, border_color=COLOR_BORDER, border_width=1)
        log_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))
 
        self.txt_log = tk.Text(
            log_container,
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            selectbackground=COLOR_PRIMARY,
            selectforeground=COLOR_TEXT,
            bd=0,
            highlightthickness=0,
            font=("Consolas", 9)
        )
        self.txt_log.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
 
        scrollbar = ctk.CTkScrollbar(log_container, command=self.txt_log.yview, button_color=COLOR_PRIMARY, button_hover_color=COLOR_HOVER)
        scrollbar.pack(side="right", fill="y", padx=(5, 5), pady=10)
        self.txt_log.configure(yscrollcommand=scrollbar.set)
 
    # =====================================================================
    # Log / Status / Label Updaters
    # =====================================================================
    def append_log(self, text: str) -> None:
        """Appends plain logs to the Live Feed terminal widget."""
        self.txt_log.insert("end", text)
        self.txt_log.see("end")
 
    def append_colored_drop(self, idx: int, name: str, grade: str, is_chest: bool = False) -> None:
        """Appends item display lines formatted using color markers."""
        color = GRADE_COLORS.get(grade.upper(), COLOR_TEXT)
        lbl_type = "Chest" if is_chest else "Drop"
        tag_name = f"grade_{grade.upper()}"
        
        # Configure tag color once (Tkinter handles duplicates safely)
        self.txt_log.tag_config(tag_name, foreground=color)
        
        if is_chest:
            self.txt_log.insert("end", f"[{idx}] {lbl_type}: ")
            self.txt_log.insert("end", f"{name} [{grade}]\n", tag_name)
        else:
            self.txt_log.insert("end", "   â””â”€ Drop: ")
            self.txt_log.insert("end", f"{name} [{grade}]\n", tag_name)
            
        self.txt_log.see("end")
 
    def update_cal_labels(self) -> None:
        if not hasattr(self, 'lbl_cal_status') or not self.lbl_cal_status.winfo_exists():
            return
        menu_st = "OK" if self.coords["menu"] else "No"
        exit_st = "OK" if self.coords["exit"] else "No"
        stage_st = "OK" if self.coords["stage_icon"] else "No"
        conf_st = "OK" if self.coords["confirm_enter"] else "No"
        self.lbl_cal_status.configure(
            text=f"Coords: Menu ({menu_st}), Title ({exit_st}), Start ({stage_st}), Enter ({conf_st})"
        )
 
    def on_relogger_method_changed(self, method: str) -> None:
        if method == "Process Restart":
            self.relogger_method = "process_restart"
        else:
            self.relogger_method = "mouse_clicks"
        self.save_peeker_config()
        self.update_relogger_ui_visibility()
 
    def update_relogger_ui_visibility(self) -> None:
        if self.relogger_method == "process_restart":
            if hasattr(self, 'clicks_container') and self.clicks_container.winfo_exists():
                self.clicks_container.pack_forget()
            if hasattr(self, 'restart_container') and self.restart_container.winfo_exists():
                self.restart_container.pack(fill="x", padx=15, pady=5)
        else:
            if hasattr(self, 'restart_container') and self.restart_container.winfo_exists():
                self.restart_container.pack_forget()
            if hasattr(self, 'clicks_container') and self.clicks_container.winfo_exists():
                self.clicks_container.pack(fill="x", padx=15, pady=5)
                self.update_cal_labels()
 
    def browse_game_path(self) -> None:
        from tkinter import filedialog
        initial_dir = "C:\\"
        if self.game_path and os.path.exists(os.path.dirname(self.game_path)):
            initial_dir = os.path.dirname(self.game_path)
        path = filedialog.askopenfilename(
            title="Select TaskbarHero.exe",
            initialdir=initial_dir,
            filetypes=[("Executable Files", "*.exe")]
        )
        if path:
            self.game_path = os.path.normpath(path)
            self.entry_game_path.delete(0, "end")
            self.entry_game_path.insert(0, self.game_path)
            self.save_peeker_config()
            self.append_log(f"[CONFIG] Game path updated to: {self.game_path}\n")
 
    def on_game_path_typed(self, event: Any) -> None:
        self.game_path = self.entry_game_path.get().strip()
        self.save_peeker_config()
 
    def on_pause_delay_typed(self, event: Any) -> None:
        try:
            val = int(self.entry_pause_delay.get().strip())
            if val > 0:
                self.pause_duration = val
                self.save_peeker_config()
        except Exception:
            pass
 
    def on_safety_delay_typed(self, event: Any) -> None:
        try:
            val = int(self.entry_safety_delay.get().strip())
            if val >= 0:
                self.relog_safety_delay = val
                self.save_peeker_config()
        except Exception:
            pass
 
    def on_max_chest_index_typed(self, event: Any) -> None:
        try:
            val = int(self.entry_max_chest_index.get().strip())
            if val >= 0:
                self.max_chest_index = val
                self.save_peeker_config()
        except Exception:
            pass

    def on_rare_cooldown_typed(self, event: Any) -> None:
        try:
            val = int(self.entry_rare_cooldown.get().strip())
            if val >= 0:
                self.rare_chest_cooldown = val
                self.save_peeker_config()
        except Exception:
            pass

    def on_uncommon_cooldown_typed(self, event: Any) -> None:
        try:
            val = int(self.entry_uncommon_cooldown.get().strip())
            if val >= 0:
                self.uncommon_chest_cooldown = val
                self.save_peeker_config()
        except Exception:
            pass
 
    def update_target_box(self) -> None:
        # 1. Update Target Box
        self.target_box.configure(state="normal")
        self.target_box.delete("1.0", "end")
        active_vals = []
        if not self.target_items:
            self.target_box.insert("end", "No target items set.\n")
            active_vals = ["No active targets"]
        else:
            for idx, item_id in enumerate(self.target_items, 1):
                info = self.get_item_info_by_id(item_id)
                if info:
                    name = self.get_item_name(info, "Unknown")
                    grade = info.get("grade", "COMMON")
                    disp_str = f"{name} (ID: {item_id}) [{grade}]"
                    self.target_box.insert("end", f" {idx}. {disp_str}\n")
                    active_vals.append(disp_str)
                else:
                    disp_str = f"Item ID: {item_id}"
                    self.target_box.insert("end", f" {idx}. {disp_str}\n")
                    active_vals.append(disp_str)
        self.target_box.configure(state="disabled")
        
        # Update the active targets removal dropdown
        if hasattr(self, "combo_active_targets"):
            self.combo_active_targets.configure(values=active_vals)
            if active_vals:
                self.combo_active_targets.set(active_vals[0])

        # 2. Update Ignore Box
        if hasattr(self, "ignore_box"):
            self.ignore_box.configure(state="normal")
            self.ignore_box.delete("1.0", "end")
            active_ignores = []
            if not getattr(self, "ignored_items", []):
                self.ignore_box.insert("end", "No ignored items set.\n")
                active_ignores = ["No active ignores"]
            else:
                for idx, item_id in enumerate(self.ignored_items, 1):
                    info = self.get_item_info_by_id(item_id)
                    if info:
                        name = self.get_item_name(info, "Unknown")
                        grade = info.get("grade", "COMMON")
                        disp_str = f"{name} (ID: {item_id}) [{grade}]"
                        self.ignore_box.insert("end", f" {idx}. {disp_str}\n")
                        active_ignores.append(disp_str)
                    else:
                        disp_str = f"Item ID: {item_id}"
                        self.ignore_box.insert("end", f" {idx}. {disp_str}\n")
                        active_ignores.append(disp_str)
            self.ignore_box.configure(state="disabled")
            
            # Update the active ignores removal dropdown
            if hasattr(self, "combo_active_ignores"):
                self.combo_active_ignores.configure(values=active_ignores)
                if active_ignores:
                    self.combo_active_ignores.set(active_ignores[0])

    def remove_target_item(self) -> None:
        selected = self.combo_active_targets.get()
        if "ID: " not in selected and "Item ID: " not in selected:
            return
        
        item_id = None
        match = re.search(r"\(ID:\s*(?P<id>\d+)\)", selected)
        if match:
            item_id = int(match.group("id"))
        else:
            match = re.search(r"Item ID:\s*(?P<id>\d+)", selected)
            if match:
                item_id = int(match.group("id"))
                
        if item_id is not None and item_id in self.target_items:
            self.target_items.remove(item_id)
            self.save_peeker_config()
            self.update_target_box()
            self.append_log(f"[FILTER] Removed Item ID {item_id} from targets.\n")

    def remove_ignored_item(self) -> None:
        selected = self.combo_active_ignores.get()
        if "ID: " not in selected and "Item ID: " not in selected:
            return
        
        item_id = None
        match = re.search(r"\(ID:\s*(?P<id>\d+)\)", selected)
        if match:
            item_id = int(match.group("id"))
        else:
            match = re.search(r"Item ID:\s*(?P<id>\d+)", selected)
            if match:
                item_id = int(match.group("id"))
                
        if item_id is not None and item_id in self.ignored_items:
            self.ignored_items.remove(item_id)
            self.save_peeker_config()
            self.update_target_box()
            self.append_log(f"[FILTER] Removed Item ID {item_id} from ignores.\n")
 
    def get_item_info_by_id(self, item_id: int) -> dict[str, Any] | None:
        for x in self.items_db:
            if x.get("id") == item_id:
                return x
        return None
 
    def get_item_name(self, info: dict[str, Any] | None, default: str = "Unknown") -> str:
        if not info:
            return default
        name_dict = info.get("name")
        if not isinstance(name_dict, dict):
            return default
        return name_dict.get("en-US", name_dict.get("en", default))

    def estimate_chest_cooldown(self, chest_id: int | None) -> int:
        if chest_id is None:
            return self.uncommon_chest_cooldown
        c_info = self.get_item_info_by_id(chest_id)
        if not c_info:
            return self.uncommon_chest_cooldown
        name = self.get_item_name(c_info, "").lower()
        grade = c_info.get("grade", "COMMON").upper()
        
        if "boss" in name or "rare" in name or grade in ["RARE", "BOSS"]:
            return self.rare_chest_cooldown
        return self.uncommon_chest_cooldown
 
    # =====================================================================
    # Item Search & Filtering
    # =====================================================================
    def search_items(self) -> None:
        query = self.entry_search.get().strip().lower()
        if not query:
            self.combo_results.configure(values=["Type a keyword first..."])
            return
 
        matches = []
        for x in self.items_db:
            name_en = self.get_item_name(x, "").lower()
            name_dict = x.get("name")
            name_id = ""
            if isinstance(name_dict, dict):
                name_id = name_dict.get("id", "").lower()
            item_id = str(x.get("id", ""))
            
            if query in name_en or query in name_id or query == item_id:
                name_en_disp = self.get_item_name(x, "Unknown")
                grade = x.get("grade", "COMMON")
                level = f" Lv.{x['level']}" if x.get("level") is not None else ""
                matches.append(f"{name_en_disp}{level} [{grade}] (ID: {x['id']})")
                if len(matches) >= 30: # Limit to 30 items
                    break
        
        if matches:
            self.combo_results.configure(values=matches)
            self.combo_results.set(matches[0])
        else:
            self.combo_results.configure(values=["No matches found."])
            self.combo_results.set("No matches found.")
 
    def add_target_item(self) -> None:
        selected = self.combo_results.get()
        if "ID: " not in selected:
            return
        
        match = re.search(r"\(ID:\s*(?P<id>\d+)\)", selected)
        if match:
            item_id = int(match.group("id"))
            if item_id not in self.target_items:
                self.target_items.append(item_id)
                self.save_peeker_config()
                self.update_target_box()
                self.append_log(f"[FILTER] Added Item ID {item_id} to targets.\n")

    def add_ignored_item(self) -> None:
        selected = self.combo_results.get()
        if "ID: " not in selected:
            return
        
        match = re.search(r"\(ID:\s*(?P<id>\d+)\)", selected)
        if match:
            item_id = int(match.group("id"))
            if item_id not in self.ignored_items:
                self.ignored_items.append(item_id)
                self.save_peeker_config()
                self.update_target_box()
                self.append_log(f"[FILTER] Added Item ID {item_id} to ignores.\n")
 
    def clear_target_items(self) -> None:
        self.target_items = []
        self.save_peeker_config()
        self.update_target_box()
        self.append_log("[FILTER] Cleared all target items.\n")

    def clear_ignored_items(self) -> None:
        self.ignored_items = []
        self.save_peeker_config()
        self.update_target_box()
        self.append_log("[FILTER] Cleared all ignored items.\n")
 
    def save_grades_config(self) -> None:
        self.target_grades = [g for g, var in self.grade_vars.items() if var.get()]
        self.save_peeker_config()
        self.append_log(f"[FILTER] Target Grades updated: {self.target_grades}\n")
 
    # =====================================================================
    # Calibration Functions (F8 listener)
    # =====================================================================
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
        if self.relogger_active:
            if (ctypes.windll.user32.GetAsyncKeyState(0x78) & 0x8000) != 0:
                self.stop_relogger("EMERGENCY STOP (F9 Pressed)")
                while (ctypes.windll.user32.GetAsyncKeyState(0x78) & 0x8000) != 0:
                    time.sleep(0.05)
 
        self.after(50, self.check_hotkeys)
 
    # =====================================================================
    # Proxy Process Runner
    # =====================================================================
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
 
    # =====================================================================
    # Log / Stdout Parser & Relogger Logic
    # =====================================================================
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
        
        # Debug traffic lines from proxy â€” show in log for traffic analysis
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
        
        if plain_line.strip() and not plain_line.startswith("=") and not plain_line.startswith(" Chest:") and not plain_line.startswith("    â””â”€ Drop:"):
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
        
        # Handle 'seen' results silently â€” these are item IDs from any server response.
        # If a target match is found while a countdown is running, auto-trigger safety relog.
        if res_type == "seen":
            seen_ids = data if isinstance(data, list) else []
            
            # Desempilhar itens da fila sequencialmente para manter o controle de progresso
            for item_id in seen_ids:
                if hasattr(self, 'current_stage_queue') and self.current_stage_queue and item_id in self.current_stage_queue:
                    try:
                        idx = self.current_stage_queue.index(item_id)
                        # Desempilhar atÃ© o item atual (inclusive)
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
                                    if current_display_name and popped_name in current_display_name and not current_display_name.startswith("âœ“"):
                                        widgets["lbl_name"].configure(text=f"âœ“ Coletado: {popped_name}", text_color="#7f8c8d")
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
                    self.append_log(f"\n[LIVE DETECT] ðŸŽ¯ Target item '{name}' (ID: {item_id}) detected in server response!\n")
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
                        self.append_log(f"\n[LIVE DETECT] ðŸŽ¯ Target grade '{grade}' item '{display_name}' (ID: {item_id}) detected in server response!\n")
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
            self.append_log(f"\n[ERROR] âš  Server error detected (HTTP {error_code})! Error #{self.consecutive_errors}\n")
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
 
        # Valid game data received â€” reset error counter
        self.consecutive_errors = 0
 
        self.append_log(f"\n======================================================\n")
        self.append_log(f"   [PEEK FEED] DETECTED MAP DATA LOADED ({res_type.upper()})\n")
        self.append_log(f"======================================================\n")
 
        found_item_ids = []
        found_item_indices = []
        found_chest_ids = []
        
        if res_type == "chests":
            # list of lists: [[chest_id, reward_id], ...]
            for idx, (chest_id, reward_id) in enumerate(data, 1):
                c_info = self.get_item_info_by_id(chest_id) or {}
                r_info = self.get_item_info_by_id(reward_id) or {}
                
                c_name = self.get_item_name(c_info, f"Chest ({chest_id})")
                r_name = self.get_item_name(r_info, f"Reward ({reward_id})")
                r_grade = r_info.get("grade", "COMMON")
                c_grade = c_info.get("grade", "COMMON")
                if "boss" in c_name.lower():
                    c_grade = "BOSS"
                
                self.append_colored_drop(idx, c_name, c_grade, is_chest=True)
                self.append_colored_drop(idx, r_name, r_grade, is_chest=False)
                
                found_item_ids.append(reward_id)
                found_item_indices.append(idx)
                found_chest_ids.append(chest_id)
                
        elif res_type == "direct":
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
        self.evaluate_filters_and_relog(found_item_ids, res_type, found_item_indices, found_chest_ids)

    def evaluate_filters_and_relog(self, found_item_ids: list[int], res_type: str = "chests", item_indices: list[int] | None = None, chest_ids: list[int | None] | None = None) -> None:
        try:
            self._evaluate_filters_and_relog_impl(found_item_ids, res_type, item_indices, chest_ids)
        except Exception as e:
            import traceback
            self.append_log(f"\n[CRITICAL ERROR] Error in evaluate_filters_and_relog: {e}\n{traceback.format_exc()}\n")

    def _evaluate_filters_and_relog_impl(self, found_item_ids: list[int], res_type: str = "chests", item_indices: list[int] | None = None, chest_ids: list[int | None] | None = None) -> None:
        if res_type == "chests":
            self.current_stage_queue = list(found_item_ids)
            self.current_chest_queue = list(chest_ids) if chest_ids else [None] * len(found_item_ids)
            self.target_chest_index = None

        # Check if any target item is present (independent of relogger_active)
        target_found = False
        found_target_id = None
        
        if item_indices is None:
            item_indices = [1] * len(found_item_ids)

        for item_id, index in zip(found_item_ids, item_indices):
            # Skip if in ignore list
            if item_id in getattr(self, "ignored_items", []):
                continue

            # 1. Check if matches specific item targets (ALWAYS matches regardless of index)
            if item_id in self.target_items:
                target_found = True
                found_target_id = item_id
                break
            
            # 2. Check if matches grade targets (excluding Soulstones)
            # Skip grade matching if chest index is greater than max_chest_index
            if index > self.max_chest_index:
                continue

            info = self.get_item_info_by_id(item_id)
            if info:
                grade = info.get("grade", "COMMON").upper()
                if grade in self.target_grades:
                    # Check name for "soulstone"
                    name = self.get_item_name(info, "").lower()
                    if "soulstone" in name or "soul stone" in name:
                        # Skip this item as it is a Soulstone
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
            
            # Send external notifications if enabled
            self.notify_discord_match(found_target_id, name, grade, res_type)
            self.notify_telegram_match(found_target_id, name, grade, res_type)
            
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
            
            # Auto-Relogger specific actions
            if self.relogger_active:
                if res_type == "chests":
                    # Calcular cooldown dinÃ¢mico (paralelo)
                    wait_duration = self.pause_duration
                    try:
                        target_idx = self.current_stage_queue.index(found_target_id)
                        self.target_chest_index = target_idx + 1
                        
                        # O Grid de 50 baÃºs corre em paralelo:
                        # BaÃºs 1 a 30 (Ã­ndices 0 a 29) sÃ£o normais (Uncommon)
                        # BaÃºs 31 a 50 (Ã­ndices 30 a 49) sÃ£o de chefe (Rare)
                        if target_idx < 30:
                            estimated_secs = (target_idx + 1) * self.uncommon_chest_cooldown
                        else:
                            estimated_secs = (target_idx - 29) * self.rare_chest_cooldown
                        
                        # Adicionar 120s de margem de seguranÃ§a
                        estimated_secs += 120
                        wait_duration = max(self.pause_duration, estimated_secs)
                    except ValueError:
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
 
    # =====================================================================
    # Auto-Relogger Click Automation
    # =====================================================================
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
        """User clicked 'Item Collected' â€” cancel long countdown, apply safety delay, then relog."""
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
 
        self.lbl_bot_status.configure(
            text=f"Relogger Status: ACTIVE (PAUSED - Found {item_name})\nRelaunching game in {seconds_left}s...",
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
 
    def click_coordinate(self, key: str) -> None:
        pos = self.coords.get(key)
        if not pos:
            return
        x, y = pos[0], pos[1]
        
        # Set cursor and left mouse click down/up
        ctypes.windll.user32.SetCursorPos(x, y)
        time.sleep(0.02)
        ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0) # mouse left down
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0) # mouse left up
 
    # Safe exit cleanup
    def destroy(self) -> None:
        self.stop_relogger()
        self.stop_proxy()
        super().destroy()
 
    def on_closing(self) -> None:
        self.stop_proxy()
        self.destroy()
 
# =====================================================================
# Main execution entry
# =====================================================================
if __name__ == "__main__":
    # Ensure Windows console supports colors just in case
    if os.name == 'nt':
        os.system('color')
        
    app = PeekerGUI()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.destroy()
