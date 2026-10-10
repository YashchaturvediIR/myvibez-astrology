"""Persistent Kundli records. Set DATABASE_URL to PostgreSQL in production."""
import os
from datetime import datetime, timezone
import secrets
from sqlalchemy import create_engine, String, Float, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON

def _database_url():
    url = os.getenv("DATABASE_URL", "sqlite:///./brahmvakya.db")
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

DATABASE_URL = _database_url()
_engine_args = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _engine_args["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **_engine_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class KundliRecord(Base):
    __tablename__ = "kundli_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    report_token: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: secrets.token_urlsafe(24))
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    instagram_username: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="manual")
    query_type: Mapped[str] = mapped_column(String(80), default="kundli")
    dob: Mapped[str] = mapped_column(String(20))
    birth_time: Mapped[str] = mapped_column(String(30))
    birth_place: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="completed", index=True)
    kundli_json: Mapped[dict] = mapped_column(JSON)
    analyses_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

def init_db():
    Base.metadata.create_all(bind=engine)
