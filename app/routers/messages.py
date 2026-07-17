from collections import defaultdict

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

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


class NotifyManager:
    """One persistent WS per logged-in user for cross-chat notifications."""

    def __init__(self):
        self.connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.connections[user_id].append(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        try:
            self.connections[user_id].remove(ws)
        except ValueError:
            pass

    async def notify(self, user_id: int, data: dict):
        dead = []
        for ws in list(self.connections[user_id]):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)


manager = ConnectionManager()
notify_manager = NotifyManager()


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


@router.websocket("/ws/notify")
async def ws_notify(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        await websocket.close(code=1008)
        return

    await notify_manager.connect(user_id, websocket)
    try:
        while True:
            # Keep-alive: ignore anything the client sends
            await websocket.receive_text()
    except WebSocketDisconnect:
        notify_manager.disconnect(user_id, websocket)
    except Exception:
        notify_manager.disconnect(user_id, websocket)


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

                # Collect participants to notify (everyone in this chat except sender)
                other_ids = {
                    row[0]
                    for row in db.query(Message.sender_id)
                    .filter(Message.listing_id == listing_id, Message.sender_id != user_id)
                    .distinct()
                    .all()
                }
                listing = db.query(Listing).filter(Listing.id == listing_id).first()
                if listing and listing.seller_id != user_id:
                    other_ids.add(listing.seller_id)

                card_name = listing.card.name if listing else ""
                seller_id = listing.seller_id if listing else 0
                seller_username = listing.seller.username if listing else ""
                listing_type = listing.listing_type if listing else "sale"
            finally:
                db.close()

            await manager.broadcast(listing_id, out)

            # Push notification to participants not currently viewing this chat
            notify_payload = {
                "type": "new_message",
                "listing_id": listing_id,
                "card_name": card_name,
                "seller_id": seller_id,
                "seller_username": seller_username,
                "listing_type": listing_type,
                "sender_username": sender_username,
                "preview": content[:60],
            }
            for uid in other_ids:
                await notify_manager.notify(uid, notify_payload)

    except WebSocketDisconnect:
        manager.disconnect(listing_id, websocket)
    except Exception:
        manager.disconnect(listing_id, websocket)
