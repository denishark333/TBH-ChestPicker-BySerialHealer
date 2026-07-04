from __future__ import annotations
 
import json
import os
import re
import shutil
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any
 
# Silence deprecation and user warnings to keep the console clean
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
 
# ANSI Colors for terminal output
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
 
C_DARK_RED = "\033[31m"
C_DARK_GREEN = "\033[32m"
C_DARK_YELLOW = "\033[33m"
C_DARK_BLUE = "\033[34m"
C_DARK_MAGENTA = "\033[35m"
C_DARK_CYAN = "\033[36m"
 
C_BRIGHT_GRAY = "\033[90m"
C_BRIGHT_RED = "\033[91m"
C_BRIGHT_GREEN = "\033[92m"
C_BRIGHT_YELLOW = "\033[93m"
C_BRIGHT_BLUE = "\033[94m"
C_BRIGHT_MAGENTA = "\033[95m"
C_BRIGHT_CYAN = "\033[96m"
C_BRIGHT_WHITE = "\033[97m"
 
C_RED = C_BRIGHT_RED
C_GREEN = C_BRIGHT_GREEN
C_YELLOW = C_BRIGHT_YELLOW
C_GRAY = C_BRIGHT_GRAY
C_CYAN = C_BRIGHT_CYAN
C_BLUE = C_BRIGHT_BLUE
C_MAGENTA = C_BRIGHT_MAGENTA
C_WHITE = C_BRIGHT_WHITE
 
GRADE_COLORS = {
    "COMMON": C_BRIGHT_GRAY,
    "UNCOMMON": C_DARK_GREEN,
    "RARE": C_DARK_BLUE,
    "LEGENDARY": C_DARK_YELLOW,
    "IMMORTAL": C_BRIGHT_RED,
    "ARCANA": C_DARK_MAGENTA,
    "BEYOND": C_DARK_CYAN,
    "CELESTIAL": C_BRIGHT_CYAN,
    "DIVINE": C_BRIGHT_YELLOW,
    "COSMIC": C_BRIGHT_MAGENTA,
    "BOSS": C_BRIGHT_BLUE
}
 
def get_grade_color(grade: str) -> str:
    return GRADE_COLORS.get(grade.upper(), C_BRIGHT_WHITE)
 
try:
    from mitmproxy import ctx
except Exception:
    ctx = None
 
ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
ITEMS_PATH = ROOT / "items.json"
 
ITEM_FIELD_RE = re.compile(r'\\?"itemId\\?"\s*:\s*(?P<item_id>\d+)(?!\d)')
REWARD_FIELD_RE = re.compile(r'(\\?"rewardItemId\\?"\s*:\s*)(?P<reward_id>\d+)(?!\d)')
 
items_db: dict[int, dict[str, Any]] = {}
if ITEMS_PATH.exists():
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                items_db[item["id"]] = item
        print(f"{C_GREEN}[PEEKER] Loaded {len(items_db)} items from items.json.{C_RESET}")
    except Exception as e:
        print(f"{C_RED}[PEEKER] Error loading items.json: {e}{C_RESET}")
else:
    print(f"{C_YELLOW}[PEEKER] Warning: items.json not found. Item names will not be resolved.{C_RESET}")
 
def get_item_info(item_id: int) -> dict[str, Any]:
    return items_db.get(item_id, {})
 
def get_item_display(item_id: int, colored: bool = True) -> str:
    info = get_item_info(item_id)
    if not info:
        return f"Unknown Item ({item_id})"
    
    name_dict = info.get("name")
    if isinstance(name_dict, dict):
        name = name_dict.get("en-US", name_dict.get("en", "Unknown Name"))
    else:
        name = "Unknown Name"
        
    grade = info.get("grade", "COMMON")
    if "boss" in name.lower():
        grade = "BOSS"
        
    color = get_grade_color(grade) if colored else C_WHITE
    
    level_str = f" [Lv. {info['level']}]" if info.get("level") is not None else ""
    return f"{color}{name}{level_str} (ID: {item_id}) [{grade}]{C_RESET}"


