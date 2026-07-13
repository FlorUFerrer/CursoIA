from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Tournament, User
from ..schemas import TournamentCreate, TournamentOut

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
