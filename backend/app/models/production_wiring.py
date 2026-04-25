from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductionLead(Base):
    __tablename__ = "production_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), default="")
    contact_name: Mapped[str] = mapped_column(String(255), default="")
    contact_email: Mapped[str] = mapped_column(String(255), default="", index=True)
    website: Mapped[str] = mapped_column(String(255), default="")
    vertical: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(255), default="")
    estimated_monthly_call_volume: Mapped[str] = mapped_column(String(50), default="")
    fit_band: Mapped[str] = mapped_column(String(50), default="")
    fit_score: Mapped[int] = mapped_column(Integer, default=0)
    route: Mapped[str] = mapped_column(String(50), default="")
    lead_state: Mapped[str] = mapped_column(String(50), default="new")
    pipeline_state: Mapped[str] = mapped_column(String(50), default="new")
    close_state: Mapped[str] = mapped_column(String(50), default="new")
    fulfillment_state: Mapped[str] = mapped_column(String(50), default="not_started")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductionOpportunity(Base):
    __tablename__ = "production_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    lead_external_id: Mapped[str] = mapped_column(String(255), index=True)
    company_name: Mapped[str] = mapped_column(String(255), default="")
    launch_type: Mapped[str] = mapped_column(String(50), default="")
    recommended_offer: Mapped[str] = mapped_column(String(255), default="")
    price_guidance: Mapped[str] = mapped_column(String(255), default="")
    best_next_commercial_move: Mapped[str] = mapped_column(Text, default="")
    close_route: Mapped[str] = mapped_column(String(50), default="")
    opportunity_state: Mapped[str] = mapped_column(String(50), default="new")
    buyer_email_subject: Mapped[str] = mapped_column(String(255), default="")
    buyer_email_body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductionAction(Base):
    __tablename__ = "production_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), default="")
    entity_external_id: Mapped[str] = mapped_column(String(255), index=True)
    action_type: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    dedupe_key: Mapped[str] = mapped_column(String(100), default="", index=True)
    to_email: Mapped[str] = mapped_column(String(255), default="")
    subject: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    provider_message_id: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductionException(Base):
    __tablename__ = "production_exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_external_id: Mapped[str] = mapped_column(String(255), index=True)
    exception_type: Mapped[str] = mapped_column(String(100), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProductionTransition(Base):
    __tablename__ = "production_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    entity_external_id: Mapped[str] = mapped_column(String(255), index=True)
    event_type: Mapped[str] = mapped_column(String(100), default="")
    old_state: Mapped[str] = mapped_column(String(100), default="")
    new_state: Mapped[str] = mapped_column(String(100), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
