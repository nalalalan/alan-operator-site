from __future__ import annotations

import html
import os
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import SessionLocal
from app.integrations.resend_client import ResendClient
from app.models.acquisition_supervisor import AcquisitionEvent, AcquisitionProspect


def _session() -> Session:
    return SessionLocal()


def _intake_url() -> str:
    return (
        settings.client_intake_destination
        or os.getenv("CLIENT_INTAKE_URL", "").strip()
    )


def _pack_url() -> str:
    return (
        os.getenv("PACKET_5_PACK_URL", "").strip()
        or settings.packet_checkout_url
    )


def _monthly_url() -> str:
    return (
        os.getenv("MONTHLY_AUTOPILOT_URL", "").strip()
        or settings.landing_page_url
    )


def _find_prospect_by_email(session: Session, email: str) -> AcquisitionProspect | None:
    stmt = select(AcquisitionProspect).where(AcquisitionProspect.contact_email == email)
    return session.execute(stmt).scalar_one_or_none()


def _event_exists(session: Session, prospect_external_id: str, event_type: str) -> bool:
    stmt = (
        select(AcquisitionEvent.id)
        .where(AcquisitionEvent.prospect_external_id == prospect_external_id)
        .where(AcquisitionEvent.event_type == event_type)
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none() is not None


def _log_event(
    session: Session,
    event_type: str,
    prospect_external_id: str,
    summary: str,
    payload: Dict[str, Any] | None = None,
) -> None:
    session.add(
        AcquisitionEvent(
            event_type=event_type,
            prospect_external_id=prospect_external_id,
            summary=summary,
            payload_json=(__import__("json").dumps(payload or {}, ensure_ascii=False)),
        )
    )


def _send_html_email(to_email: str, subject: str, blocks: list[str]) -> dict[str, Any]:
    body = "<div style='font-family:Arial,Helvetica,sans-serif;font-size:16px;color:#1f1f1f;line-height:1.6;'>" + "".join(blocks) + "</div>"
    client = ResendClient()
    return client.send_email(
        to_email=to_email,
        subject=subject,
        html=body,
        from_email=settings.from_email_fulfillment or settings.from_email_outbound,
        reply_to=settings.reply_to_email,
    )


def _p(text: str) -> str:
    return f"<p style='margin:0 0 16px 0'>{html.escape(text)}</p>"


def send_paid_onboarding_for_email(email: str) -> dict[str, Any]:
    email = (email or "").strip().lower()
    if not email:
        return {"status": "ignored", "summary": "missing email"}

    with _session() as session:
        prospect = _find_prospect_by_email(session, email)
        if prospect is None:
            return {"status": "ignored", "summary": "no matching prospect"}
        if _event_exists(session, prospect.external_id, "autopilot_paid_onboarding_sent"):
            return {"status": "skipped", "summary": "already sent"}

        intake_url = _intake_url()
        if not intake_url:
            return {"status": "ignored", "summary": "missing intake url"}

        company = prospect.company_name or "your team"
        subject = "You're in - send the call"
        blocks = [
            _p(f"Thanks - you're in for {company}."),
            _p("Next step is just sending the details for the first real call."),
            _p(f"Intake: {intake_url}"),
            _p("Once that comes through, the packet gets built and sent back automatically."),
            _p("- Alan"),
        ]
        send_result = _send_html_email(email, subject, blocks)
        _log_event(
            session,
            "autopilot_paid_onboarding_sent",
            prospect.external_id,
            "sent paid onboarding email",
            {"email": email, "send_result": send_result},
        )
        session.commit()
        return {"status": "sent", "summary": "paid onboarding sent", "send_result": send_result}


def send_intake_ack_for_email(email: str) -> dict[str, Any]:
    email = (email or "").strip().lower()
    if not email:
        return {"status": "ignored", "summary": "missing email"}

    with _session() as session:
        prospect = _find_prospect_by_email(session, email)
        if prospect is None:
            return {"status": "ignored", "summary": "no matching prospect"}
        if _event_exists(session, prospect.external_id, "autopilot_intake_ack_sent"):
            return {"status": "skipped", "summary": "already sent"}

        subject = "Got it - packet is in motion"
        blocks = [
            _p("Got it."),
            _p("I have what I need from the intake and the packet is in motion."),
            _p("You'll get the finished recap, next steps, and follow-up draft automatically."),
            _p("- Alan"),
        ]
        send_result = _send_html_email(email, subject, blocks)
        _log_event(
            session,
            "autopilot_intake_ack_sent",
            prospect.external_id,
            "sent intake acknowledgement",
            {"email": email, "send_result": send_result},
        )
        session.commit()
        return {"status": "sent", "summary": "intake ack sent", "send_result": send_result}


def run_paid_intake_reminder_sweep(hours: int = 12) -> dict[str, Any]:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    sent_count = 0
    skipped = 0

    with _session() as session:
        paid_events = session.execute(
            select(AcquisitionEvent)
            .where(AcquisitionEvent.event_type == "stripe_paid")
            .where(AcquisitionEvent.created_at <= cutoff)
            .order_by(AcquisitionEvent.created_at.asc())
        ).scalars().all()

        for event in paid_events:
            stmt = select(AcquisitionProspect).where(AcquisitionProspect.external_id == event.prospect_external_id)
            prospect = session.execute(stmt).scalar_one_or_none()
            if prospect is None:
                skipped += 1
                continue

            if prospect.intake_status != "not_started":
                skipped += 1
                continue

            if _event_exists(session, prospect.external_id, "autopilot_intake_reminder_sent"):
                skipped += 1
                continue

            intake_url = _intake_url()
            if not intake_url or not prospect.contact_email:
                skipped += 1
                continue

            subject = "Quick reminder - send the call details"
            blocks = [
                _p("Quick reminder - I still need the call details to generate the packet."),
                _p(f"Intake: {intake_url}"),
                _p("Once that is in, the packet gets built automatically."),
                _p("- Alan"),
            ]
            send_result = _send_html_email(prospect.contact_email, subject, blocks)
            _log_event(
                session,
                "autopilot_intake_reminder_sent",
                prospect.external_id,
                "sent intake reminder",
                {"send_result": send_result},
            )
            sent_count += 1

        session.commit()

    return {"status": "ok", "sent_count": sent_count, "skipped": skipped, "hours": hours}


def run_post_delivery_upsell_sweep(hours: int = 24) -> dict[str, Any]:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    sent_count = 0
    skipped = 0

    with _session() as session:
        intake_events = session.execute(
            select(AcquisitionEvent)
            .where(AcquisitionEvent.event_type == "intake_received")
            .where(AcquisitionEvent.created_at <= cutoff)
            .order_by(AcquisitionEvent.created_at.asc())
        ).scalars().all()

        for event in intake_events:
            stmt = select(AcquisitionProspect).where(AcquisitionProspect.external_id == event.prospect_external_id)
            prospect = session.execute(stmt).scalar_one_or_none()
            if prospect is None:
                skipped += 1
                continue

            if _event_exists(session, prospect.external_id, "autopilot_upsell_sent"):
                skipped += 1
                continue

            if not prospect.contact_email:
                skipped += 1
                continue

            subject = "Want this for more calls?"
            blocks = [
                _p("If you want this for more calls, easiest move is just to use the next-step links below."),
                _p(f"5-pack / next packet: {_pack_url()}"),
                _p(f"Monthly / site: {_monthly_url()}"),
                _p("If you do want the same flow running automatically for future calls, that's the path."),
                _p("- Alan"),
            ]
            send_result = _send_html_email(prospect.contact_email, subject, blocks)
            _log_event(
                session,
                "autopilot_upsell_sent",
                prospect.external_id,
                "sent upsell email",
                {"send_result": send_result},
            )
            sent_count += 1

        session.commit()

    return {"status": "ok", "sent_count": sent_count, "skipped": skipped, "hours": hours}
