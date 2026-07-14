"""Regenera el snapshot local con el catalogo completo de optcgapi.com:
data/optcg_all_sets.json (cartas de los 21 sets) y data/optcg_sets_meta.json
(lista de sets con su nombre bonito).

Es un script manual: la app NO llama a esto por si sola. El seed y el
Catalogo sirven todo desde estos archivos commiteados al repo; si aparece
un set nuevo que no esta aca, la app cae sola a traerlo en vivo como
respaldo (ver app/optcg_client.py). Correr este script de nuevo solo si
queres refrescar precios/actualizar a sets recien lanzados:

    python scripts/fetch_optcg_cards.py
"""
import json
import time
import urllib.request

from app.optcg_client import BUNDLED_SETS_JSON, BUNDLED_SETS_META_JSON, normalize_set

REQUEST_DELAY_SECONDS = 0.8


def fetch_set_raw(set_id: str) -> list[dict]:
    url = f"https://optcgapi.com/api/sets/{set_id}/"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def main() -> None:
    with urllib.request.urlopen("https://optcgapi.com/api/allSets/", timeout=30) as resp:
        sets = json.load(resp)
    print(f"{len(sets)} sets a traer")

    all_sets: dict[str, list[dict]] = {}
    for entry in sets:
        set_id = entry["set_id"]
        cards = normalize_set(fetch_set_raw(set_id))
        all_sets[set_id] = cards
        print(f"  {set_id}: {len(cards)} cartas")
        time.sleep(REQUEST_DELAY_SECONDS)

    BUNDLED_SETS_JSON.parent.mkdir(exist_ok=True)
    BUNDLED_SETS_JSON.write_text(json.dumps(all_sets, ensure_ascii=False), encoding="utf-8")
    BUNDLED_SETS_META_JSON.write_text(json.dumps(sets, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(len(v) for v in all_sets.values())
    print(f"Guardadas {total} cartas de {len(all_sets)} sets en {BUNDLED_SETS_JSON}")
    print(f"Guardados metadatos de {len(sets)} sets en {BUNDLED_SETS_META_JSON}")


if __name__ == "__main__":
    main()
