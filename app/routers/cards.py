import hashlib
import os
import random
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from ..auth import get_optional_user
from ..database import get_db
from ..models import Card, Scan, User
from ..schemas import CardOut, PriceHistoryOut, ScanOut

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
        history=history,
    )


async def identify_card_with_ai(image_bytes: bytes, cards: list[Card]) -> Optional[Card]:
    """Optional OpenAI vision identification. Returns None to fall back to simulated scan."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        import base64
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        catalog = "\n".join(f"- {c.code}: {c.name} ({c.game})" for c in cards)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"),
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
            max_tokens=50,
        )
        text = (response.choices[0].message.content or "").strip().upper()
        for card in cards:
            if card.code.upper() in text or card.name.upper() in text:
                return card
    except Exception:
        return None
    return None


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


@router.get("/cards", response_model=list[CardOut])
def list_cards(db: Session = Depends(get_db)):
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
    if image_bytes and os.getenv("OPENAI_API_KEY"):
        card = await identify_card_with_ai(image_bytes, cards)
        if card:
            method = "openai"

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
