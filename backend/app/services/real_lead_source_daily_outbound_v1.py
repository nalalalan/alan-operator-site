from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.models.production_wiring import ProductionLead
from app.services.outbound_50_agency_system_v1 import build_outbound_decision, normalize_row
from app.services.production_wiring_v1 import process_production_event, production_digest


@dataclass
class DailyOutboundLeadResult:
    lead_id: str
    company_name: str
    source_name: str
    priority_bucket: str
    route: str
    score: int
    outcome: str
    summary: str


@dataclass
class RealLeadSourceDailyOutboundResult:
    total_candidates: int
    selected_for_send: int
    sent_now: int
    queued: int
    skipped_existing: int
    skipped_blocked: int
    skipped_low_priority: int
    ignored: int
    rows: List[Dict[str, Any]]


def _session_factory(sf: Callable[[], Session] | None = None) -> Callable[[], Session]:
    return sf or SessionLocal


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv_list_env(name: str) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


def _event_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _priority_rank(bucket: str, score: int) -> int:
    base = {"A": 400, "B": 300, "C": 200, "D": 100}.get(bucket, 0)
    return base + score


def _allowed_buckets(include_b: bool) -> set[str]:
    return {"A", "B"} if include_b else {"A"}


def _infer_source_name(record: dict[str, Any], path: str) -> str:
    explicit = str(record.get("source_name", "")).strip()
    if explicit:
        return explicit
    source = str(record.get("source", "")).strip()
    if source:
        return source
    return Path(path).name


