from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.services.production_wiring_v1 import process_production_event, production_digest


def process_events(events: Iterable[Dict[str, Any]], session_factory=None, auto_send: bool = False) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    for event in events:
        result = process_production_event(event, session_factory=session_factory, auto_send=auto_send)
        outputs.append(result.__dict__)
    return outputs


def write_exception_digest(target_path: str | Path, session_factory=None) -> Path:
    digest = production_digest(session_factory=session_factory)
    path = Path(target_path)
    lines = ["Production Wiring v1 digest", ""]
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
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path
