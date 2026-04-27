from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import select

from app.core.config import settings
from app.db.base import SessionLocal
from app.integrations.apollo import ApolloClient
from app.models.acquisition_supervisor import AcquisitionProspect
from app.services.custom_outreach import StepTemplate


router = APIRouter()

GENERIC_INBOX_LOCAL_PARTS = {
    "admin",
    "contact",
    "hello",
    "hi",
    "info",
    "inquiries",
    "mail",
    "marketing",
    "office",
    "sales",
    "support",
    "team",
}

RECOVERY_STEP_TEMPLATES = [
    StepTemplate(
        step_number=1,
        subject="after-call follow-up",
        body=(
            "Hey - quick question.\n\n"
            "When a good sales or client call ends, does your team already have someone who turns the messy notes into the recap, follow-up email, next steps, and CRM update the same day?\n\n"
            "I built Relay for that after-call cleanup. No software setup - you send rough notes, and the finished handoff comes back ready to use.\n\n"
            "Worth sending the sample?\n\n"
            "- Alan"
        ),
        delay_after_prev_days=0,
    ),
    StepTemplate(
        step_number=2,
        subject="re: after-call follow-up",
        body=(
            "Following up once with the concrete version.\n\n"
            "Sample packet:\n"
            "{sample_url}\n\n"
            "The use case is simple: send rough notes from one real call, get back the client-ready recap, follow-up draft, open questions, and CRM-ready update.\n\n"
            "If you have one messy call from this week, I can turn it around as a $40 test.\n\n"
            "- Alan"
        ),
        delay_after_prev_days=1,
    ),
    StepTemplate(
        step_number=3,
        subject="re: after-call follow-up",
        body=(
            "Last note from me.\n\n"
            "If after-call follow-up is a real bottleneck, the lowest-friction test is one call for $40:\n"
            "{packet_checkout_url}\n\n"
            "More detail is here:\n"
            "{landing_page_url}\n\n"
            "If it is not relevant, no worries - I will not keep chasing.\n\n"
            "- Alan"
        ),
        delay_after_prev_days=2,
    ),
]

_original_apollo_search = None
_original_outreach_status = None


def _split_csv(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split(",") if x.strip()]


def _landing_page_url() -> str:
    url = os.getenv("LANDING_PAGE_URL", "").strip() or settings.landing_page_url.strip()
    if not url or "nalalalan.github.io/alan-operator-site" in url:
        return "https://relay.aolabs.io"
    return url.rstrip("/")


def _sample_url() -> str:
    return _landing_page_url().rstrip("/") + "/sample.pdf"


def _is_generic_inbox(email_address: str) -> bool:
    local = (email_address or "").split("@", 1)[0].strip().lower()
    if not local:
        return True
    local_base = local.replace(".", "").replace("-", "").replace("_", "")
    if local in GENERIC_INBOX_LOCAL_PARTS or local_base in GENERIC_INBOX_LOCAL_PARTS:
        return True
    return local.startswith(("info", "hello", "contact", "admin", "support", "sales"))


def _render_body(template: StepTemplate, prospect: AcquisitionProspect) -> str:
    body = template.body.format(
        company_name=prospect.company_name or "there",
        contact_name=prospect.contact_name or "",
        packet_offer_name=settings.packet_offer_name,
        packet_checkout_url=settings.packet_checkout_url,
        landing_page_url=_landing_page_url(),
        sample_url=_sample_url(),
    )
    return body.strip()


def _patched_outreach_status() -> dict[str, Any]:
    assert _original_outreach_status is not None
    status = _original_outreach_status()

    with SessionLocal() as session:
        active_emails = list(
            session.execute(
                select(AcquisitionProspect.contact_email)
                .where(AcquisitionProspect.contact_email != "")
                .where(
                    AcquisitionProspect.status.in_(
                        ["scored", "queued_to_sender", "sent_custom", "sent_to_smartlead"]
                    )
                )
            ).scalars().all()
        )

    generic = sum(1 for email in active_emails if _is_generic_inbox(email))
    status["generic_inbox_count"] = generic
    status["direct_inbox_count"] = max(len(active_emails) - generic, 0)
    return status


