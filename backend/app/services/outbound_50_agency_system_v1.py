from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import re
from typing import Any, Dict, List

from app.services.acquisition_engine_v1 import run_acquisition_engine_v1


@dataclass
class OutboundLeadRow:
    lead_id: str
    company_name: str
    website: str
    contact_name: str
    contact_email: str
    role: str
    vertical: str
    company_type: str
    source: str
    estimated_monthly_call_volume: int | None
    known_tools: List[str]
    notes: str


@dataclass
class OutboundLeadDecision:
    lead_id: str
    company_name: str
    fit_band: str
    route: str
    priority_bucket: str
    priority_rank: int
    outreach_subject: str
    outreach_body: str
    founder_digest_line: str
    next_action: str
    confidence: str
    score: int


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _parse_int(value: Any) -> int | None:
    text = _norm(value)
    if not text:
        return None
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None


def _parse_tools(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = _norm(value)
    if not text:
        return []
    return [x.strip() for x in text.split(",") if x.strip()]


def normalize_row(row: Dict[str, Any]) -> OutboundLeadRow:
    return OutboundLeadRow(
        lead_id=_norm(row.get("lead_id")),
        company_name=_norm(row.get("company_name")),
        website=_norm(row.get("website")),
        contact_name=_norm(row.get("contact_name")),
        contact_email=_norm(row.get("contact_email")),
        role=_norm(row.get("role")),
        vertical=_norm(row.get("vertical")),
        company_type=_norm(row.get("company_type")),
        source=_norm(row.get("source") or "manual outbound list"),
        estimated_monthly_call_volume=_parse_int(row.get("estimated_monthly_call_volume")),
        known_tools=_parse_tools(row.get("known_tools")),
        notes=_norm(row.get("notes")),
    )


def priority_bucket_for(fit_band: str, route: str, score: int) -> str:
    # A/B are reserved for leads that should actually be worked now.
    if fit_band == "high_priority" and route == "send_now":
        if score >= 7:
            return "A"
        return "B"

    # C is only for real nurture candidates with enough signal to revisit.
    # Weak borderline leads should fall to D instead of cluttering the queue.
    if fit_band == "nurture" and route == "nurture_later":
        if score >= 4:
            return "C"
        return "D"

    return "D"


def priority_rank_for(bucket: str, score: int) -> int:
    base = {"A": 400, "B": 300, "C": 200, "D": 100}[bucket]
    return base + max(min(score, 99), -99)


def build_outbound_decision(row: Dict[str, Any]) -> OutboundLeadDecision:
    lead = normalize_row(row)
    acquisition = run_acquisition_engine_v1(asdict(lead))
    bucket = priority_bucket_for(acquisition.fit_band, acquisition.route, acquisition.score)
    rank = priority_rank_for(bucket, acquisition.score)
    return OutboundLeadDecision(
        lead_id=lead.lead_id,
        company_name=lead.company_name,
        fit_band=acquisition.fit_band,
        route=acquisition.route,
        priority_bucket=bucket,
        priority_rank=rank,
        outreach_subject=acquisition.outreach_subject,
        outreach_body=acquisition.outreach_body,
        founder_digest_line=acquisition.founder_digest_line,
        next_action=acquisition.next_action,
        confidence=acquisition.confidence,
        score=acquisition.score,
    )


def decisions_to_csv_rows(decisions: List[OutboundLeadDecision]) -> List[Dict[str, Any]]:
    rows = []
    for d in decisions:
        rows.append(
            {
                "lead_id": d.lead_id,
                "company_name": d.company_name,
                "fit_band": d.fit_band,
                "route": d.route,
                "priority_bucket": d.priority_bucket,
                "priority_rank": d.priority_rank,
                "confidence": d.confidence,
                "score": d.score,
                "outreach_subject": d.outreach_subject,
                "outreach_body": d.outreach_body,
                "next_action": d.next_action,
                "founder_digest_line": d.founder_digest_line,
            }
        )
    return rows
