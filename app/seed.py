import random

from sqlalchemy.orm import Session

from .auth import hash_password
from .models import Card, Listing, PriceHistory, User
from .optcg_client import fetch_op01_cards
from .pricing import USD_ARS_RATE

HISTORY_LABELS = ("may 1", "may 15", "jun 1", "hoy")

# Cartas usadas para las publicaciones demo del mercado (codigos del set OP-01).
DEMO_LISTING_CODES = {
    "sale": "OP01-003",  # Monkey.D.Luffy (Leader)
    "trade": "OP01-120",  # Shanks
    "combo": "OP01-024",  # Monkey.D.Luffy (024)
}


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


def load_seed_cards() -> list[dict]:
    raw = fetch_op01_cards()
    cards = []
    for entry in raw:
        history, trend, trend_dir = _build_history(entry["code"])
        cards.append(
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
    return cards


def seed_database(db: Session) -> None:
    if db.query(Card).count() > 0:
        return

    demo = User(username="demo", password_hash=hash_password("demo123"))
    seller = User(username="ColeccionAR", password_hash=hash_password("demo123"))
    seller2 = User(username="TCG_BA", password_hash=hash_password("demo123"))
    db.add_all([demo, seller, seller2])
    db.flush()

    cards_by_code = {}
    for raw in load_seed_cards():
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
        cards_by_code[card.code] = card

    db.add(
        Listing(
            seller_id=seller.id,
            card_id=cards_by_code[DEMO_LISTING_CODES["sale"]].id,
            listing_type="sale",
            price=cards_by_code[DEMO_LISTING_CODES["sale"]].price,
            featured=True,
            status="active",
        )
    )
    db.add(
        Listing(
            seller_id=seller2.id,
            card_id=cards_by_code[DEMO_LISTING_CODES["trade"]].id,
            listing_type="trade",
            price=None,
            wants="Luffy Leader o Zoro",
            featured=False,
            status="active",
        )
    )
    db.add(
        Listing(
            seller_id=seller.id,
            card_id=cards_by_code[DEMO_LISTING_CODES["combo"]].id,
            listing_type="combo",
            price=cards_by_code[DEMO_LISTING_CODES["combo"]].price,
            wants="Shanks + dinero",
            featured=True,
            status="active",
        )
    )
    db.commit()
