import json
import re
from pathlib import Path
from typing import Any
import customtkinter as ctk
from PIL import Image

ROOT = Path(__file__).parent.parent.resolve()
ITEMS_PATH = ROOT / "items.json"


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

class DatabaseMixin:
    def load_items_db(self) -> None:
        if ITEMS_PATH.exists():
            try:
                with open(ITEMS_PATH, "r", encoding="utf-8") as f:
                    self.items_db = json.load(f)
            except Exception as e:
                print(f"Error loading items.json: {e}")

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