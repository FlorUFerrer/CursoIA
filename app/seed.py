import random

from sqlalchemy.orm import Session, joinedload

from .auth import hash_password
from .models import Card, Listing, PriceHistory, User
from .optcg_client import DEFAULT_SET_ID, fetch_all_sets, fetch_set_cards
from .pricing import USD_ARS_RATE

HISTORY_LABELS = ("may 1", "may 15", "jun 1", "hoy")


def _build_history(code: str) -> tuple[list[tuple[str, int, bool]], float, str]:
    """Genera una serie de 4 puntos (valores relativos 0-100 para el grafico
    de barras) y una tendencia, a partir de una semilla determinada por el
    codigo de carta (la API no trae historico de precios)."""
    rng = random.Random(code)
    direction = rng.choices(["up", "down", "stable"], weights=[55, 30, 15])[0]
    if direction == "up":
        values = sorted(rng.sample(range(55, 90), 3)) + [100]
    elif direction == "down":
        values = [100] + sorted(rng.sample(range(55, 90), 3), reverse=True)
    else:
        base = rng.randint(78, 88)
        values = [base + rng.randint(-3, 3) for _ in range(4)]
        values[-1] = base

    history = [(label, value, label == "hoy") for label, value in zip(HISTORY_LABELS, values)]

    if direction == "up":
        trend = round(rng.uniform(2, 20), 1)
    elif direction == "down":
        trend = round(rng.uniform(-20, -2), 1)
    else:
        trend = round(rng.uniform(-1, 1), 1)
    return history, trend, direction


def _build_card_rows(raw_entries: list[dict]) -> list[dict]:
    rows = []
    for entry in raw_entries:
        history, trend, trend_dir = _build_history(entry["code"])
        rows.append(
            {
                "name": entry["name"],
                "game": "One Piece",
                "set_name": entry["set_name"],
                "code": entry["code"],
                "rarity": entry["rarity"],
                "price": round(entry["market_price_usd"] * USD_ARS_RATE),
                "trend": trend,
                "trend_dir": trend_dir,
                "image_url": entry["image_url"],
                "history": history,
            }
        )
    return rows


def ensure_set_cards(db: Session, set_id: str) -> list[Card]:
    """Devuelve las cartas de un set. La primera vez que se pide un set, lo
    trae de la API y lo guarda en la base; las siguientes veces se sirve
    directo desde ahi (no se vuelve a pedir a optcgapi.com)."""
    existing = (
        db.query(Card).options(joinedload(Card.history)).filter(Card.set_name == set_id).all()
    )
    if existing:
        return existing

    cards = []
    for raw in _build_card_rows(fetch_set_cards(set_id)):
        data = {k: v for k, v in raw.items() if k != "history"}
        history = raw["history"]
        card = Card(**data)
        db.add(card)
        db.flush()
        for label, value, is_today in history:
            db.add(
                PriceHistory(
                    card_id=card.id,
                    label=label,
                    value=value,
                    is_today=is_today,
                )
            )
        cards.append(card)
    db.commit()
    return cards


def _pick_default_set_id() -> str:
    """El ultimo set lanzado segun /allSets/, o OP-01 si esa consulta falla."""
    try:
        sets = fetch_all_sets()
        if sets:
            return sets[-1]["set_id"]
    except Exception:
        pass
    return DEFAULT_SET_ID


def seed_database(db: Session) -> None:
    if db.query(Card).count() > 0:
        return

    demo = User(username="demo", password_hash=hash_password("demo123"))
    seller = User(username="ColeccionAR", password_hash=hash_password("demo123"))
    seller2 = User(username="TCG_BA", password_hash=hash_password("demo123"))
    db.add_all([demo, seller, seller2])
    db.flush()

    default_set_id = _pick_default_set_id()
    try:
        cards = ensure_set_cards(db, default_set_id)
    except Exception:
        # Ultimo respaldo: OP-01 siempre tiene snapshot local, no depende de red.
        cards = ensure_set_cards(db, DEFAULT_SET_ID)

    top = sorted(cards, key=lambda c: c.price, reverse=True)[:3]
    if len(top) >= 3:
        db.add(
            Listing(
                seller_id=seller.id,
                card_id=top[0].id,
                listing_type="sale",
                price=top[0].price,
                featured=True,
                status="active",
            )
        )
        db.add(
            Listing(
                seller_id=seller2.id,
                card_id=top[1].id,
                listing_type="trade",
                price=None,
                wants="Busco otras cartas top del set",
                featured=False,
                status="active",
            )
        )
        db.add(
            Listing(
                seller_id=seller.id,
                card_id=top[2].id,
                listing_type="combo",
                price=top[2].price,
                wants="Carta + dinero",
                featured=True,
                status="active",
            )
        )
        db.commit()
