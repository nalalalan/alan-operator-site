from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from app.services.outbound_50_agency_system_v1 import build_outbound_decision, decisions_to_csv_rows


def process_lead_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    decisions = [build_outbound_decision(r) for r in rows]
    decisions.sort(key=lambda x: (-x.priority_rank, x.company_name.lower()))
    return decisions_to_csv_rows(decisions)


def write_output_csv(rows: List[Dict[str, Any]], target_path: str | Path) -> Path:
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return path
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_digest(rows: List[Dict[str, Any]], target_path: str | Path) -> Path:
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["50-Agency Outbound System digest", ""]
    bucket_counts = {}
    for row in rows:
        bucket_counts[row["priority_bucket"]] = bucket_counts.get(row["priority_bucket"], 0) + 1
    for bucket in ["A", "B", "C", "D"]:
        lines.append(f"{bucket}: {bucket_counts.get(bucket, 0)}")
    lines.append("")
    for row in rows[:15]:
        lines.append(f"- {row['company_name']} | {row['priority_bucket']} | {row['route']} | score={row['score']}")
        lines.append(f"  next: {row['next_action']}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path