def collect_item_ids(node: Any) -> list[int]:
    found: list[int] = []
    if isinstance(node, dict):
        item_id = node.get("itemId")
        if isinstance(item_id, int):
            found.append(item_id)
        for value in node.values():
            found.extend(collect_item_ids(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(collect_item_ids(value))
    return found


def collect_section_item_ids(node: Any, section_name: str) -> list[int]:
    found: list[int] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == section_name:
                found.extend(collect_item_ids(value))
            found.extend(collect_section_item_ids(value, section_name))
    elif isinstance(node, list):
        for value in node:
            found.extend(collect_section_item_ids(value, section_name))
    return found
 
class ChestPeekerHook:
    def __init__(self) -> None:
        try:
            self.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        except Exception:
            self.config = {}
        
        self.url_contains = self.config.get("url_contains", ["/backend-function/base/v1"])
        self.only_post = self.config.get("only_post", True)
        self.require_boxes_marker = self.config.get("require_boxes_marker", True)
        
        print(f"{C_CYAN}[PEEKER] Mitmproxy peeker hook loaded.{C_RESET}")
        self.silence_asyncio_errors()
        
        port = load_port()
        set_system_proxy(True, port)
 
    def done(self) -> None:
        port = load_port()
        set_system_proxy(False, port)
 
    def silence_asyncio_errors(self) -> None:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            
            def custom_handler(loop, context):
                exception = context.get("exception")
                if isinstance(exception, OSError) and getattr(exception, "winerror", 0) in (10053, 10054):
                    return
                loop.default_exception_handler(context)
                
            loop.set_exception_handler(custom_handler)
        except Exception:
            pass
 
    def request(self, flow: Any) -> None:
        request = flow.request
        if request.pretty_host in ("127.0.0.1", "localhost") and request.path == "/proxy.pac":
            try:
                pdata = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
            except Exception:
                pdata = {}
            port = int(pdata.get("listen_port", 8877))
 
            pac_content = f"""function FindProxyForURL(url, host) {{
    if (dnsDomainIs(host, "script.google.com") ||
        dnsDomainIs(host, "script.googleusercontent.com") ||
        dnsDomainIs(host, "nugem.io") ||
        dnsDomainIs(host, "taskbarhero.org") ||
        shExpMatch(host, "*tbh*") ||
        shExpMatch(host, "*taskbarhero*") ||
        shExpMatch(host, "*nugem*")) {{
        return "PROXY 127.0.0.1:{port}";
    }}
    return "DIRECT";
}}
"""
            from mitmproxy import http
            flow.response = http.Response.make(
                200,
                pac_content.encode("utf-8"),
                {"Content-Type": "application/x-ns-proxy-autoconfig"}
            )
 
    def response(self, flow: Any) -> None:
        request = flow.request
        response = flow.response
 
        if self.only_post and request.method.upper() != "POST":
            return
 
        pretty_url = getattr(request, "pretty_url", "") or getattr(request, "url", "")
        if self.url_contains and not any(marker in pretty_url for marker in self.url_contains):
            return
 
        try:
            body = response.get_text(strict=False)
        except Exception:
            return
 
        if body is None:
            return
 
        body_preview = body[:200].replace('\n', ' ').replace('\r', '')
        print(f"__PEEK_DEBUG__:{len(body)}:{body_preview}", flush=True)
 
        if response.status_code >= 500:
            print(f"{C_RED}[PEEKER] ⚠ Server error: HTTP {response.status_code}{C_RESET}")
            print(f"__PEEK_RESULT__:error:{response.status_code}", flush=True)
            return
 
        if body and len(body) < 1000:
            body_lower = body.lower()
            if "invalid steam" in body_lower or "invalid session" in body_lower:
                print(f"{C_RED}[PEEKER] ⚠ Authentication error detected{C_RESET}")
                print(f"__PEEK_RESULT__:error:401", flush=True)
                return
 
        is_exchange = "removed" in body and "added" in body
        is_offering = False
        exchange_added_ids: list[int] = []
        exchange_removed_ids: list[int] = []
        if is_exchange:
            pretty_url = getattr(request, "pretty_url", "") or getattr(request, "url", "") or ""
            pretty_url_lower = pretty_url.lower()
            request_body_lower = ""
            try:
                request_body_lower = (request.get_text(strict=False) or "").lower()
            except Exception:
                pass
            is_offering = (
                "offering" in pretty_url_lower or "offer" in pretty_url_lower or
                "offering" in request_body_lower or "offer" in request_body_lower
            )
            try:
                parsed_body = json.loads(body)
            except Exception:
                parsed_body = None
            if parsed_body is not None:
                exchange_added_ids = sorted(set(iid for iid in collect_section_item_ids(parsed_body, "added") if get_item_info(iid)))
                exchange_removed_ids = sorted(set(iid for iid in collect_section_item_ids(parsed_body, "removed") if get_item_info(iid)))
 
        chests_found = []
        direct_drops_found = []
        
        OBJECT_RE = re.compile(r'\{([^{}]+)\}')
        for obj_match in OBJECT_RE.finditer(body):
            obj_content = obj_match.group(1)
            item_match = ITEM_FIELD_RE.search(obj_content)
            reward_match = REWARD_FIELD_RE.search(obj_content)
            
            if item_match:
                item_id = int(item_match.group("item_id"))
                if reward_match:
                    reward_id = int(reward_match.group("reward_id"))
                    chests_found.append((item_id, reward_id))
                else:
                    if get_item_info(item_id) and item_id not in direct_drops_found:
                        direct_drops_found.append(item_id)
 
        if chests_found:
            print("\n" + "="*80)
            print(f"{C_BOLD}{C_CYAN}[PEEKER] DETECTED UPCOMING CHEST DROPS (Original, Unmodified){C_RESET}")
            print("="*80)
            for idx, (chest_id, reward_id) in enumerate(chests_found, 1):
                chest_str = get_item_display(chest_id, colored=False)
                reward_str = get_item_display(reward_id)
                print(f" {C_BOLD}{idx}.{C_RESET} Chest: {chest_str}")
                print(f"    └─ Drop: {reward_str}")
            print("="*80 + "\n")
            print(f"__PEEK_RESULT__:chests:{json.dumps(chests_found)}", flush=True)
 
        if direct_drops_found and not is_offering:
            print("\n" + "="*80)
            print(f"{C_BOLD}{C_GREEN}[PEEKER] DETECTED STAGE CLEAR / BOSS REWARDS (Hadiah Selesai Stage){C_RESET}")
            print("="*80)
            for idx, item_id in enumerate(direct_drops_found, 1):
                item_str = get_item_display(item_id)
                print(f" {C_BOLD}{idx}.{C_RESET} Drop: {item_str}")
            print("="*80 + "\n")
            print(f"__PEEK_RESULT__:direct:{json.dumps(direct_drops_found)}", flush=True)

        if is_exchange and (exchange_added_ids or exchange_removed_ids):
            print(f"__PEEK_RESULT__:exchange:{json.dumps({'added': exchange_added_ids, 'removed': exchange_removed_ids, 'offering': is_offering})}", flush=True)
        
        if is_exchange and is_offering:
            reward_id = exchange_added_ids[0] if exchange_added_ids else None
            if reward_id is None:
                added_idx = body.find('"added"')
                if added_idx == -1:
                    added_idx = body.find('\\"added\\"')
                if added_idx != -1:
                    match = ITEM_FIELD_RE.search(body, added_idx)
                    if match:
                        reward_id = int(match.group("item_id"))
            if reward_id is not None:
                print("\n" + "="*80)
                print(f"{C_BOLD}{C_CYAN}[PEEKER] DETECTED SYNTHESIS / CUBE OFFERING RESULT{C_RESET}")
                print("="*80)
                reward_str = get_item_display(reward_id)
                print(f" Result Drop: {reward_str}")
                print("="*80 + "\n")
                print(f"__PEEK_RESULT__:synthesis:{reward_id}", flush=True)
 
        all_seen_ids = set()
        for m in ITEM_FIELD_RE.finditer(body):
            try:
                iid = int(m.group("item_id"))
                if get_item_info(iid):
                    all_seen_ids.add(iid)
            except Exception:
                pass
        
        if all_seen_ids:
            chest_reward_ids = set(r for _, r in chests_found)
            chest_box_ids = set(c for c, _ in chests_found)
            direct_ids = set(direct_drops_found)
            new_seen = all_seen_ids - chest_reward_ids - chest_box_ids - direct_ids
            if new_seen:
                print(f"__PEEK_RESULT__:seen:{json.dumps(sorted(new_seen))}", flush=True)
 
def set_system_proxy(enabled: bool, port: int = 8877) -> None:
    if os.name != 'nt':
        return
    import winreg
    import ctypes
    try:
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"127.0.0.1:{port}")
                try:
                    winreg.DeleteValue(key, "AutoConfigURL")
                except FileNotFoundError:
                    pass
                print(f"{C_GREEN}[PEEKER] Windows system proxy enabled: 127.0.0.1:{port}{C_RESET}")
            else:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                print(f"{C_YELLOW}[PEEKER] Windows system proxy disabled.{C_RESET}")
        
        INTERNET_OPTION_SETTINGS_CHANGED = 39
        INTERNET_OPTION_REFRESH = 37
        try:
            internet_set_option = ctypes.windll.wininet.InternetSetOptionW
            internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
            internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)
        except Exception:
            pass
    except Exception as e:
        print(f"{C_RED}[PEEKER] Failed to set system proxy: {e}{C_RESET}")
 
