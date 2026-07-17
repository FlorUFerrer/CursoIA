from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Tournament, User
from ..schemas import TournamentCancel, TournamentCreate, TournamentOut, TournamentUpdate

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])


def _to_out(t: Tournament) -> TournamentOut:
    return TournamentOut(
        id=t.id,
        organizer_id=t.organizer_id,
        organizer_username=t.organizer.username,
        title=t.title,
        description=t.description,
        event_date=t.event_date,
        location=t.location,
        status=t.status,
        cancellation_reason=t.cancellation_reason,
        created_at=t.created_at,
    )


@router.get("", response_model=list[TournamentOut])
def list_tournaments(db: Session = Depends(get_db)):
    tournaments = (
        db.query(Tournament)
        .filter(Tournament.status == "active")
        .order_by(Tournament.created_at.desc())
        .all()
    )
    return [_to_out(t) for t in tournaments]


@router.get("/mine", response_model=list[TournamentOut])
def list_my_tournaments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tournaments = (
        db.query(Tournament)
        .filter(Tournament.organizer_id == user.id)
        .order_by(Tournament.created_at.desc())
        .all()
    )
    return [_to_out(t) for t in tournaments]


@router.patch("/{tournament_id}", response_model=TournamentOut)
def update_tournament(
    tournament_id: int,
    payload: TournamentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    if t.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Solo el organizador puede editar este torneo")
    if payload.title is not None:
        t.title = payload.title
    if payload.description is not None:
        t.description = payload.description
    if payload.event_date is not None:
        t.event_date = payload.event_date
    if payload.location is not None:
        t.location = payload.location
    db.commit()
    db.refresh(t)
    return _to_out(t)


@router.post("/{tournament_id}/cancel", response_model=TournamentOut)
def cancel_tournament(
    tournament_id: int,
    payload: TournamentCancel,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    if t.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Solo el organizador puede cancelar este torneo")
    if t.status == "cancelled":
        raise HTTPException(status_code=400, detail="El torneo ya está cancelado")
    t.status = "cancelled"
    t.cancellation_reason = payload.reason
    db.commit()
    db.refresh(t)
    return _to_out(t)


@router.post("", response_model=TournamentOut, status_code=status.HTTP_201_CREATED)
def create_tournament(
    payload: TournamentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.is_store:
        raise HTTPException(status_code=403, detail="Solo las tiendas pueden publicar torneos")
    t = Tournament(
        organizer_id=user.id,
        title=payload.title,
        description=payload.description,
        event_date=payload.event_date,
        location=payload.location,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _to_out(t)
