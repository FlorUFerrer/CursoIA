"""
Configuración global de pytest para TCG Trade.

Se establece DATABASE_URL ANTES de importar cualquier módulo de la app,
porque database.py lee esa variable en tiempo de carga del módulo.
El seed se parchea para evitar llamadas a la API externa durante los tests.
"""
import os

# ── Apuntar a una base de datos de test (aislada) ────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_tcg.db")
os.environ.setdefault("DATA_DIR", "./data")

# ── Ahora sí importamos la app ────────────────────────────────────────────────
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password
from app.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.models import Card, CollectionItem, Listing, PriceHistory, Tournament, User

# Crear tablas una sola vez para toda la sesión de tests
Base.metadata.create_all(bind=engine)


# ── Limpieza entre tests ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def truncate_tables():
    """Borra todos los registros antes de cada test para garantizar aislamiento."""
    # Limpia ANTES del test (estado limpio garantizado)
    _wipe()
    yield
    # Limpia DESPUÉS también por si quedó basura
    _wipe()


def _wipe():
    session = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()


# ── Session de base de datos para tests ──────────────────────────────────────

@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Cliente HTTP con DB sobrescrita y seed parcheado ─────────────────────────

@pytest.fixture
def client(db: Session) -> TestClient:
    """
    TestClient de FastAPI con:
    - get_db apuntando a la DB de test
    - seed_database parcheado (no llama a la API externa)
    """
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.main.seed_database", return_value=None):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
    app.dependency_overrides.clear()


# ── Fixtures de datos ─────────────────────────────────────────────────────────

@pytest.fixture
def card(db: Session) -> Card:
    """Carta de prueba con historial de precios."""
    c = Card(
        name="Monkey D. Luffy",
        game="One Piece",
        set_name="OP-01",
        code="OP01-001",
        rarity="Leader",
        price=15000,
        trend=5.2,
        trend_dir="up",
    )
    db.add(c)
    db.flush()
    db.add(PriceHistory(card_id=c.id, label="hoy", value=85, is_today=True))
    db.add(PriceHistory(card_id=c.id, label="may 1", value=70, is_today=False))
    db.add(PriceHistory(card_id=c.id, label="may 15", value=75, is_today=False))
    db.add(PriceHistory(card_id=c.id, label="jun 1", value=80, is_today=False))
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture
def second_card(db: Session) -> Card:
    """Segunda carta para tests que necesitan dos cartas distintas."""
    c = Card(
        name="Roronoa Zoro",
        game="One Piece",
        set_name="OP-01",
        code="OP01-002",
        rarity="Super Rare",
        price=8000,
        trend=-2.1,
        trend_dir="down",
    )
    db.add(c)
    db.flush()
    db.add(PriceHistory(card_id=c.id, label="hoy", value=60, is_today=True))
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture
def user(db: Session) -> User:
    """Usuario estándar (sin premium, sin tienda)."""
    u = User(username="testuser", password_hash=hash_password("testpass123"))
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def store_user(db: Session) -> User:
    """Usuario tienda (is_store=True)."""
    u = User(
        username="teststore",
        password_hash=hash_password("storepass123"),
        is_store=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def premium_user(db: Session) -> User:
    """Usuario premium (is_premium=True)."""
    u = User(
        username="premiumuser",
        password_hash=hash_password("premiumpass123"),
        is_premium=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def token(user: User) -> str:
    return create_access_token(user.id, user.username)


@pytest.fixture
def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def store_token(store_user: User) -> str:
    return create_access_token(store_user.id, store_user.username)


@pytest.fixture
def store_headers(store_token: str) -> dict:
    return {"Authorization": f"Bearer {store_token}"}


@pytest.fixture
def listing(db: Session, store_user: User, card: Card) -> Listing:
    """Publicación activa de la tienda."""
    l = Listing(
        seller_id=store_user.id,
        card_id=card.id,
        listing_type="sale",
        price=card.price,
        featured=False,
        status="active",
    )
    db.add(l)
    db.commit()
    db.refresh(l)
    return l