def _records_from_json(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        records = data.get("records")
        if isinstance(records, list):
            return [x for x in records if isinstance(x, dict)]
    raise ValueError(f"Unsupported JSON format for {path}")


def _records_from_csv(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_real_lead_source_records(source_paths: Iterable[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_path in source_paths:
        path = str(raw_path).strip()
        if not path:
            continue
        suffix = Path(path).suffix.lower()
        if suffix == ".json":
            chunk = _records_from_json(path)
        elif suffix == ".csv":
            chunk = _records_from_csv(path)
        else:
            raise ValueError(f"Unsupported source file type: {path}")
        for item in chunk:
            enriched = dict(item)
            enriched["source_name"] = _infer_source_name(enriched, path)
            records.append(enriched)
    return records


def _email_domain(record: dict[str, Any]) -> str:
    email = str(record.get("contact_email", "")).strip().lower()
    if "@" in email:
        return email.split("@", 1)[1]
    website = str(record.get("website", "")).strip().lower()
    if website.startswith("http://"):
        website = website[7:]
    if website.startswith("https://"):
        website = website[8:]
    website = website.strip("/")
    if website.startswith("www."):
        website = website[4:]
    return website


def _is_blocked(record: dict[str, Any], blocked_emails: set[str], blocked_domains: set[str]) -> bool:
    email = str(record.get("contact_email", "")).strip().lower()
    domain = _email_domain(record)
    return (email and email in blocked_emails) or (domain and domain in blocked_domains)


def _already_exists(session_factory: Callable[[], Session], record: dict[str, Any]) -> bool:
    email = str(record.get("contact_email", "")).strip()
    company = str(record.get("company_name", "")).strip()
    if not email and not company:
        return False
    with session_factory() as session:
        stmt = select(ProductionLead)
        clauses = []
        if email:
            clauses.append(ProductionLead.contact_email == email)
        if company:
            clauses.append(ProductionLead.company_name == company)
        stmt = stmt.where(or_(*clauses))
        existing = session.execute(stmt).scalars().first()
        return existing is not None


def run_real_lead_source_daily_outbound_v1(
    source_paths: list[str],
    session_factory: Callable[[], Session] | None = None,
    auto_send: bool | None = None,
    include_b: bool = False,
    daily_send_cap: int = 10,
) -> RealLeadSourceDailyOutboundResult:
    sf = _session_factory(session_factory)
    auto_send = _bool_env("REAL_LEAD_OUTBOUND_AUTO_SEND", False) if auto_send is None else auto_send

    blocked_emails = set(_csv_list_env("REAL_LEAD_BLOCKED_EMAILS"))
    blocked_domains = set(_csv_list_env("REAL_LEAD_BLOCKED_DOMAINS"))

    raw_records = load_real_lead_source_records(source_paths)
    total_candidates = len(raw_records)

    evaluated: list[dict[str, Any]] = []
    skipped_blocked = 0
    skipped_existing = 0
    skipped_low_priority = 0
    selected_for_send = 0
    sent_now = 0
    queued = 0
    ignored = 0

    for raw in raw_records:
        normalized = normalize_row(raw)
        source_name = _infer_source_name(raw, str(raw.get("source_name", "")))

        if _is_blocked(asdict(normalized), blocked_emails, blocked_domains):
            skipped_blocked += 1
            evaluated.append(
                asdict(
                    DailyOutboundLeadResult(
                        lead_id=normalized.lead_id,
                        company_name=normalized.company_name,
                        source_name=source_name,
                        priority_bucket="",
                        route="",
                        score=0,
                        outcome="blocked",
                        summary="blocked by email/domain rules",
                    )
                )
            )
            continue

        if _already_exists(sf, asdict(normalized)):
            skipped_existing += 1
            evaluated.append(
                asdict(
                    DailyOutboundLeadResult(
                        lead_id=normalized.lead_id,
                        company_name=normalized.company_name,
                        source_name=source_name,
                        priority_bucket="",
                        route="",
                        score=0,
                        outcome="existing",
                        summary="lead already exists in production store",
                    )
                )
            )
            continue

        decision = build_outbound_decision(raw)
        record = {
            "normalized": asdict(normalized),
            "source_name": source_name,
            "decision": decision,
        }

        if decision.priority_bucket not in _allowed_buckets(include_b) or decision.route != "send_now":
            skipped_low_priority += 1
            evaluated.append(
                asdict(
                    DailyOutboundLeadResult(
                        lead_id=normalized.lead_id,
                        company_name=normalized.company_name,
                        source_name=source_name,
                        priority_bucket=decision.priority_bucket,
                        route=decision.route,
                        score=decision.score,
                        outcome="low_priority",
                        summary="not in active send set",
                    )
                )
            )
            continue

        evaluated.append(record)

    sendable = [x for x in evaluated if "decision" in x]
    sendable.sort(
        key=lambda x: (
            _priority_rank(x["decision"].priority_bucket, x["decision"].score),
            x["decision"].score,
            x["normalized"].get("company_name", ""),
        ),
        reverse=True,
    )
    sendable = sendable[: max(daily_send_cap, 0)]

    results_rows: list[dict[str, Any]] = [x for x in evaluated if "decision" not in x]

    for item in sendable:
        selected_for_send += 1
        payload = item["normalized"]
        decision = item["decision"]
        source_name = item["source_name"]

        event = {
            "event_id": _event_id("daily-lead", json.dumps(payload, sort_keys=True)),
            "event_type": "lead_found",
            "payload": payload,
        }
        result = process_production_event(event, session_factory=sf, auto_send=auto_send)

        outcome = "processed"
        if result.status == "processed":
            if any(a.get("action_type") == "send_outreach" for a in result.actions_created):
                sent_now += 1
                outcome = "sent_now"
            elif any(a.get("action_type") == "nurture_queue" for a in result.actions_created):
                queued += 1
                outcome = "queued"
            else:
                ignored += 1
                outcome = "ignored"
        elif result.status == "ignored":
            ignored += 1
            outcome = "ignored"

        results_rows.append(
            asdict(
                DailyOutboundLeadResult(
                    lead_id=payload.get("lead_id", ""),
                    company_name=payload.get("company_name", ""),
                    source_name=source_name,
                    priority_bucket=decision.priority_bucket,
                    route=decision.route,
                    score=decision.score,
                    outcome=outcome,
                    summary=result.summary,
                )
            )
        )

    results_rows.sort(key=lambda x: (x.get("outcome", ""), x.get("company_name", "")))
    return RealLeadSourceDailyOutboundResult(
        total_candidates=total_candidates,
        selected_for_send=selected_for_send,
        sent_now=sent_now,
        queued=queued,
        skipped_existing=skipped_existing,
        skipped_blocked=skipped_blocked,
        skipped_low_priority=skipped_low_priority,
        ignored=ignored,
        rows=results_rows,
    )


def write_real_lead_daily_outbound_digest(target_path: str, session_factory: Callable[[], Session] | None = None) -> str:
    digest = production_digest(session_factory=session_factory)
    lines = ["Real Lead Source + Daily Outbound Autopilot v1 digest", ""]
    lines.append(f"lead_count: {digest['lead_count']}")
    lines.append(f"action_count: {digest['action_count']}")
    lines.append(f"open_exception_count: {digest['open_exception_count']}")
    lines.append("")
    lines.append("Paid / queued:")
    for item in digest["paid_or_queued"]:
        lines.append(
            f"- {item['company_name']} | close={item['close_state']} | fulfillment={item['fulfillment_state']}"
        )
    lines.append("")
    lines.append("Exceptions:")
    for item in digest["exceptions"]:
        lines.append(f"- {item['exception_type']} | {item['entity_external_id']} | {item['summary']}")
    p = Path(target_path)
    p.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return str(p)
