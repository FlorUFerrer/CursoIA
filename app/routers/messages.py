from collections import defaultdict

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from sqlalchemy.orm import joinedload

from ..auth import ALGORITHM, SECRET_KEY, get_current_user
from ..database import SessionLocal, get_db
from ..models import Listing, Message, User
from ..schemas import ChatSummaryOut, MessageOut

router = APIRouter(tags=["messages"])


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, listing_id: int, ws: WebSocket):
        await ws.accept()
        self.rooms[listing_id].append(ws)

    def disconnect(self, listing_id: int, ws: WebSocket):
        try:
            self.rooms[listing_id].remove(ws)
        except ValueError:
            pass

    async def broadcast(self, listing_id: int, data: dict):
        dead = []
        for ws in list(self.rooms[listing_id]):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(listing_id, ws)


manager = ConnectionManager()


@router.get("/api/messages/mine", response_model=list[ChatSummaryOut])
def get_my_chats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sent_ids = {
        row[0]
        for row in db.query(Message.listing_id).filter(Message.sender_id == user.id).distinct().all()
    }
    seller_ids = {
        row[0]
        for row in db.query(Message.listing_id)
        .join(Listing, Message.listing_id == Listing.id)
        .filter(Listing.seller_id == user.id)
        .distinct()
        .all()
    }
    listing_ids = sent_ids | seller_ids
    if not listing_ids:
        return []

    summaries = []
    for lid in listing_ids:
        last_msg = (
            db.query(Message)
            .filter(Message.listing_id == lid)
            .order_by(Message.created_at.desc())
            .first()
        )
        if not last_msg:
            continue
        listing = (
            db.query(Listing)
            .options(joinedload(Listing.card), joinedload(Listing.seller))
            .filter(Listing.id == lid)
            .first()
        )
        if not listing:
            continue
        summaries.append(
            ChatSummaryOut(
                listing_id=lid,
                card_name=listing.card.name,
                seller_id=listing.seller_id,
                seller_username=listing.seller.username,
                listing_type=listing.listing_type,
                last_content=last_msg.content,
                last_at=last_msg.created_at,
                last_sender=last_msg.sender.username,
            )
        )
    summaries.sort(key=lambda x: x.last_at, reverse=True)
    return summaries


@router.get("/api/messages/{listing_id}", response_model=list[MessageOut])
def get_messages(
    listing_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msgs = (
        db.query(Message)
        .filter(Message.listing_id == listing_id)
        .order_by(Message.created_at)
        .all()
    )
    return [
        MessageOut(
            id=m.id,
            listing_id=m.listing_id,
            sender_id=m.sender_id,
            sender_username=m.sender.username,
            content=m.content,
            created_at=m.created_at,
        )
        for m in msgs
    ]


@router.websocket("/ws/chat/{listing_id}")
async def ws_chat(listing_id: int, websocket: WebSocket, token: str = Query(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
        sender_username = payload.get("username", "?")
    except (JWTError, ValueError):
        await websocket.close(code=1008)
        return

    await manager.connect(listing_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            content = (data.get("content") or "").strip()
            if not content:
                continue
            db = SessionLocal()
            try:
                msg = Message(listing_id=listing_id, sender_id=user_id, content=content)
                db.add(msg)
                db.commit()
                db.refresh(msg)
                out = {
                    "id": msg.id,
                    "listing_id": listing_id,
                    "sender_id": user_id,
                    "sender_username": sender_username,
                    "content": content,
                    "created_at": msg.created_at.isoformat(),
                }
            finally:
                db.close()
            await manager.broadcast(listing_id, out)
    except WebSocketDisconnect:
        manager.disconnect(listing_id, websocket)
    except Exception:
        manager.disconnect(listing_id, websocket)
