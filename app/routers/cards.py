import hashlib
import logging
import os
import random
import re
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from ..auth import get_optional_user
from ..database import get_db
from ..models import Card, Scan, User
from ..optcg_client import DEFAULT_SET_ID, list_all_sets
from ..schemas import CardOut, PriceHistoryOut, ScanOut
from ..seed import ensure_set_cards

router = APIRouter(prefix="/api", tags=["cards"])
logger = logging.getLogger("tcg_trade.scan")


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


# Codigo de carta tipo "OP05-003", "EB01-012", "ST15-005".
CODE_PATTERN = re.compile(r"\b([A-Z]{2,5}\d{0,3})-(\d{2,4})\b")


def _guess_set_id(prefix: str) -> str:
    """'OP05' -> 'OP-05' (asi se llaman los sets en optcgapi.com)."""
    m = re.match(r"^([A-Z]+)(\d+)$", prefix)
    return f"{m.group(1)}-{m.group(2)}" if m else prefix


async def identify_card_with_ai(
    image_bytes: bytes, cards: list[Card], db: Session
) -> tuple[Optional[Card], Optional[str]]:
    """Identificacion por vision AI. Prueba los proveedores configurados en
    orden (ver AI_VISION_PROVIDERS) y devuelve (carta, metodo), o (None, None)
    para caer a la simulacion si ninguno esta configurado o falla.

    No le mandamos el catalogo completo al modelo (con cientos de cartas
    cacheadas localmente el prompt explota y el modelo gasta el limite de
    tokens "pensando" antes de contestar). Le pedimos que identifique la
    carta con su propio conocimiento; si menciona un set que todavia no
    tenemos cacheado (ej. el usuario escaneo una carta de un set que nadie
    eligio nunca en el Catalogo), lo traemos on-demand para poder matchear
    por codigo exacto en vez de "misma carta, otro set" por nombre nomas."""
    for provider in AI_VISION_PROVIDERS:
        api_key = os.getenv(provider["env"])
        if not api_key:
            logger.info("Proveedor %s sin API key configurada, se salta.", provider["method"])
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
                                    "Identify the One Piece TCG card in this image. Reply with ONLY the "
                                    "character name and the card's set code/number if visible "
                                    "(e.g. 'Monkey D. Luffy OP01-003'), or UNKNOWN if you can't tell. "
                                    "No explanation, no reasoning, just the answer."
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
                # visible; con un limite bajo la respuesta queda vacia/cortada.
                max_tokens=1500,
            )
            text = (response.choices[0].message.content or "").strip().upper()
            logger.info("Respuesta de %s: %r", provider["method"], text)

            candidates = cards
            code_match = CODE_PATTERN.search(text)
            if code_match:
                guessed_set_id = _guess_set_id(code_match.group(1))
                try:
                    fetched = ensure_set_cards(db, guessed_set_id)
                    existing_ids = {c.id for c in candidates}
                    candidates = candidates + [c for c in fetched if c.id not in existing_ids]
                except Exception:
                    logger.info("No se pudo traer el set %s sugerido por la IA", guessed_set_id)

            # 1ra pasada: codigo exacto (evita devolver la misma carta pero
            # de otro set/temporada cuando el nombre coincide en varios).
            for card in candidates:
                if card.code.upper() in text:
                    return card, provider["method"]
            # 2da pasada: nombre, solo si no hubo match de codigo.
            for card in candidates:
                if card.name.upper() in text:
                    return card, provider["method"]
            logger.info("%s no matcheo ninguna carta del catalogo (%d cartas)", provider["method"], len(candidates))
        except Exception:
            logger.exception("Fallo el proveedor %s", provider["method"])
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
        sets = list_all_sets()
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
        card, ai_method = await identify_card_with_ai(image_bytes, cards, db)
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
