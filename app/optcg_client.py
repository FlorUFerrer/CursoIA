"""Cliente para la API publica y gratuita de optcgapi.com (One Piece TCG)."""
import json
import urllib.request
from pathlib import Path

DEFAULT_SET_ID = "OP-01"
REQUEST_TIMEOUT = 10

# Snapshot local con las cartas de los 21 sets (bajado una sola vez con
# scripts/fetch_optcg_cards.py y commiteado al repo). El seed carga todo el
# catalogo desde aca al primer arranque; solo se le pega a la API en vivo
# como respaldo si aparece un set nuevo que todavia no esta en el archivo.
BUNDLED_SETS_JSON = Path(__file__).resolve().parent.parent / "data" / "optcg_all_sets.json"
BUNDLED_SETS_META_JSON = Path(__file__).resolve().parent.parent / "data" / "optcg_sets_meta.json"
_bundled_cache: dict | None = None

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


def list_all_sets() -> list[dict]:
    """Lista de sets sin pegarle a la API: lee el snapshot local commiteado
    (ver scripts/fetch_optcg_cards.py). Si no existe, cae al fetch en vivo."""
    if BUNDLED_SETS_META_JSON.exists():
        return json.loads(BUNDLED_SETS_META_JSON.read_text(encoding="utf-8"))
    return fetch_all_sets()


def fetch_set_cards(set_id: str) -> list[dict]:
    """Trae las cartas de un set en vivo. Se usa solo como respaldo para
    sets que todavia no estan en el snapshot local (ver load_bundled_set)."""
    url = f"https://optcgapi.com/api/sets/{set_id}/"
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:
        raw = json.load(resp)
    return normalize_set(raw)


def _load_bundled_sets() -> dict:
    global _bundled_cache
    if _bundled_cache is None:
        if BUNDLED_SETS_JSON.exists():
            _bundled_cache = json.loads(BUNDLED_SETS_JSON.read_text(encoding="utf-8"))
        else:
            _bundled_cache = {}
    return _bundled_cache


def load_bundled_set(set_id: str) -> list[dict] | None:
    """Cartas de un set desde el snapshot local commiteado (sin red), o
    None si ese set no esta incluido ahi."""
    return _load_bundled_sets().get(set_id)


def bundled_set_ids() -> list[str]:
    """Todos los set_id incluidos en el snapshot local, en el orden en que
    se guardaron (orden de lanzamiento)."""
    return list(_load_bundled_sets().keys())
