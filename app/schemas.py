from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PriceHistoryOut(BaseModel):
    label: str
    value: int
    is_today: bool = False

    model_config = {"from_attributes": True}


class CardOut(BaseModel):
    id: int
    name: str
    game: str
    set_name: str
    code: str
    rarity: str
    price: int
    trend: float
    trend_dir: str
    history: list[PriceHistoryOut] = []

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=4, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProfileStatsOut(BaseModel):
    username: str
    scans_count: int
    collection_count: int
    collection_value: int


class CollectionItemOut(BaseModel):
    id: int
    card: CardOut
    created_at: datetime

    model_config = {"from_attributes": True}


class CollectionSummaryOut(BaseModel):
    items: list[CollectionItemOut]
    total_value: int
    count: int


class ListingCreate(BaseModel):
    card_id: int
    listing_type: str = "sale"
    price: Optional[int] = None
    wants: Optional[str] = None
    featured: bool = False


class ListingOut(BaseModel):
    id: int
    card: CardOut
    seller_id: int
    seller_username: str
    listing_type: str
    price: Optional[int] = None
    wants: Optional[str] = None
    featured: bool
    status: str
    created_at: datetime


class OfferCreate(BaseModel):
    money_offer: Optional[int] = None
    cards_offer: Optional[str] = None


class OfferOut(BaseModel):
    id: int
    listing_id: int
    buyer_id: int
    buyer_username: str
    money_offer: Optional[int] = None
    cards_offer: Optional[str] = None
    status: str
    created_at: datetime


class ReservationOut(BaseModel):
    id: int
    listing_id: int
    buyer_id: int
    buyer_username: str
    status: str
    created_at: datetime


class ScanOut(BaseModel):
    card: CardOut
    scan_id: int
    method: str
