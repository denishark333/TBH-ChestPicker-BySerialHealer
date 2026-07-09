import os
import sys
import json
import time
import datetime
import re
from pathlib import Path
from typing import Any
import customtkinter as ctk
from tkinter import filedialog
import tkinter as tk
from PIL import Image

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

class GuiMixin:
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
        for name in ["Dashboard", "Targets & Alerts", "Loot Progress", "Save File", "Settings", "Console Log"]:
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
        self.tab_mouse_auto = ctk.CTkFrame(self.content_area, fg_color="transparent")
        
        self.tab_frames["Dashboard"] = self.tab_dashboard
        self.tab_frames["Targets & Alerts"] = self.tab_targets
        self.tab_save = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.tab_frames["Save File"] = self.tab_save
        self.tab_loot_progress = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.tab_frames["Loot Progress"] = self.tab_loot_progress
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
        self.build_save_tab()
        self.build_loot_progress_tab()
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
        
        lbl_bot = ctk.CTkLabel(self.bot_frame, text="Master Automation Controls", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl_bot.pack(anchor="w", padx=15, pady=(8, 10))
        
        auto_grid = ctk.CTkFrame(self.bot_frame, fg_color="transparent")
        auto_grid.pack(fill="both", expand=True, padx=15, pady=(0, 8))
        auto_grid.grid_columnconfigure(0, weight=1)
        auto_grid.grid_columnconfigure(1, weight=1)
        auto_grid.grid_columnconfigure(2, weight=1)
        
        # 1. AutoRelogger
        col_relogger = ctk.CTkFrame(auto_grid, fg_color="transparent")
        col_relogger.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.btn_bot = ctk.CTkButton(col_relogger, text="Start Auto-Relogger", fg_color="#2ecc71", hover_color="#27ae60", text_color=COLOR_TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=self.toggle_relogger, height=36)
        self.btn_bot.pack(fill="x", pady=(0, 4))
        self.lbl_bot_status = ctk.CTkLabel(col_relogger, text="Status: Inactive\n[F9] to STOP", text_color=COLOR_MUTED, font=ctk.CTkFont(size=10, slant="italic"), justify="left")
        self.lbl_bot_status.pack(anchor="w")
        
        # 2. Stage Switcher
        col_switcher = ctk.CTkFrame(auto_grid, fg_color="transparent")
        col_switcher.grid(row=0, column=1, sticky="nsew", padx=4)
        self.btn_toggle_switcher = ctk.CTkButton(col_switcher, text="Start Stage Switcher", fg_color="#3498db", hover_color="#2980b9", text_color=COLOR_TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=self.toggle_stage_switcher, height=36)
        self.btn_toggle_switcher.pack(fill="x", pady=(0, 4))
        self.lbl_switcher_status = ctk.CTkLabel(col_switcher, text="Status: Stopped", font=ctk.CTkFont(size=10, slant="italic"), text_color=COLOR_MUTED, justify="left")
        self.lbl_switcher_status.pack(anchor="w")
        
        # 3. Inventory Cleaner
        col_cleaner = ctk.CTkFrame(auto_grid, fg_color="transparent")
        col_cleaner.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
        self.btn_toggle_cleaner = ctk.CTkButton(col_cleaner, text="Start Auto-Stash", fg_color="#9b59b6", hover_color="#8e44ad", text_color=COLOR_TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=self.toggle_cleaner, height=36)
        self.btn_toggle_cleaner.pack(fill="x", pady=(0, 4))
        
        # Extra relogger buttons
        self.btn_force_relaunch = ctk.CTkButton(self.bot_frame, text="Force Relaunch Game", fg_color="#3498db", hover_color="#2980b9", text_color=COLOR_TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=self.force_relaunch_game, height=32)
        self.btn_force_relaunch.pack(fill="x", padx=15, pady=(4, 4))
        
        self.btn_item_collected = ctk.CTkButton(self.bot_frame, text="✅ Item Collected → Resume / Relog", fg_color="#e67e22", hover_color="#d35400", text_color=COLOR_TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=self.skip_to_safety_relog, height=32)
        self.btn_item_collected.pack(fill="x", padx=15, pady=(0, 8))
        self.btn_item_collected.pack_forget()
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

    def build_save_tab(self) -> None:
        self.save_scroll = ctk.CTkScrollableFrame(
            self.tab_save,
            fg_color="transparent",
            scrollbar_button_color=COLOR_PRIMARY,
            scrollbar_button_hover_color=COLOR_HOVER
        )
        self.save_scroll.pack(fill="both", expand=True, padx=12, pady=12)
        self.save_content = ctk.CTkFrame(self.save_scroll, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.save_content.pack(fill="x", padx=4, pady=4)
        lbl_save_title = ctk.CTkLabel(
            self.save_content,
            text="TBH Save File Integration (Real-time Chest Tracker)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT
        )
        lbl_save_title.pack(anchor="w", padx=15, pady=(10, 5))
        lbl_save_desc = ctk.CTkLabel(
            self.save_content,
            text="Decrypts the local SaveFile_Live.es3 to monitor chest openings in real-time.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_MUTED
        )
        lbl_save_desc.pack(anchor="w", padx=15, pady=(0, 10))
        lbl_copy_hint = ctk.CTkLabel(
            self.save_content,
            text="COPY TO PATHFILE (Click to copy):\n%USERPROFILE%\\AppData\\LocalLow\\TesseractStudio\\TaskbarHero\\SaveFile_Live.es3",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f1c40f",
            cursor="hand2",
            justify="center"
        )
        lbl_copy_hint.pack(anchor="center", padx=15, pady=(5, 10))
        def on_copy_click(event):
            self.clipboard_clear()
            self.clipboard_append(r"%USERPROFILE%\AppData\LocalLow\TesseractStudio\TaskbarHero\SaveFile_Live.es3")
            self.update()
            lbl_copy_hint.configure(text="✓ Copied to Clipboard!", text_color="#2ecc71")
            self.after(2000, lambda: lbl_copy_hint.configure(
                text="COPY TO PATHFILE (Click to copy):\n%USERPROFILE%\\AppData\\LocalLow\\TesseractStudio\\TaskbarHero\\SaveFile_Live.es3",
                text_color="#f1c40f"
            ))
            self.append_log("[INFO] Path copied to clipboard.\n")
        lbl_copy_hint.bind("<Button-1>", on_copy_click)
        lbl_save_path = ctk.CTkLabel(
            self.save_content,
            text="SaveFile_Live.es3 Path:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_MUTED
        )
        lbl_save_path.pack(anchor="w", padx=15, pady=(5, 2))
        save_path_row = ctk.CTkFrame(self.save_content, fg_color="transparent")
        save_path_row.pack(fill="x", padx=15, pady=(0, 15))
        self.entry_save_path = ctk.CTkEntry(
            save_path_row,
            fg_color=COLOR_ENTRY_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="Browse path to SaveFile_Live.es3...",
            font=ctk.CTkFont(size=11)
        )
        self.entry_save_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_save_path.insert(0, self.save_file_path)
        self.entry_save_path.bind("<KeyRelease>", self.on_save_path_typed)
        self.btn_browse_save = ctk.CTkButton(
            save_path_row,
            text="Browse",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=70,
            command=self.browse_save_path
        )
        self.btn_browse_save.pack(side="right")

    def build_loot_progress_tab(self) -> None:
        self.loot_disclaimer_frame = ctk.CTkFrame(self.tab_loot_progress, fg_color="transparent")
        self.loot_disclaimer_frame.pack(fill="x", padx=12, pady=(12, 0))
        
        lbl_disclaimer1 = ctk.CTkLabel(
            self.loot_disclaimer_frame,
            text="The estimates and calculations are based on the average times we analyzed.",
            font=ctk.CTkFont(size=13, weight="bold", slant="italic"),
            text_color="#888888"
        )
        lbl_disclaimer1.pack(anchor="center")
        
        lbl_disclaimer2 = ctk.CTkLabel(
            self.loot_disclaimer_frame,
            text="For greater accuracy, keep in mind that we assume the stage will be completed in approximately 60 seconds.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#666666"
        )
        lbl_disclaimer2.pack(anchor="center")
        
        self.loot_frame = ctk.CTkFrame(self.tab_loot_progress, fg_color="transparent")
        self.loot_frame.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Split layout: StageBoss on left, Normal on right
        self.frame_sb_progress = ctk.CTkFrame(self.loot_frame, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.frame_sb_progress.pack(side="left", fill="both", expand=True, padx=(0, 6))
        
        lbl_sb = ctk.CTkLabel(
            self.frame_sb_progress,
            text="StageBoss Chests (Raros)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_PRIMARY
        )
        lbl_sb.pack(anchor="w", padx=15, pady=(10, 5))
        
        self.scroll_sb_progress = ctk.CTkScrollableFrame(
            self.frame_sb_progress,
            fg_color=COLOR_BG,
            scrollbar_button_color=COLOR_PRIMARY,
            scrollbar_button_hover_color=COLOR_HOVER
        )
        self.scroll_sb_progress.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.frame_norm_progress = ctk.CTkFrame(self.loot_frame, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.frame_norm_progress.pack(side="right", fill="both", expand=True, padx=(6, 0))
        
        lbl_norm = ctk.CTkLabel(
            self.frame_norm_progress,
            text="Normal Chests (Comuns)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT
        )
        lbl_norm.pack(anchor="w", padx=15, pady=(10, 5))
        
        self.scroll_norm_progress = ctk.CTkScrollableFrame(
            self.frame_norm_progress,
            fg_color=COLOR_BG,
            scrollbar_button_color=COLOR_PRIMARY,
            scrollbar_button_hover_color=COLOR_HOVER
        )
        self.scroll_norm_progress.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def update_loot_progress_ui(self) -> None:
        if not hasattr(self, 'scroll_sb_progress') or not self.scroll_sb_progress.winfo_exists():
            return
            
        # Clear scrollables
        for widget in self.scroll_sb_progress.winfo_children():
            widget.destroy()
        for widget in self.scroll_norm_progress.winfo_children():
            widget.destroy()
            
        self.stageboss_progress_widgets.clear()
        self.normal_progress_widgets.clear()
        
        # Populate StageBoss
        for idx, item in enumerate(self.stageboss_chest_queue):
            item_id = item["item_id"]
            is_unreachable = item.get("is_unreachable", False)
            info = self.get_item_info_by_id(item_id)
            name = self.get_item_name(info, f"Item ({item_id})")
            grade = info.get("grade", "COMMON")
            color = GRADE_COLORS.get(grade.upper(), COLOR_TEXT)
            
            card = ctk.CTkFrame(
                self.scroll_sb_progress, 
                fg_color=COLOR_FRAME if not is_unreachable else "#151518", 
                border_color=COLOR_BORDER if not is_unreachable else "#252528", 
                border_width=1, 
                height=36
            )
            card.pack(fill="x", padx=6, pady=3)
            card.pack_propagate(False)
            
            lbl_status = ctk.CTkLabel(card, text="[  ]", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=COLOR_MUTED)
            lbl_status.pack(side="left", padx=10)
            
            lbl_idx = ctk.CTkLabel(card, text=f"#{idx+1}", font=ctk.CTkFont(family="Consolas", size=11), text_color=COLOR_MUTED)
            lbl_idx.pack(side="left", padx=(0, 10))
            
            if is_unreachable:
                lbl_unreach = ctk.CTkLabel(card, text="[⚠️ UNREACHABLE]", font=ctk.CTkFont(size=10, weight="bold"), text_color="#e74c3c")
                lbl_unreach.pack(side="right", padx=10)
                
            lbl_name = ctk.CTkLabel(
                card, 
                text=name, 
                font=ctk.CTkFont(size=12, weight="bold"), 
                text_color=color if not is_unreachable else COLOR_MUTED
            )
            lbl_name.pack(side="left", fill="x", expand=True, anchor="w")
            
            self.stageboss_progress_widgets.append({
                "card": card,
                "lbl_status": lbl_status,
                "lbl_name": lbl_name,
                "name": name,
                "id": item_id,
                "color": color
            })
            
        # Populate Normal
        for idx, item in enumerate(self.normal_chest_queue):
            item_id = item["item_id"]
            info = self.get_item_info_by_id(item_id)
            name = self.get_item_name(info, f"Item ({item_id})")
            grade = info.get("grade", "COMMON")
            color = GRADE_COLORS.get(grade.upper(), COLOR_TEXT)
            
            card = ctk.CTkFrame(self.scroll_norm_progress, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1, height=36)
            card.pack(fill="x", padx=6, pady=3)
            card.pack_propagate(False)
            
            lbl_status = ctk.CTkLabel(card, text="[  ]", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=COLOR_MUTED)
            lbl_status.pack(side="left", padx=10)
            
            lbl_idx = ctk.CTkLabel(card, text=f"#{idx+1}", font=ctk.CTkFont(family="Consolas", size=11), text_color=COLOR_MUTED)
            lbl_idx.pack(side="left", padx=(0, 10))
            
            lbl_name = ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=12, weight="bold"), text_color=color)
            lbl_name.pack(side="left", fill="x", expand=True, anchor="w")
            
            self.normal_progress_widgets.append({
                "card": card,
                "lbl_status": lbl_status,
                "lbl_name": lbl_name,
                "name": name,
                "id": item_id,
                "color": color
            })

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
        lbl_cal = ctk.CTkLabel(self.calib_frame, text="Auto-Relogger Setup (F8 Calibrate | F9 Stop)", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl_cal.pack(anchor="w", padx=15, pady=(8, 5))
        self.relogger_method_var = ctk.StringVar(value="Process Restart")
        self.relogger_method = "process_restart"
        self.restart_container = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        self.restart_container.pack(fill="x", padx=15, pady=5)
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
        self.clicks_container = None
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
        self.build_stage_switcher_settings_ui()
        self.build_inventory_cleaner_settings_ui()

    def build_stage_switcher_settings_ui(self):
        frame = ctk.CTkFrame(self.settings_scroll, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        frame.pack(fill="x", padx=4, pady=12)
        
        lbl_title = ctk.CTkLabel(frame, text="Stage Switcher Setup", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl_title.pack(anchor="w", padx=15, pady=(8, 0))
        lbl_switch_desc = ctk.CTkLabel(frame, text="Automatically switch between two stages (e.g. 1-3 to 1-2) at a set interval.\nHow to Calibrate: Click a button below, then left-click inside the game to record points. Right-click to stop recording.", text_color=COLOR_MUTED, font=ctk.CTkFont(size=11, slant="italic"), justify="left")
        lbl_switch_desc.pack(anchor="w", padx=15, pady=(0, 10))
        
        row_int = ctk.CTkFrame(frame, fg_color="transparent")
        row_int.pack(fill="x", padx=15, pady=(0, 5))
        ctk.CTkLabel(row_int, text="Switch Interval (seconds):", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED).pack(side="left", padx=(0, 10))
        self.entry_switcher_interval = ctk.CTkEntry(row_int, width=60, height=24, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT)
        self.entry_switcher_interval.pack(side="left")
        self.entry_switcher_interval.insert(0, str(getattr(self, "switcher_interval", 20)))
        
        # Stage 1
        s1_frame = ctk.CTkFrame(frame, fg_color="transparent")
        s1_frame.pack(fill="x", padx=15, pady=5)
        self.btn_calib_1 = ctk.CTkButton(s1_frame, text="Calibrate Stage 1", fg_color=COLOR_PRIMARY, hover_color=COLOR_HOVER, text_color=COLOR_TEXT, font=ctk.CTkFont(weight="bold"), command=lambda: self.calibrate_stage(1))
        self.btn_calib_1.pack(side="left", padx=(0, 10))
        self.lbl_calib_1_status = ctk.CTkLabel(s1_frame, text=f"Stage 1: {len(self.stage_1_clicks)} clicks saved", text_color=COLOR_MUTED)
        self.lbl_calib_1_status.pack(side="left")
        
        # Stage 2
        s2_frame = ctk.CTkFrame(frame, fg_color="transparent")
        s2_frame.pack(fill="x", padx=15, pady=(5, 10))
        self.btn_calib_2 = ctk.CTkButton(s2_frame, text="Calibrate Stage 2", fg_color=COLOR_PRIMARY, hover_color=COLOR_HOVER, text_color=COLOR_TEXT, font=ctk.CTkFont(weight="bold"), command=lambda: self.calibrate_stage(2))
        self.btn_calib_2.pack(side="left", padx=(0, 10))
        self.lbl_calib_2_status = ctk.CTkLabel(s2_frame, text=f"Stage 2: {len(self.stage_2_clicks)} clicks saved", text_color=COLOR_MUTED)
        self.lbl_calib_2_status.pack(side="left")
        
    def build_inventory_cleaner_settings_ui(self):
        cleaner_card = ctk.CTkFrame(self.settings_scroll, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        cleaner_card.pack(fill="x", padx=4, pady=(0, 12))
        lbl_clean = ctk.CTkLabel(cleaner_card, text="Auto-Stash / Inventory Cleaner (Left-Click Calibrate)", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl_clean.pack(anchor="w", padx=15, pady=(10, 5))
        lbl_clean_desc = ctk.CTkLabel(cleaner_card, text="Periodically clicks up to 3 coordinates to move items to your Stash (e.g., clicking 'Store All').\nHow to Calibrate: Click a button below, hover your mouse over the game, and Left Click to register the point (Right Click to Cancel).\n\nNOTE: Coordinates are saved, but recalibrate if you move the game window!\n\nPRO TIP: For perfect AFK framing, keep 3 panels open simultaneously in-game:\nLeft = Stash, Center = Inventory, Right = Stage Portal.", text_color=COLOR_MUTED, font=ctk.CTkFont(size=11, slant="italic"), justify="left")
        lbl_clean_desc.pack(anchor="w", padx=15, pady=(0, 10))
        
        row_clean_int = ctk.CTkFrame(cleaner_card, fg_color="transparent")
        row_clean_int.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkLabel(row_clean_int, text="Cleanup Interval (seconds):", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED).pack(side="left", padx=(0, 10))
        self.entry_cleaner_interval = ctk.CTkEntry(row_clean_int, width=60, height=24, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT)
        self.entry_cleaner_interval.pack(side="left")
        saved_interval = str(getattr(self, "cleaner_interval", 600))
        self.entry_cleaner_interval.insert(0, saved_interval)
        
        cal_frame = ctk.CTkFrame(cleaner_card, fg_color="transparent")
        cal_frame.pack(fill="x", padx=15, pady=(0, 10))
        for i in range(3):
            btn = ctk.CTkButton(cal_frame, text=f"Calibrate Click {i+1}", fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER, border_color=COLOR_BORDER, border_width=1, text_color=COLOR_TEXT, width=120, command=lambda idx=i: self.trigger_cleaner_calibration(idx))
            btn.pack(side="left", padx=(0, 10))
        
        self.lbl_cleaner_cal_status = ctk.CTkLabel(cleaner_card, text="No clicks set yet.", text_color=COLOR_MUTED, font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_cleaner_cal_status.pack(anchor="w", padx=15, pady=(0, 10))

    def build_stage_switcher_dashboard_ui(self):
        self.switcher_frame = ctk.CTkFrame(self.sidebar, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.switcher_frame.pack(side="bottom", fill="x", padx=12, pady=(0, 12))
        lbl = ctk.CTkLabel(self.switcher_frame, text="Stage Switcher", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT)
        lbl.pack(anchor="w", padx=10, pady=(6, 8))
        
        row_interval = ctk.CTkFrame(self.switcher_frame, fg_color="transparent")
        row_interval.pack(fill="x", padx=10, pady=(0, 6))
        lbl_interval = ctk.CTkLabel(row_interval, text="Interval (s):", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_MUTED)
        lbl_interval.pack(side="left", padx=(0, 5))
        self.entry_switcher_interval = ctk.CTkEntry(row_interval, width=40, height=24, fg_color=COLOR_ENTRY_BG, border_color=COLOR_BORDER, text_color=COLOR_TEXT)
        self.entry_switcher_interval.pack(side="left")
        self.entry_switcher_interval.insert(0, str(getattr(self, "switcher_interval", 20)))
        
        self.btn_toggle_switcher = ctk.CTkButton(self.switcher_frame, text="START SWITCHER", fg_color="#2ecc71", hover_color="#27ae60", text_color=COLOR_TEXT, font=ctk.CTkFont(size=11, weight="bold"), command=self.toggle_stage_switcher, height=32)
        self.btn_toggle_switcher.pack(fill="x", padx=10, pady=(0, 6))
        

        self.btn_switcher_item_collected = ctk.CTkButton(self.switcher_frame, text="✅ Item Collected → Resume", fg_color="#e67e22", hover_color="#d35400", text_color=COLOR_TEXT, font=ctk.CTkFont(size=10, weight="bold"), command=self.skip_to_switcher_safety_resume, height=28)
        self.btn_switcher_item_collected.pack(fill="x", padx=10, pady=(0, 6))
        self.btn_switcher_item_collected.pack_forget()
        
        self.lbl_switcher_status = ctk.CTkLabel(self.switcher_frame, text="Status: Stopped", font=ctk.CTkFont(size=10, slant="italic"), text_color=COLOR_MUTED)

        self.lbl_switcher_status.pack(anchor="w", padx=10, pady=(0, 6))

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
        self.alert_banner_label.configure(text=f"Alert: {item_name or 'Target detected'} • {(grade or 'UNKNOWN').upper()}", text_color=color)
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
        self.left_content_frame.grid_rowconfigure(1, weight=0)
        self.left_content_frame.grid_rowconfigure(2, weight=1, minsize=360)
        
        
        # 1. Proxy Controls Panel
        self.proxy_frame = ctk.CTkFrame(self.left_content_frame, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.proxy_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 12))
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
        self.calib_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(6, 0), pady=(0, 12))
        lbl_cal = ctk.CTkLabel(self.calib_frame, text="Auto-Relogger Setup (F8 Calibrate | F9 Stop)", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT)
        lbl_cal.pack(anchor="w", padx=15, pady=(8, 5))
        # Relogger Method Selector
        self.relogger_method_var = ctk.StringVar(value="Process Restart")
        self.relogger_method = "process_restart"
        # 2a. Process Restart UI Container
        self.restart_container = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        self.restart_container.pack(fill="x", padx=15, pady=5)
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
        self.clicks_container = None
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
        self.build_stage_switcher_settings_ui()
        # 3. Auto-Relogger Actions Frame
        self.bot_frame = ctk.CTkFrame(self.left_content_frame, fg_color=COLOR_FRAME, border_color=COLOR_BORDER, border_width=1)
        self.bot_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 6), pady=(0, 12))
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
            text="✅ Item Collected → Relog Now",
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
        self.filter_tabview.grid(row=2, column=1, sticky="nsew", padx=(6, 0), pady=(0, 12))
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
            actions_frame, text="Add to Targets 🎯",
            fg_color=COLOR_SECONDARY, hover_color=COLOR_SEC_HOVER,
            command=self.add_target_item
        )
        self.btn_add_filter.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        self.btn_add_ignore = ctk.CTkButton(
            actions_frame, text="Add to Ignore List ⛔",
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
        lbl_t_title = ctk.CTkLabel(targets_panel, text="Active Target List 🎯", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_PRIMARY)
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
        lbl_i_title = ctk.CTkLabel(ignores_panel, text="Active Ignore List ⛔", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_PRIMARY)
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
            text="⚠️ Note: Soulstones are automatically EXCLUDED from grade-based matching to prevent useless stops.",
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
            placeholder_text="Right-click profile → Copy User ID",
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
            self.txt_log.insert("end", "   └─ Drop: ")
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
        self.build_stage_switcher_settings_ui()

    def update_relogger_ui_visibility(self) -> None:
        if self.relogger_method == "process_restart":
            if hasattr(self, 'clicks_container') and self.clicks_container and self.clicks_container.winfo_exists():
                self.clicks_container.pack_forget()
            if hasattr(self, 'restart_container') and self.restart_container.winfo_exists():
                self.restart_container.pack(fill="x", padx=15, pady=5)
        else:
            if hasattr(self, 'restart_container') and self.restart_container.winfo_exists():
                self.restart_container.pack_forget()
            if hasattr(self, 'clicks_container') and self.clicks_container and self.clicks_container.winfo_exists():
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














