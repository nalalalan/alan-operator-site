from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict

from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.services.lead_drop_intake_v1 import process_lead_drop_inbox
from app.services.production_wiring_v1 import production_digest


@dataclass
class DailyLeadDropRunnerResult:
    base_dir: str
    intake_result: Dict[str, Any]
    digest_path: str
    digest_summary: Dict[str, Any]


def _session_factory(sf: Callable[[], Session] | None = None) -> Callable[[], Session]:
    return sf or SessionLocal


def _write_digest(target_path: str | Path, digest: Dict[str, Any]) -> str:
    p = Path(target_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    lines = ["Daily Lead Drop Runner + Digest v1", ""]
    lines.append(f"lead_count: {digest['lead_count']}")
    lines.append(f"action_count: {digest['action_count']}")
    lines.append(f"open_exception_count: {digest['open_exception_count']}")
    lines.append("")

    lines.append("Paid / queued:")
    paid = digest.get("paid_or_queued", [])
    if paid:
        for item in paid:
            lines.append(
                f"- {item['company_name']} | close={item['close_state']} | fulfillment={item['fulfillment_state']}"
            )
    else:
        lines.append("- none")

    lines.append("")
    lines.append("Exceptions:")
    exceptions = digest.get("exceptions", [])
    if exceptions:
        for item in exceptions:
            lines.append(f"- {item['exception_type']} | {item['entity_external_id']} | {item['summary']}")
    else:
        lines.append("- none")

    p.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return str(p)


def run_daily_lead_drop_runner(
    base_dir: str,
    session_factory: Callable[[], Session] | None = None,
    auto_send: bool = False,
    include_b: bool = False,
    daily_send_cap: int = 10,
) -> DailyLeadDropRunnerResult:
    sf = _session_factory(session_factory)

    intake = process_lead_drop_inbox(
        base_dir=base_dir,
        session_factory=sf,
        auto_send=auto_send,
        include_b=include_b,
        daily_send_cap=daily_send_cap,
    )

    digest = production_digest(session_factory=sf)
    digest_path = _write_digest(Path(base_dir) / "daily_digest.txt", digest)

    return DailyLeadDropRunnerResult(
        base_dir=base_dir,
        intake_result=intake.__dict__,
        digest_path=digest_path,
        digest_summary=digest,
    )
