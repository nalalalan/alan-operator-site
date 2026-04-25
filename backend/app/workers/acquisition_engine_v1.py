from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.services.acquisition_engine_v1 import acquisition_decision_to_dict, run_acquisition_engine_v1


def process_leads(submissions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    for submission in submissions:
        decision = run_acquisition_engine_v1(submission)
        outputs.append(acquisition_decision_to_dict(decision))
    return outputs


def write_founder_digest(outputs: List[Dict[str, Any]], target_path: str | Path) -> Path:
    path = Path(target_path)
    lines = ["Acquisition Engine v1 founder digest", ""]
    for item in outputs:
        lines.append(f"- {item['founder_digest_line']}")
        lines.append(f"  next: {item['next_action']}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path
