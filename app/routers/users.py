from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_current_user, get_user_by_username, hash_password, verify_password
from ..database import get_db
from ..models import CollectionItem, Scan, User
from ..schemas import ProfileStatsOut, TokenOut, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.username)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = get_user_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    token = create_access_token(user.id, user.username)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.get("/me/stats", response_model=ProfileStatsOut)
def my_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scans_count = db.query(Scan).filter(Scan.user_id == user.id).count()
    items = db.query(CollectionItem).filter(CollectionItem.user_id == user.id).all()
    total = sum(item.card.price for item in items if item.card)
    return ProfileStatsOut(
        username=user.username,
        scans_count=scans_count,
        collection_count=len(items),
        collection_value=total,
    )
