import json
from pathlib import Path

# Definições base que precisam ser compartilhadas
ROOT = Path(__file__).parent.parent.resolve()
PEEKER_CONFIG_PATH = ROOT / "peeker_config.json"


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

class ConfigMixin:
    def load_peeker_config(self) -> None:
        if PEEKER_CONFIG_PATH.exists():
            try:
                data = json.loads(PEEKER_CONFIG_PATH.read_text(encoding="utf-8-sig"))
                self.coords = data.get("coords", getattr(self, "coords", {}))
                self.target_items = data.get("target_items", [])
                self.ignored_items = data.get("ignored_items", [])
                self.target_grades = data.get("target_grades", getattr(self, "target_grades", []))
                self.relogger_method = data.get("relogger_method", "process_restart")
                self.game_path = data.get("game_path", r"C:\Program Files (x86)\Steam\steamapps\common\TaskbarHero\TaskBarHero.exe")
                self.pause_duration = data.get("pause_duration", 110)
                self.discord_notify_enabled = data.get("discord_notify_enabled", False)
                self.discord_webhook_url = data.get("discord_webhook_url", "")
                self.discord_user_id = data.get("discord_user_id", "")
                self.trainer_auto_launch = data.get("trainer_auto_launch", False)
                self.trainer_path = data.get("trainer_path", str(ROOT / "TBH Trainer.exe"))
                self.relog_safety_delay = data.get("relog_safety_delay", 45)
                self.stage_1_clicks = data.get("stage_1_clicks", [])
                self.stage_2_clicks = data.get("stage_2_clicks", [])
                self.switcher_interval = data.get("switcher_interval", 20)
                self.max_chest_index = data.get("max_chest_index", 43)
                self.rare_chest_cooldown = data.get("rare_chest_cooldown", 420)
                self.uncommon_chest_cooldown = data.get("uncommon_chest_cooldown", 240)
                self.save_file_path = data.get("save_file_path", getattr(self, "save_file_path", ""))
                self.cleaner_clicks = data.get("cleaner_clicks", getattr(self, "cleaner_clicks", [(None, None), (None, None), (None, None)]))
                self.cleaner_interval = data.get("cleaner_interval", getattr(self, "cleaner_interval", 600))
            except Exception as e:
                print(f"[ERROR] Loading config: {e}")

    def save_peeker_config(self) -> None:
        try:
            data = {
                "coords": getattr(self, "coords", {}),
                "target_items": getattr(self, "target_items", []),
                "ignored_items": getattr(self, "ignored_items", []),
                "target_grades": getattr(self, "target_grades", []),
                "relogger_method": getattr(self, "relogger_method", "process_restart"),
                "game_path": getattr(self, "game_path", ""),
                "pause_duration": getattr(self, "pause_duration", 110),
                "discord_notify_enabled": getattr(self, "discord_notify_enabled", False),
                "discord_webhook_url": getattr(self, "discord_webhook_url", ""),
                "discord_user_id": getattr(self, "discord_user_id", ""),
                "trainer_auto_launch": getattr(self, "trainer_auto_launch", False),
                "trainer_path": getattr(self, "trainer_path", ""),
                "relog_safety_delay": getattr(self, "relog_safety_delay", 45),
                "stage_1_clicks": getattr(self, "stage_1_clicks", []),
                "stage_2_clicks": getattr(self, "stage_2_clicks", []),
                "switcher_interval": getattr(self, "switcher_interval", 20),
                "max_chest_index": getattr(self, "max_chest_index", 43),
                "rare_chest_cooldown": getattr(self, "rare_chest_cooldown", 420),
                "uncommon_chest_cooldown": getattr(self, "uncommon_chest_cooldown", 240),
                "save_file_path": getattr(self, "save_file_path", ""),
                "cleaner_clicks": getattr(self, "cleaner_clicks", [(None, None), (None, None), (None, None)]),
                "cleaner_interval": getattr(self, "cleaner_interval", 600)
            }
            PEEKER_CONFIG_PATH.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[ERROR] Saving config: {e}")
