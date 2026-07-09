import json
import urllib.request
import urllib.parse
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
MARKET_CACHE_PATH = ROOT / "market_cache.json"


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

class SteamMixin:
    def load_market_cache(self) -> None:
        """Carrega o cache de preços do arquivo local."""
        self.market_price_cache = {}
        cache_path = ROOT / "market_cache.json"
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    self.market_price_cache = json.load(f)
            except Exception:
                pass

    def save_market_cache(self) -> None:
        """Salva o cache de preços no arquivo local."""
        cache_path = ROOT / "market_cache.json"
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(self.market_price_cache, f, indent=2)
        except Exception:
            pass

    def fetch_steam_market_price(self, item_name: str, callback) -> None:
        """Busca o preço do item, respeitando o cooldown incondicional de 12 horas."""
        now = time.time()
        max_cache_age = 12 * 3600  # 12 horas em segundos
        # Se o item já foi consultado (com sucesso, erro ou indisponível) dentro de 12h, 
        # usa a resposta do cache de forma incondicional.
        if item_name in self.market_price_cache:
            item_data = self.market_price_cache[item_name]
            cached_time = item_data.get("timestamp", 0)
            cached_price = item_data.get("price", "N/A")
            if now - cached_time < max_cache_age:
                callback(cached_price)
                return
        # Caso contrário, dispara a thread para consultar a Steam
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
            # Salva o resultado (preço real ou N/A) no cache com o timestamp atual
            self.market_price_cache[item_name] = {
                "price": price_str,
                "timestamp": now
            }
            self.save_market_cache()
            self.after(0, lambda: callback(price_str))
        threading.Thread(target=worker, daemon=True).start()