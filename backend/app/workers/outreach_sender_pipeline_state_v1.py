from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.services.outreach_sender_pipeline_state_v1 import (
    ingest_reply,
    result_to_dict,
    send_or_queue_candidate,
    transition_to_dict,
)


def process_outreach_candidates(
    candidates: Iterable[Dict[str, Any]],
    existing_dedupe_keys: set[str] | None = None,
) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    dedupe = set(existing_dedupe_keys or set())
    for candidate in candidates:
        result = send_or_queue_candidate(candidate, existing_dedupe_keys=dedupe)
        outputs.append(result_to_dict(result))
        if result.send_status in {"sent", "queued"}:
            dedupe.add(result.dedupe_key)
    return outputs


def process_replies(replies: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    for item in replies:
        transition = ingest_reply(
            lead_id=str(item.get("lead_id", "")).strip(),
            current_state=str(item.get("current_state", "sent")).strip() or "sent",
            reply_text=str(item.get("reply_text", "")).strip(),
        )
        outputs.append(transition_to_dict(transition))
    return outputs


def write_pipeline_digest(
    send_results: List[Dict[str, Any]],
    reply_results: List[Dict[str, Any]],
    target_path: str | Path,
) -> Path:
    path = Path(target_path)
    lines = ["Outreach Sender + Pipeline State v1 digest", ""]
    lines.append("Send/queue results:")
    for item in send_results:
        lines.append(f"- {item['company_name']} | {item['send_status']} | {item['pipeline_state']} | {item['reason']}")
        lines.append(f"  next: {item['next_action']}")
    lines.append("")
    lines.append("Reply transitions:")
    for item in reply_results:
        lines.append(
            f"- {item['lead_id']} | {item['old_state']} -> {item['new_state']} | {item['reply_classification']}"
        )
        lines.append(f"  next: {item['next_action']}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path
