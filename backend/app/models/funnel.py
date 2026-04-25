from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FunnelState(str, Enum):
    LEAD_FOUND = "lead_found"
    QUALIFIED = "qualified"
    OUTREACHED = "outreached"
    REPLIED = "replied"
    INTERESTED = "interested"
    PAID = "paid"
    SUBMITTED = "submitted"
    GENERATED = "generated"
    SENT = "sent"
    FAILED = "failed"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(255))
    contact_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    niche: Mapped[str] = mapped_column(String(255), default="marketing agency")
    state: Mapped[FunnelState] = mapped_column(SqlEnum(FunnelState), default=FunnelState.LEAD_FOUND)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
