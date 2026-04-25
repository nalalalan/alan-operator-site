from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.services.close_path_v1 import close_path_to_dict, decide_close_path


def process_close_opportunities(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    for item in items:
        outputs.append(close_path_to_dict(decide_close_path(item)))
    return outputs


def write_close_digest(outputs: List[Dict[str, Any]], target_path: str | Path) -> Path:
    path = Path(target_path)
    lines = ["Close Path v1 digest", ""]
    for item in outputs:
        lines.append(f"- {item['founder_digest_line']}")
        lines.append(f"  next: {item['next_action']}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path
