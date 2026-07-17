from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_store: Mapped[bool] = mapped_column(Boolean, default=False)
    first_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dni: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    listings = relationship("Listing", back_populates="seller")
    collection_items = relationship("CollectionItem", back_populates="user")
    scans = relationship("Scan", back_populates="user")
    offers = relationship("Offer", back_populates="buyer", foreign_keys="Offer.buyer_id")
    reservations = relationship("Reservation", back_populates="buyer")
    tournaments = relationship("Tournament", back_populates="organizer")
    tournament_registrations = relationship("TournamentRegistration", back_populates="user")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    game: Mapped[str] = mapped_column(String(80), index=True)
    set_name: Mapped[str] = mapped_column(String(80))
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    rarity: Mapped[str] = mapped_column(String(40))
    price: Mapped[int] = mapped_column(Integer)
    trend: Mapped[float] = mapped_column(Float, default=0.0)
    trend_dir: Mapped[str] = mapped_column(String(10), default="stable")
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    history = relationship("PriceHistory", back_populates="card", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="card")
    collection_items = relationship("CollectionItem", back_populates="card")
    scans = relationship("Scan", back_populates="card")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    label: Mapped[str] = mapped_column(String(40))
    value: Mapped[int] = mapped_column(Integer)
    is_today: Mapped[bool] = mapped_column(Boolean, default=False)

    card = relationship("Card", back_populates="history")


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    card = relationship("Card", back_populates="scans")
    user = relationship("User", back_populates="scans")


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="collection_items")
    card = relationship("Card", back_populates="collection_items")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    # sale | trade | negotiable | combo
    listing_type: Mapped[str] = mapped_column(String(20), default="sale")
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wants: Mapped[str | None] = mapped_column(Text, nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    seller = relationship("User", back_populates="listings")
    card = relationship("Card", back_populates="listings")
    offers = relationship("Offer", back_populates="listing", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="listing", cascade="all, delete-orphan")


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    money_offer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cards_offer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pending | accepted | rejected
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing", back_populates="offers")
    buyer = relationship("User", back_populates="offers", foreign_keys=[buyer_id])


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # active | cancelled | completed
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing", back_populates="reservations")
    buyer = relationship("User", back_populates="reservations")


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # active | cancelled
    status: Mapped[str] = mapped_column(String(20), default="active")
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organizer = relationship("User", back_populates="tournaments")
    registrations = relationship("TournamentRegistration", back_populates="tournament", cascade="all, delete-orphan")


class TournamentRegistration(Base):
    __tablename__ = "tournament_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dni_used: Mapped[str | None] = mapped_column(String(20), nullable=True)

    tournament = relationship("Tournament", back_populates="registrations")
    user = relationship("User", back_populates="tournament_registrations")
