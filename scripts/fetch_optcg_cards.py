"""Regenera el snapshot local data/optcg_op01_raw.json desde optcgapi.com.

La app YA NO depende de este archivo en el uso normal: en cada arranque
(cuando la tabla de cartas esta vacia) pide el set OP-01 en vivo a la API
(ver app/optcg_client.py). Este JSON solo se usa como respaldo si esa
llamada en vivo falla (API caida, sin red, etc).

Uso (para actualizar el respaldo manualmente):
    python scripts/fetch_optcg_cards.py
"""
import json
import urllib.request

from app.optcg_client import FALLBACK_JSON, SET_ID, normalize_set


def main() -> None:
    url = f"https://optcgapi.com/api/sets/{SET_ID}/"
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = json.load(resp)
    cards = normalize_set(raw)
    FALLBACK_JSON.parent.mkdir(exist_ok=True)
    FALLBACK_JSON.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardadas {len(cards)} cartas en {FALLBACK_JSON}")


if __name__ == "__main__":
    main()
