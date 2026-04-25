from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Literal

from app.services.acquisition_engine_v1 import classify_reply


PipelineState = Literal[
    "new",
    "queued",
    "sent",
    "replied_interested",
    "replied_needs_info",
    "replied_not_now",
    "replied_not_fit",
    "skipped",
]


@dataclass
class OutreachCandidate:
    lead_id: str
    company_name: str
    contact_name: str
    contact_email: str
    fit_band: str
    route: str
    outreach_subject: str
    outreach_body: str
    founder_digest_line: str
    next_action: str
    source: str = ""
    state: PipelineState = "new"


@dataclass
class OutreachSendResult:
    lead_id: str
    company_name: str
    contact_email: str
    send_status: Literal["sent", "queued", "skipped", "duplicate_blocked"]
    pipeline_state: PipelineState
    dedupe_key: str
    reason: str
    subject: str
    founder_digest_line: str
    next_action: str


@dataclass
class ReplyTransition:
    lead_id: str
    reply_text: str
    reply_classification: str
    old_state: PipelineState
    new_state: PipelineState
    next_action: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def dedupe_key_for(lead_id: str, subject: str, email: str) -> str:
    raw = f"{lead_id}|{subject}|{email}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def normalize_candidate(payload: Dict[str, Any]) -> OutreachCandidate:
    return OutreachCandidate(
        lead_id=str(payload.get("lead_id", "")).strip(),
        company_name=str(payload.get("company_name", "")).strip(),
        contact_name=str(payload.get("contact_name", "")).strip(),
        contact_email=str(payload.get("contact_email", "")).strip(),
        fit_band=str(payload.get("fit_band", "")).strip(),
        route=str(payload.get("route", "")).strip(),
        outreach_subject=str(payload.get("outreach_subject", "")).strip(),
        outreach_body=str(payload.get("outreach_body", "")).strip(),
        founder_digest_line=str(payload.get("founder_digest_line", "")).strip(),
        next_action=str(payload.get("next_action", "")).strip(),
        source=str(payload.get("source", "")).strip(),
        state=str(payload.get("state", "new")).strip() or "new",
    )


def should_send(candidate: OutreachCandidate) -> tuple[bool, str]:
    if not candidate.contact_email:
        return False, "missing contact email"
    if candidate.route == "send_now":
        return True, "high-priority lead ready for outreach"
    if candidate.route == "nurture_later":
        return False, "lead is nurture-only right now"
    return False, "lead is not active for outreach"


def send_or_queue_candidate(
    candidate_payload: Dict[str, Any],
    existing_dedupe_keys: set[str] | None = None,
) -> OutreachSendResult:
    existing_dedupe_keys = existing_dedupe_keys or set()
    candidate = normalize_candidate(candidate_payload)
    key = dedupe_key_for(candidate.lead_id, candidate.outreach_subject, candidate.contact_email)

    if key in existing_dedupe_keys:
        return OutreachSendResult(
            lead_id=candidate.lead_id,
            company_name=candidate.company_name,
            contact_email=candidate.contact_email,
            send_status="duplicate_blocked",
            pipeline_state="queued" if candidate.route == "nurture_later" else "sent",
            dedupe_key=key,
            reason="duplicate outreach blocked",
            subject=candidate.outreach_subject,
            founder_digest_line=candidate.founder_digest_line,
            next_action="Do nothing. Outreach with the same subject already exists.",
        )

    allow_send, reason = should_send(candidate)
    if allow_send:
        return OutreachSendResult(
            lead_id=candidate.lead_id,
            company_name=candidate.company_name,
            contact_email=candidate.contact_email,
            send_status="sent",
            pipeline_state="sent",
            dedupe_key=key,
            reason=reason,
            subject=candidate.outreach_subject,
            founder_digest_line=candidate.founder_digest_line,
            next_action="Wait for reply and classify it automatically.",
        )

    if candidate.route == "nurture_later":
        return OutreachSendResult(
            lead_id=candidate.lead_id,
            company_name=candidate.company_name,
            contact_email=candidate.contact_email,
            send_status="queued",
            pipeline_state="queued",
            dedupe_key=key,
            reason=reason,
            subject=candidate.outreach_subject,
            founder_digest_line=candidate.founder_digest_line,
            next_action="Keep in nurture queue until better timing or stronger context appears.",
        )

    return OutreachSendResult(
        lead_id=candidate.lead_id,
        company_name=candidate.company_name,
        contact_email=candidate.contact_email,
        send_status="skipped",
        pipeline_state="skipped",
        dedupe_key=key,
        reason=reason,
        subject=candidate.outreach_subject,
        founder_digest_line=candidate.founder_digest_line,
        next_action="No outreach. Leave out of the active pipeline.",
    )


def state_for_reply_classification(reply_classification: str, current_state: PipelineState) -> PipelineState:
    if current_state not in {"sent", "replied_interested", "replied_needs_info", "replied_not_now", "replied_not_fit"}:
        return current_state

    mapping = {
        "interested": "replied_interested",
        "needs_info": "replied_needs_info",
        "not_now": "replied_not_now",
        "not_fit": "replied_not_fit",
        "unknown": current_state,
        "no_reply": current_state,
    }
    return mapping.get(reply_classification, current_state)


def next_action_for_reply_state(state: PipelineState) -> str:
    mapping = {
        "replied_interested": "Send the concrete paid next step or booking path now.",
        "replied_needs_info": "Answer the question and route into Proposal / Audit Launcher if still warm.",
        "replied_not_now": "Set follow-up for later and keep out of the main attention loop.",
        "replied_not_fit": "Close the loop and remove from active pipeline.",
        "sent": "Wait for reply and classify it automatically.",
        "queued": "Leave in nurture queue until timing improves.",
        "skipped": "Ignore unless the lead changes materially.",
        "new": "Run send/queue decision first.",
    }
    return mapping[state]


def ingest_reply(
    lead_id: str,
    current_state: PipelineState,
    reply_text: str,
) -> ReplyTransition:
    classification = classify_reply(reply_text)
    new_state = state_for_reply_classification(classification, current_state)
    return ReplyTransition(
        lead_id=lead_id,
        reply_text=reply_text,
        reply_classification=classification,
        old_state=current_state,
        new_state=new_state,
        next_action=next_action_for_reply_state(new_state),
    )


def result_to_dict(result: OutreachSendResult) -> Dict[str, Any]:
    return asdict(result)


def transition_to_dict(transition: ReplyTransition) -> Dict[str, Any]:
    return asdict(transition)
