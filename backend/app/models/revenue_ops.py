from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BuyerFitBand(str, Enum):
    STRONG_FIT = "strong_fit"
    LIKELY_FIT = "likely_fit"
    MAYBE_FIT = "maybe_fit"
    LOW_FIT = "low_fit"
    NOT_FIT = "not_fit"


class OpportunityStage(str, Enum):
    INTAKE = "intake"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"
    DELIVERY = "delivery"


class CallType(str, Enum):
    DISCOVERY = "discovery"
    QUALIFICATION = "qualification"
    PROPOSAL_REVIEW = "proposal_review"
    RENEWAL = "renewal"
    EXPANSION = "expansion"
    ONBOARDING = "onboarding"


class BuyerRequest(Base):
    __tablename__ = "buyer_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    agency_name: Mapped[str] = mapped_column(String(255), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    calls_per_week: Mapped[str] = mapped_column(String(50), default="")
    bottleneck: Mapped[str] = mapped_column(Text, default="")
    fit_band: Mapped[BuyerFitBand] = mapped_column(SqlEnum(BuyerFitBand), default=BuyerFitBand.MAYBE_FIT)
    fit_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    buyer_request_id: Mapped[int | None] = mapped_column(ForeignKey("buyer_requests.id"), nullable=True)
    company: Mapped[str] = mapped_column(String(255), default="")
    contact_name: Mapped[str] = mapped_column(String(255), default="")
    contact_email: Mapped[str] = mapped_column(String(255), default="")
    stage: Mapped[OpportunityStage] = mapped_column(SqlEnum(OpportunityStage), default=OpportunityStage.INTAKE)
    fit_band: Mapped[BuyerFitBand] = mapped_column(SqlEnum(BuyerFitBand), default=BuyerFitBand.MAYBE_FIT)
    current_summary: Mapped[str] = mapped_column(Text, default="")
    biggest_risk: Mapped[str] = mapped_column(Text, default="")
    recommended_next_sell: Mapped[str] = mapped_column(Text, default="")
    missing_info: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    calls: Mapped[list["CallRecord"]] = relationship(back_populates="opportunity")
    action_items: Mapped[list["ActionItem"]] = relationship(back_populates="opportunity")
    proposals: Mapped[list["ProposalDraft"]] = relationship(back_populates="opportunity")


class CallRecord(Base):
    __tablename__ = "call_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    call_type: Mapped[CallType] = mapped_column(SqlEnum(CallType), default=CallType.DISCOVERY)
    raw_notes: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    what_matters_most: Mapped[str] = mapped_column(Text, default="")
    immediate_next_step: Mapped[str] = mapped_column(Text, default="")
    open_risks: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="calls")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    owner: Mapped[str] = mapped_column(String(255), default="")
    action_text: Mapped[str] = mapped_column(Text, default="")
    due_hint: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(50), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="action_items")


class ProposalDraft(Base):
    __tablename__ = "proposal_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    proposed_scope: Mapped[str] = mapped_column(Text, default="")
    workstreams: Mapped[str] = mapped_column(Text, default="")
    why_now: Mapped[str] = mapped_column(Text, default="")
    missing_inputs: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="proposals")


class FounderDigest(Base):
    __tablename__ = "founder_digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
