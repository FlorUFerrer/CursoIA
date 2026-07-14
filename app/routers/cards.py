import hashlib
import os
import random
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from ..auth import get_optional_user
from ..database import get_db
from ..models import Card, Scan, User
from ..optcg_client import DEFAULT_SET_ID, fetch_all_sets
from ..schemas import CardOut, PriceHistoryOut, ScanOut
from ..seed import ensure_set_cards

router = APIRouter(prefix="/api", tags=["cards"])


def card_to_out(card: Card) -> CardOut:
    history = [
        PriceHistoryOut(label=h.label, value=h.value, is_today=h.is_today)
        for h in sorted(card.history, key=lambda x: x.id)
    ]
    return CardOut(
        id=card.id,
        name=card.name,
        game=card.game,
        set_name=card.set_name,
        code=card.code,
        rarity=card.rarity,
        price=card.price,
        trend=card.trend,
        trend_dir=card.trend_dir,
        image_url=card.image_url,
        history=history,
    )


# Proveedores de vision AI probados en orden. Gemini primero: tiene tier
# gratuito estable (sin tarjeta) via su endpoint compatible con OpenAI.
AI_VISION_PROVIDERS = [
    {
        "env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model_env": "GEMINI_VISION_MODEL",
        "default_model": "gemini-flash-latest",
        "method": "gemini",
    },
    {
        "env": "OPENAI_API_KEY",
        "base_url": None,
        "model_env": "OPENAI_VISION_MODEL",
        "default_model": "gpt-4o-mini",
        "method": "openai",
    },
]


async def identify_card_with_ai(image_bytes: bytes, cards: list[Card]) -> tuple[Optional[Card], Optional[str]]:
    """Identificacion por vision AI. Prueba los proveedores configurados en
    orden (ver AI_VISION_PROVIDERS) y devuelve (carta, metodo), o (None, None)
    para caer a la simulacion si ninguno esta configurado o falla."""
    catalog = "\n".join(f"- {c.code}: {c.name} ({c.game})" for c in cards)
    for provider in AI_VISION_PROVIDERS:
        api_key = os.getenv(provider["env"])
        if not api_key:
            continue
        try:
            import base64
            from openai import OpenAI

            client_kwargs = {"api_key": api_key}
            if provider["base_url"]:
                client_kwargs["base_url"] = provider["base_url"]
            client = OpenAI(**client_kwargs)
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            response = client.chat.completions.create(
                model=os.getenv(provider["model_env"], provider["default_model"]),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Identify the TCG card in this image. Reply with ONLY the card code "
                                    f"from this catalog, or UNKNOWN if unsure:\n{catalog}"
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                            },
                        ],
                    }
                ],
                # Gemini gasta tokens de "razonamiento" antes de emitir texto
                # visible; con un limite bajo la respuesta queda vacia.
                max_tokens=300,
            )
            text = (response.choices[0].message.content or "").strip().upper()
            for card in cards:
                if card.code.upper() in text or card.name.upper() in text:
                    return card, provider["method"]
        except Exception:
            continue
    return None, None


def identify_card_simulated(image_bytes: bytes, cards: list[Card]) -> Card:
    """Deterministic-ish pick based on image hash so same photo tends to map similarly."""
    if not cards:
        raise HTTPException(status_code=404, detail="No hay cartas en la base")
    digest = hashlib.md5(image_bytes).hexdigest()
    idx = int(digest[:8], 16) % len(cards)
    # Small chance of random card for variety when scanning without photo content change
    if random.random() < 0.15:
        return random.choice(cards)
    return cards[idx]


@router.get("/catalog/sets")
def catalog_sets():
    """Lista de sets de One Piece TCG disponibles, para el selector del catalogo."""
    try:
        sets = fetch_all_sets()
    except Exception:
        sets = []
    default_set_id = sets[-1]["set_id"] if sets else DEFAULT_SET_ID
    return {"sets": sets, "default_set_id": default_set_id}


@router.get("/cards", response_model=list[CardOut])
def list_cards(set_id: Optional[str] = None, db: Session = Depends(get_db)):
    if set_id:
        try:
            cards = ensure_set_cards(db, set_id)
        except Exception:
            raise HTTPException(status_code=502, detail="No se pudo obtener el set desde la API externa")
        if not cards:
            raise HTTPException(status_code=404, detail="Set sin cartas o inexistente")
        cards = sorted(cards, key=lambda c: c.name)
    else:
        cards = db.query(Card).options(joinedload(Card.history)).order_by(Card.name).all()
    return [card_to_out(c) for c in cards]


@router.get("/cards/{card_id}", response_model=CardOut)
def get_card(card_id: int, db: Session = Depends(get_db)):
    card = db.query(Card).options(joinedload(Card.history)).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Carta no encontrada")
    return card_to_out(card)


@router.get("/scans/recent", response_model=list[CardOut])
def recent_scans(limit: int = 10, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    query = db.query(Scan).options(joinedload(Scan.card).joinedload(Card.history))
    if user:
        query = query.filter(Scan.user_id == user.id)
    scans = query.order_by(Scan.created_at.desc()).limit(limit).all()
    seen = set()
    result = []
    for scan in scans:
        if scan.card_id in seen or not scan.card:
            continue
        seen.add(scan.card_id)
        result.append(card_to_out(scan.card))
    if not result:
        # Public recent: last scans overall if anonymous
        scans = (
            db.query(Scan)
            .options(joinedload(Scan.card).joinedload(Card.history))
            .order_by(Scan.created_at.desc())
            .limit(limit)
            .all()
        )
        for scan in scans:
            if scan.card_id in seen or not scan.card:
                continue
            seen.add(scan.card_id)
            result.append(card_to_out(scan.card))
    if not result:
        cards = db.query(Card).options(joinedload(Card.history)).limit(2).all()
        result = [card_to_out(c) for c in cards]
    return result


@router.post("/scan", response_model=ScanOut)
async def scan_card(
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    cards = db.query(Card).options(joinedload(Card.history)).all()
    if not cards:
        raise HTTPException(status_code=404, detail="No hay cartas en la base")

    image_bytes = b""
    if file is not None:
        image_bytes = await file.read()

    method = "simulated"
    card = None
    if image_bytes:
        card, ai_method = await identify_card_with_ai(image_bytes, cards)
        if card:
            method = ai_method

    if card is None:
        if not image_bytes:
            image_bytes = os.urandom(16)
        card = identify_card_simulated(image_bytes, cards)
        method = "simulated"

    # Reload with history
    card = db.query(Card).options(joinedload(Card.history)).filter(Card.id == card.id).first()
    scan = Scan(card_id=card.id, user_id=user.id if user else None)
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return ScanOut(card=card_to_out(card), scan_id=scan.id, method=method)
