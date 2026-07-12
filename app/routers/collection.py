from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user
from ..database import get_db
from ..models import Card, CollectionItem, User
from ..routers.cards import card_to_out
from ..schemas import CollectionItemOut, CollectionSummaryOut

router = APIRouter(prefix="/api/collection", tags=["collection"])


@router.get("", response_model=CollectionSummaryOut)
def get_collection(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = (
        db.query(CollectionItem)
        .options(joinedload(CollectionItem.card).joinedload(Card.history))
        .filter(CollectionItem.user_id == user.id)
        .order_by(CollectionItem.created_at.desc())
        .all()
    )
    out_items = [
        CollectionItemOut(id=i.id, card=card_to_out(i.card), created_at=i.created_at)
        for i in items
        if i.card
    ]
    total = sum(i.card.price for i in out_items)
    return CollectionSummaryOut(items=out_items, total_value=total, count=len(out_items))


@router.post("/{card_id}", response_model=CollectionItemOut, status_code=status.HTTP_201_CREATED)
def add_to_collection(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    card = db.query(Card).options(joinedload(Card.history)).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Carta no encontrada")
    existing = (
        db.query(CollectionItem)
        .filter(CollectionItem.user_id == user.id, CollectionItem.card_id == card_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Esta carta ya está en tu colección")
    item = CollectionItem(user_id=user.id, card_id=card_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return CollectionItemOut(id=item.id, card=card_to_out(card), created_at=item.created_at)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_collection(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = (
        db.query(CollectionItem)
        .filter(CollectionItem.user_id == user.id, CollectionItem.card_id == card_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="No está en tu colección")
    db.delete(item)
    db.commit()
    return None
