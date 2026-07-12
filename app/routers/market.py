from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user
from ..database import get_db
from ..models import Card, Listing, Offer, Reservation, User
from ..routers.cards import card_to_out
from ..schemas import ListingCreate, ListingOut, OfferCreate, OfferOut, ReservationOut

router = APIRouter(prefix="/api/market", tags=["market"])


def listing_to_out(listing: Listing) -> ListingOut:
    return ListingOut(
        id=listing.id,
        card=card_to_out(listing.card),
        seller_id=listing.seller_id,
        seller_username=listing.seller.username if listing.seller else "?",
        listing_type=listing.listing_type,
        price=listing.price,
        wants=listing.wants,
        featured=listing.featured,
        status=listing.status,
        created_at=listing.created_at,
    )


@router.get("/listings", response_model=list[ListingOut])
def list_listings(db: Session = Depends(get_db)):
    listings = (
        db.query(Listing)
        .options(
            joinedload(Listing.card).joinedload(Card.history),
            joinedload(Listing.seller),
        )
        .filter(Listing.status == "active")
        .order_by(Listing.featured.desc(), Listing.created_at.desc())
        .all()
    )
    return [listing_to_out(l) for l in listings]


@router.post("/listings", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = db.query(Card).options(joinedload(Card.history)).filter(Card.id == payload.card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Carta no encontrada")
    allowed = {"sale", "trade", "negotiable", "combo"}
    if payload.listing_type not in allowed:
        raise HTTPException(status_code=400, detail=f"listing_type debe ser uno de: {', '.join(allowed)}")
    listing = Listing(
        seller_id=user.id,
        card_id=payload.card_id,
        listing_type=payload.listing_type,
        price=payload.price if payload.price is not None else card.price,
        wants=payload.wants,
        featured=payload.featured,
        status="active",
    )
    if payload.listing_type == "trade":
        listing.price = None
    db.add(listing)
    db.commit()
    listing = (
        db.query(Listing)
        .options(
            joinedload(Listing.card).joinedload(Card.history),
            joinedload(Listing.seller),
        )
        .filter(Listing.id == listing.id)
        .first()
    )
    return listing_to_out(listing)


@router.post("/listings/{listing_id}/reserve", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
def reserve_listing(
    listing_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id, Listing.status == "active").first()
    if not listing:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    if listing.seller_id == user.id:
        raise HTTPException(status_code=400, detail="No podés reservar tu propia publicación")
    existing = (
        db.query(Reservation)
        .filter(
            Reservation.listing_id == listing_id,
            Reservation.buyer_id == user.id,
            Reservation.status == "active",
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Ya tenés una reserva activa")
    reservation = Reservation(listing_id=listing_id, buyer_id=user.id, status="active")
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return ReservationOut(
        id=reservation.id,
        listing_id=reservation.listing_id,
        buyer_id=user.id,
        buyer_username=user.username,
        status=reservation.status,
        created_at=reservation.created_at,
    )


@router.post("/listings/{listing_id}/offers", response_model=OfferOut, status_code=status.HTTP_201_CREATED)
def create_offer(
    listing_id: int,
    payload: OfferCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id, Listing.status == "active").first()
    if not listing:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    if listing.seller_id == user.id:
        raise HTTPException(status_code=400, detail="No podés ofertar en tu propia publicación")
    if payload.money_offer is None and not payload.cards_offer:
        raise HTTPException(status_code=400, detail="Indicá dinero y/o cartas en la oferta")
    offer = Offer(
        listing_id=listing_id,
        buyer_id=user.id,
        money_offer=payload.money_offer,
        cards_offer=payload.cards_offer,
        status="pending",
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return OfferOut(
        id=offer.id,
        listing_id=offer.listing_id,
        buyer_id=user.id,
        buyer_username=user.username,
        money_offer=offer.money_offer,
        cards_offer=offer.cards_offer,
        status=offer.status,
        created_at=offer.created_at,
    )


@router.get("/listings/{listing_id}/offers", response_model=list[OfferOut])
def list_offers(
    listing_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Solo el vendedor puede ver las ofertas")
    offers = (
        db.query(Offer)
        .options(joinedload(Offer.buyer))
        .filter(Offer.listing_id == listing_id)
        .order_by(Offer.created_at.desc())
        .all()
    )
    return [
        OfferOut(
            id=o.id,
            listing_id=o.listing_id,
            buyer_id=o.buyer_id,
            buyer_username=o.buyer.username if o.buyer else "?",
            money_offer=o.money_offer,
            cards_offer=o.cards_offer,
            status=o.status,
            created_at=o.created_at,
        )
        for o in offers
    ]