def load_port() -> int:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return 8877
    return int(data.get("listen_port", 8877))
 
def main() -> int:
    if os.name == 'nt':
        os.system('color')
        
    port = load_port()
    common_args = [
        "-q",
        "-s",
        str(Path(__file__).resolve()),
        "--listen-port",
        str(port),
        "--flow-detail",
        "0",
        "--set",
        "block_global=false",
    ]
 
    mitmdump = shutil.which("mitmdump")
    if mitmdump:
        command = [mitmdump, *common_args]
    else:
        command = [
            sys.executable,
            "-c",
            "from mitmproxy.tools.main import mitmdump; mitmdump()",
            *common_args,
        ]
 
    set_system_proxy(True, port)
    
    print(f"{C_GREEN}Starting Chest Peeker on 127.0.0.1:{port}{C_RESET}")
    print(f"{C_GRAY}This script will show the original game drops without changing them.{C_RESET}")
    print(f"{C_GRAY}Press Ctrl+C to stop.{C_RESET}")
    
    try:
        return subprocess.call(command, cwd=str(ROOT))
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[PEEKER] Stopping...{C_RESET}")
        return 0
    finally:
        set_system_proxy(False, port)
 
addons = [ChestPeekerHook()]
 
if __name__ == "__main__" and len(sys.argv) == 1:
    try:
        sys.exit(main())
    except SystemExit:
        pass
