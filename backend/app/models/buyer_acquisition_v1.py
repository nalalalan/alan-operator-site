from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BuyerAcquisitionProspect(Base):
    __tablename__ = "buyer_acquisition_prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    domain: Mapped[str] = mapped_column(String(255), default="", index=True)
    city: Mapped[str] = mapped_column(String(255), default="")
    region: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(255), default="")
    source_name: Mapped[str] = mapped_column(String(255), default="")
    source_query: Mapped[str] = mapped_column(String(255), default="")
    contact_name: Mapped[str] = mapped_column(String(255), default="")
    contact_email: Mapped[str] = mapped_column(String(255), default="", index=True)
    contact_role: Mapped[str] = mapped_column(String(255), default="")
    contact_source: Mapped[str] = mapped_column(String(255), default="")
    website_text: Mapped[str] = mapped_column(Text, default="")
    personalization_line: Mapped[str] = mapped_column(Text, default="")
    fit_score: Mapped[int] = mapped_column(Integer, default=0)
    fit_status: Mapped[str] = mapped_column(String(50), default="new", index=True)
    fit_summary: Mapped[str] = mapped_column(Text, default="")
    send_status: Mapped[str] = mapped_column(String(50), default="new", index=True)
    reply_status: Mapped[str] = mapped_column(String(50), default="none")
    suppression_reason: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    last_outbound_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuyerAcquisitionMessage(Base):
    __tablename__ = "buyer_acquisition_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    prospect_external_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    direction: Mapped[str] = mapped_column(String(20), default="")
    mailbox: Mapped[str] = mapped_column(String(255), default="")
    provider: Mapped[str] = mapped_column(String(50), default="")
    provider_message_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    subject: Mapped[str] = mapped_column(String(255), default="")
    body_text: Mapped[str] = mapped_column(Text, default="")
    from_email: Mapped[str] = mapped_column(String(255), default="")
    to_email: Mapped[str] = mapped_column(String(255), default="")
    classification: Mapped[str] = mapped_column(String(50), default="")
    reply_action: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(50), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
