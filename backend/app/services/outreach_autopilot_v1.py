from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from typing import Any, Callable, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.models.production_wiring import ProductionLead
from app.services.outbound_50_agency_system_v1 import build_outbound_decision, normalize_row
from app.services.production_wiring_v1 import process_production_event, production_digest


@dataclass
class OutboundAutopilotBatchResult:
    processed: int
    sent_now: int
    queued: int
    skipped: int
    ignored: int
    rows: List[Dict[str, Any]]


@dataclass
class ReplyAutopilotResult:
    status: str
    lead_id: str
    company_name: str
    close_state: str
    summary: str


def _session_factory(sf: Callable[[], Session] | None = None) -> Callable[[], Session]:
    return sf or SessionLocal


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _allowed_buckets(include_b: bool) -> set[str]:
    return {"A", "B"} if include_b else {"A"}


def _event_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def run_outreach_autopilot_batch(
    csv_path: str,
    session_factory: Callable[[], Session] | None = None,
    auto_send: bool | None = None,
    include_b: bool = False,
) -> OutboundAutopilotBatchResult:
    sf = _session_factory(session_factory)
    auto_send = _bool_env("OUTREACH_AUTOPILOT_AUTO_SEND", False) if auto_send is None else auto_send

    rows: List[Dict[str, Any]] = []
    processed = 0
    sent_now = 0
    queued = 0
    skipped = 0
    ignored = 0

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            processed += 1
            normalized = normalize_row(raw)
            decision = build_outbound_decision(raw)

            record = {
                "lead_id": decision.lead_id,
                "company_name": decision.company_name,
                "priority_bucket": decision.priority_bucket,
                "route": decision.route,
                "score": decision.score,
                "fit_band": decision.fit_band,
                "status": "",
                "summary": "",
            }

            if decision.priority_bucket not in _allowed_buckets(include_b) or decision.route != "send_now":
                record["status"] = "skipped"
                record["summary"] = "not in active autopilot send set"
                skipped += 1
                rows.append(record)
                continue

            payload = asdict(normalized)

            result = process_production_event(
                {
                    "event_id": _event_id("lead-found", json.dumps(payload, sort_keys=True)),
                    "event_type": "lead_found",
                    "payload": payload,
                },
                session_factory=sf,
                auto_send=auto_send,
            )

            record["status"] = result.status
            record["summary"] = result.summary

            if result.status == "processed":
                if any(a.get("action_type") == "send_outreach" for a in result.actions_created):
                    sent_now += 1
                elif any(a.get("action_type") == "nurture_queue" for a in result.actions_created):
                    queued += 1
                else:
                    ignored += 1
            elif result.status == "ignored":
                ignored += 1
            else:
                skipped += 1

            rows.append(record)

    return OutboundAutopilotBatchResult(
        processed=processed,
        sent_now=sent_now,
        queued=queued,
        skipped=skipped,
        ignored=ignored,
        rows=rows,
    )


def ingest_reply_autopilot(
    from_email: str,
    reply_text: str,
    provider_message_id: str = "",
    session_factory: Callable[[], Session] | None = None,
    auto_send: bool | None = None,
) -> ReplyAutopilotResult:
    sf = _session_factory(session_factory)
    auto_send = _bool_env("OUTREACH_AUTOPILOT_AUTO_SEND", False) if auto_send is None else auto_send

    with sf() as session:
        stmt = select(ProductionLead).where(ProductionLead.contact_email == from_email)
        lead = session.execute(stmt).scalar_one_or_none()
        if lead is None:
            return ReplyAutopilotResult(
                status="error",
                lead_id="",
                company_name="",
                close_state="",
                summary="reply email did not map to a known lead",
            )
        lead_id = lead.external_id
        company_name = lead.company_name

    seed = provider_message_id or f"{from_email}|{reply_text}"
    result = process_production_event(
        {
            "event_id": _event_id("reply", seed),
            "event_type": "reply_received",
            "payload": {
                "lead_id": lead_id,
                "reply_text": reply_text,
            },
        },
        session_factory=sf,
        auto_send=auto_send,
    )

    return ReplyAutopilotResult(
        status=result.status,
        lead_id=lead_id,
        company_name=company_name,
        close_state=result.close_state,
        summary=result.summary,
    )


def write_outreach_autopilot_digest(target_path: str, session_factory: Callable[[], Session] | None = None) -> str:
    digest = production_digest(session_factory=session_factory)
    lines = ["Outreach Autopilot v1 digest", ""]
    lines.append(f"lead_count: {digest['lead_count']}")
    lines.append(f"action_count: {digest['action_count']}")
    lines.append(f"open_exception_count: {digest['open_exception_count']}")
    lines.append("")
    lines.append("Paid / queued:")
    for item in digest["paid_or_queued"]:
        lines.append(f"- {item['company_name']} | close={item['close_state']} | fulfillment={item['fulfillment_state']}")
    lines.append("")
    lines.append("Exceptions:")
    for item in digest["exceptions"]:
        lines.append(f"- {item['exception_type']} | {item['entity_external_id']} | {item['summary']}")
    PathLike = __import__("pathlib").Path
    p = PathLike(target_path)
    p.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return str(p)
