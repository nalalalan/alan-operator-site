
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AcquisitionProspect(Base):
    __tablename__ = "acquisition_prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    domain: Mapped[str] = mapped_column(String(255), default="", index=True)
    contact_name: Mapped[str] = mapped_column(String(255), default="")
    contact_email: Mapped[str] = mapped_column(String(255), default="", index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(255), default="apollo")
    status: Mapped[str] = mapped_column(String(50), default="new", index=True)
    fit_score: Mapped[int] = mapped_column(Integer, default=0)
    fit_band: Mapped[str] = mapped_column(String(50), default="")
    segment: Mapped[str] = mapped_column(String(100), default="")
    smartlead_campaign_id: Mapped[str] = mapped_column(String(255), default="")
    smartlead_lead_id: Mapped[str] = mapped_column(String(255), default="")
    stripe_status: Mapped[str] = mapped_column(String(50), default="unpaid")
    intake_status: Mapped[str] = mapped_column(String(50), default="not_started")
    last_reply_state: Mapped[str] = mapped_column(String(50), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AcquisitionEvent(Base):
    __tablename__ = "acquisition_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), default="", index=True)
    prospect_external_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
