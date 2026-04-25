from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.services.proposal_audit_launcher_v1 import proposal_launch_to_dict, run_proposal_audit_launcher_v1


def process_opportunities(opportunities: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    for item in opportunities:
        decision = run_proposal_audit_launcher_v1(item)
        outputs.append(proposal_launch_to_dict(decision))
    return outputs


def write_launcher_digest(outputs: List[Dict[str, Any]], target_path: str | Path) -> Path:
    path = Path(target_path)
    lines = ["Proposal / Audit Launcher v1 digest", ""]
    for item in outputs:
        lines.append(f"- {item['founder_digest_line']}")
        lines.append(f"  move: {item['best_next_commercial_move']}")
        lines.append(f"  price: {item['recommended_price_guidance']}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path