async def import_from_apollo_people_search(payload: Dict[str, Any]) -> Dict[str, Any]:
    import app.services.acquisition_supervisor as acq

    client = ApolloClient()
    raw_apollo_payload = payload.get("apollo_payload")
    search_payload: Dict[str, Any] = dict(raw_apollo_payload) if isinstance(raw_apollo_payload, dict) else {}
    q_keywords = str(payload.get("q_keywords") or "").strip()

    search_payload.setdefault("page", int(payload.get("page") or 1))
    search_payload.setdefault("per_page", max(1, min(int(payload.get("per_page") or 25), 100)))
    search_payload.setdefault("person_titles", payload.get("person_titles") or _split_csv(settings.acq_target_person_titles))
    search_payload.setdefault("organization_locations", payload.get("organization_locations") or [settings.default_country])
    search_payload.setdefault("contact_email_status", payload.get("contact_email_status") or ["verified", "guessed"])
    if q_keywords:
        search_payload.setdefault("q_keywords", q_keywords)

    result = await client.search_people(search_payload)
    rows = acq._extract_people_rows(result)

    with acq._session() as session:
        count = 0
        for person in rows:
            organization = person.get("organization") or {}
            email = person.get("email") or person.get("contact_email") or ""
            if not email:
                continue

            acq._upsert_prospect(
                session,
                {
                    **person,
                    "id": person.get("id") or person.get("person_id") or email,
                    "person_id": person.get("id") or person.get("person_id") or "",
                    "company_name": organization.get("name") or person.get("company_name") or "",
                    "website": organization.get("website_url") or person.get("website_url") or person.get("website") or "",
                    "title": person.get("title") or "",
                    "headline": person.get("headline") or q_keywords,
                    "email": email,
                    "source": "apollo_people",
                },
            )
            count += 1
        session.commit()

    return {
        "status": "ok",
        "source": "apollo_people",
        "searched": len(rows),
        "upserted": count,
        "apollo_payload": {
            key: value
            for key, value in search_payload.items()
            if key not in {"api_key", "password", "token"}
        },
    }


async def import_from_apollo_search(payload: Dict[str, Any]) -> Dict[str, Any]:
    source = str(payload.get("source") or os.getenv("ACQ_OPS_SOURCE", "apollo_people")).strip()
    if source == "apollo_people" and settings.apollo_api_key:
        return await import_from_apollo_people_search(payload)
    assert _original_apollo_search is not None
    return await _original_apollo_search(payload)


@router.post("/apollo-people-search")
def apollo_people_search(body: dict, background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_run_apollo_people_search, body)
    return {"status": "accepted"}


def _run_apollo_people_search(body: dict) -> None:
    try:
        asyncio.run(import_from_apollo_people_search(body))
    except Exception as exc:
        print("apollo_people_search error:", exc)


def apply_relay_recovery_patch() -> None:
    global _original_apollo_search, _original_outreach_status

    import app.api.routes.acquisition_supervisor as acq_route
    import app.api.routes.custom_outreach as outreach_route
    import app.services.acquisition_supervisor as acq
    import app.services.autonomous_ops as ops
    import app.services.custom_outreach as outreach

    if _original_apollo_search is None:
        _original_apollo_search = acq.import_from_apollo_search
    if _original_outreach_status is None:
        _original_outreach_status = outreach.outreach_status

    acq.import_from_apollo_search = import_from_apollo_search
    acq.import_from_apollo_people_search = import_from_apollo_people_search
    acq_route.import_from_apollo_search = import_from_apollo_search
    ops.import_from_apollo_search = import_from_apollo_search

    outreach.STEP_TEMPLATES = RECOVERY_STEP_TEMPLATES
    outreach._landing_page_url = _landing_page_url
    outreach._render_body = _render_body
    outreach.outreach_status = _patched_outreach_status
    outreach_route.outreach_status = _patched_outreach_status
