from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.services.live_revenue_wiring_v1 import load_store, process_event, save_store


def process_events(store_path: str | Path, events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    store = load_store(store_path)
    results: List[Dict[str, Any]] = []
    for event in events:
        result = process_event(store, event)
        results.append(result.__dict__)
    save_store(store_path, store)
    return results


def write_exception_digest(store_path: str | Path, target_path: str | Path) -> Path:
    store = load_store(store_path)
    path = Path(target_path)
    lines = ["Live Revenue Wiring v1 exception digest", ""]
    lines.append("Exceptions:")
    for item in store.get("exceptions", []):
        lines.append(f"- {item['exception_type']} | {item['entity_id']} | {item['summary']}")
    lines.append("")
    lines.append("Action outbox:")
    for item in store.get("action_outbox", []):
        lines.append(f"- {item['action_type']} | {item['entity_id']}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path
