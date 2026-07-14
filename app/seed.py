import random

from sqlalchemy.orm import Session, joinedload

from .auth import hash_password
from .models import Card, Listing, PriceHistory, Tournament, User
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
        # Algunos sets incluyen como "bonus" reprints especiales cuyo codigo
        # pertenece a otro set ya cacheado (ver cartas "(SP)" de optcgapi.com).
        # Si el codigo ya existe, reusamos esa fila en vez de insertar de
        # nuevo (el codigo es UNIQUE, insertarlo de nuevo rompe la sesion).
        existing_card = db.query(Card).filter(Card.code == raw["code"]).first()
        if existing_card:
            cards.append(existing_card)
            continue
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


_DEMO_USERS = [
    # (username, password, is_premium, is_store)
    ("demo", "demo123", False, False),
    ("ColeccionAR", "demo123", False, False),
    ("TCG_BA", "demo123", False, False),
    ("usuario", "usuario123", True, False),
    ("otrousuario", "otrousuario123", False, False),
    ("tienda", "tienda123", False, True),
]


def _ensure_demo_users(db: Session) -> dict[str, User]:
    """Crea o actualiza los usuarios demo. Se ejecuta siempre (idempotente)."""
    users: dict[str, User] = {}
    for username, password, is_premium, is_store in _DEMO_USERS:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            u = User(
                username=username,
                password_hash=hash_password(password),
                is_premium=is_premium,
                is_store=is_store,
            )
            db.add(u)
        else:
            u.is_premium = is_premium
            u.is_store = is_store
        users[username] = u
    db.flush()
    return users


def seed_database(db: Session) -> None:
    users = _ensure_demo_users(db)

    if db.query(Card).count() > 0:
        db.commit()
        return

    default_set_id = _pick_default_set_id()
    try:
        cards = ensure_set_cards(db, default_set_id)
    except Exception:
        # Ultimo respaldo: OP-01 siempre tiene snapshot local, no depende de red.
        cards = ensure_set_cards(db, DEFAULT_SET_ID)

    top = sorted(cards, key=lambda c: c.price, reverse=True)[:4]
    if len(top) >= 3:
        db.add(
            Listing(
                seller_id=users["ColeccionAR"].id,
                card_id=top[0].id,
                listing_type="sale",
                price=top[0].price,
                featured=True,
                status="active",
            )
        )
        db.add(
            Listing(
                seller_id=users["TCG_BA"].id,
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
                seller_id=users["ColeccionAR"].id,
                card_id=top[2].id,
                listing_type="combo",
                price=top[2].price,
                wants="Carta + dinero",
                featured=True,
                status="active",
            )
        )
    # Publicacion de tienda — carta que usuario puede ver y ofertar
    if len(top) >= 4:
        db.add(
            Listing(
                seller_id=users["tienda"].id,
                card_id=top[3].id,
                listing_type="sale",
                price=top[3].price,
                featured=True,
                status="active",
            )
        )

    # Torneo pre-cargado publicado por tienda
    if not db.query(Tournament).filter(Tournament.organizer_id == users["tienda"].id).first():
        db.add(
            Tournament(
                organizer_id=users["tienda"].id,
                title="Gran Torneo One Piece TCG — Julio 2026",
                description="Torneo abierto a todos los niveles. Formato best-of-3. Premios para los 3 primeros puestos.",
                event_date="2026-07-26",
                location="Tienda TCG — Buenos Aires, Argentina",
                status="active",
            )
        )

    db.commit()
