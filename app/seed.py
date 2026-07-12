from sqlalchemy.orm import Session

from .auth import hash_password
from .models import Card, Listing, PriceHistory, User


SEED_CARDS = [
    {
        "name": "Monkey D. Luffy",
        "game": "One Piece",
        "set_name": "OP-01",
        "code": "OP-01-001",
        "rarity": "Super Rare",
        "price": 4200,
        "trend": 12.0,
        "trend_dir": "up",
        "history": [
            ("may 1", 62, False),
            ("may 15", 78, False),
            ("jun 1", 85, False),
            ("hoy", 100, True),
        ],
    },
    {
        "name": "Zoro Promo",
        "game": "One Piece",
        "set_name": "OP-02",
        "code": "OP-02-P01",
        "rarity": "Promo",
        "price": 8500,
        "trend": -5.0,
        "trend_dir": "down",
        "history": [
            ("may 1", 100, False),
            ("may 15", 92, False),
            ("jun 1", 88, False),
            ("hoy", 82, True),
        ],
    },
    {
        "name": "Nami",
        "game": "One Piece",
        "set_name": "OP-01",
        "code": "OP-01-016",
        "rarity": "Rare",
        "price": 1800,
        "trend": 3.0,
        "trend_dir": "up",
        "history": [
            ("may 1", 70, False),
            ("may 15", 75, False),
            ("jun 1", 80, False),
            ("hoy", 85, True),
        ],
    },
    {
        "name": "Sanji",
        "game": "One Piece",
        "set_name": "OP-03",
        "code": "OP-03-025",
        "rarity": "Rare",
        "price": 2100,
        "trend": 0.0,
        "trend_dir": "stable",
        "history": [
            ("may 1", 80, False),
            ("may 15", 82, False),
            ("jun 1", 81, False),
            ("hoy", 80, True),
        ],
    },
    {
        "name": "Shanks",
        "game": "One Piece",
        "set_name": "OP-01",
        "code": "OP-01-120",
        "rarity": "Secret Rare",
        "price": 15000,
        "trend": 8.0,
        "trend_dir": "up",
        "history": [
            ("may 1", 55, False),
            ("may 15", 70, False),
            ("jun 1", 88, False),
            ("hoy", 100, True),
        ],
    },
    {
        "name": "Trafalgar Law",
        "game": "One Piece",
        "set_name": "OP-05",
        "code": "OP-05-098",
        "rarity": "Super Rare",
        "price": 5600,
        "trend": -2.0,
        "trend_dir": "down",
        "history": [
            ("may 1", 95, False),
            ("may 15", 90, False),
            ("jun 1", 88, False),
            ("hoy", 86, True),
        ],
    },
    {
        "name": "Ace",
        "game": "One Piece",
        "set_name": "OP-02",
        "code": "OP-02-013",
        "rarity": "Super Rare",
        "price": 7200,
        "trend": 6.0,
        "trend_dir": "up",
        "history": [
            ("may 1", 65, False),
            ("may 15", 72, False),
            ("jun 1", 85, False),
            ("hoy", 92, True),
        ],
    },
    {
        "name": "Kai",
        "game": "Riftbound",
        "set_name": "RB-01",
        "code": "RB-01-007",
        "rarity": "Legendary",
        "price": 9800,
        "trend": 15.0,
        "trend_dir": "up",
        "history": [
            ("may 1", 50, False),
            ("may 15", 68, False),
            ("jun 1", 82, False),
            ("hoy", 100, True),
        ],
    },
    {
        "name": "Nyra",
        "game": "Riftbound",
        "set_name": "RB-01",
        "code": "RB-01-022",
        "rarity": "Epic",
        "price": 3400,
        "trend": -3.0,
        "trend_dir": "down",
        "history": [
            ("may 1", 90, False),
            ("may 15", 88, False),
            ("jun 1", 85, False),
            ("hoy", 80, True),
        ],
    },
    {
        "name": "Vex",
        "game": "Riftbound",
        "set_name": "RB-02",
        "code": "RB-02-041",
        "rarity": "Rare",
        "price": 1200,
        "trend": 1.0,
        "trend_dir": "up",
        "history": [
            ("may 1", 75, False),
            ("may 15", 78, False),
            ("jun 1", 80, False),
            ("hoy", 82, True),
        ],
    },
]


def seed_database(db: Session) -> None:
    if db.query(Card).count() > 0:
        return

    demo = User(username="demo", password_hash=hash_password("demo123"))
    seller = User(username="ColeccionAR", password_hash=hash_password("demo123"))
    seller2 = User(username="TCG_BA", password_hash=hash_password("demo123"))
    db.add_all([demo, seller, seller2])
    db.flush()

    cards = []
    for raw in SEED_CARDS:
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

    db.add(
        Listing(
            seller_id=seller.id,
            card_id=cards[0].id,
            listing_type="sale",
            price=4000,
            featured=True,
            status="active",
        )
    )
    db.add(
        Listing(
            seller_id=seller2.id,
            card_id=cards[1].id,
            listing_type="trade",
            price=None,
            wants="Ace o Shanks",
            featured=False,
            status="active",
        )
    )
    db.add(
        Listing(
            seller_id=seller.id,
            card_id=cards[7].id,
            listing_type="combo",
            price=5000,
            wants="Nyra + dinero",
            featured=True,
            status="active",
        )
    )
    db.commit()
