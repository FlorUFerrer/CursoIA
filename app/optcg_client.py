"""Cliente para la API publica y gratuita de optcgapi.com (One Piece TCG)."""
import json
import urllib.request
from pathlib import Path

DEFAULT_SET_ID = "OP-01"
REQUEST_TIMEOUT = 10

# Se usa solo si la API esta caida al arrancar (ver scripts/fetch_optcg_cards.py).
FALLBACK_JSON = Path(__file__).resolve().parent.parent / "data" / "optcg_op01_raw.json"

RARITY_LABELS = {
    "L": "Leader",
    "C": "Common",
    "UC": "Uncommon",
    "R": "Rare",
    "SR": "Super Rare",
    "SEC": "Secret Rare",
    "P": "Promo",
}

SKIP_MARKERS = ("(Parallel)", "(Box Topper)", "(Manga)", "(Alternate Art)")


def normalize_set(raw: list[dict]) -> list[dict]:
    """Filtra parallels/box toppers y se queda con una entrada por codigo."""
    seen: set[str] = set()
    cards = []
    for entry in raw:
        code = entry["card_set_id"]
        name = entry["card_name"]
        if code in seen:
            continue
        if any(marker in name for marker in SKIP_MARKERS):
            continue
        seen.add(code)
        cards.append(
            {
                "code": code,
                "name": name,
                "set_name": entry["set_id"],
                "rarity": RARITY_LABELS.get(entry["rarity"], entry["rarity"]),
                "market_price_usd": entry["market_price"],
                "image_url": entry["card_image"],
            }
        )
    return cards


def fetch_all_sets() -> list[dict]:
    """Lista de sets disponibles: [{'set_id': 'OP-01', 'set_name': 'Romance Dawn'}, ...]
    En el orden que los devuelve la API, que es el orden de lanzamiento."""
    url = "https://optcgapi.com/api/allSets/"
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:
        return json.load(resp)


def fetch_set_cards(set_id: str) -> list[dict]:
    """Trae las cartas de un set en vivo. Si falla y es el set por defecto
    (OP-01), usa el snapshot local en data/optcg_op01_raw.json como respaldo."""
    url = f"https://optcgapi.com/api/sets/{set_id}/"
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:
            raw = json.load(resp)
        return normalize_set(raw)
    except Exception:
        if set_id == DEFAULT_SET_ID and FALLBACK_JSON.exists():
            return json.loads(FALLBACK_JSON.read_text(encoding="utf-8"))
        raise
