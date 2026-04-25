from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Callable, Dict, List

from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.services.real_lead_source_daily_outbound_v1 import run_real_lead_source_daily_outbound_v1


REQUIRED_HEADERS = [
    "lead_id",
    "company_name",
    "website",
    "contact_name",
    "contact_email",
    "role",
    "vertical",
    "company_type",
    "source",
    "estimated_monthly_call_volume",
    "known_tools",
    "notes",
]


@dataclass
class LeadDropFileResult:
    filename: str
    status: str
    message: str
    target_path: str
    outbound_result: Dict[str, Any] | None = None


@dataclass
class LeadDropIntakeResult:
    inbox_path: str
    processed_path: str
    rejected_path: str
    manifest_path: str
    processed_files: int
    rejected_files: int
    ignored_files: int
    files: List[Dict[str, Any]]


def _session_factory(sf: Callable[[], Session] | None = None) -> Callable[[], Session]:
    return sf or SessionLocal


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_name(name: str) -> str:
    keep = []
    for ch in name:
        if ch.isalnum() or ch in ("-", "_", "."):
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep)


def _hash_file(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


def _ensure_dirs(base_dir: str | Path) -> tuple[Path, Path, Path]:
    base = Path(base_dir)
    inbox = base / "inbox"
    processed = base / "processed"
    rejected = base / "rejected"
    inbox.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    rejected.mkdir(parents=True, exist_ok=True)
    return inbox, processed, rejected


def _validate_csv(path: Path) -> tuple[bool, str]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            missing = [h for h in REQUIRED_HEADERS if h not in headers]
            if missing:
                return False, "missing headers: " + ", ".join(missing)
            rows = list(reader)
            if not rows:
                return False, "no rows found"
            missing_company_rows = [
                str(i + 2) for i, row in enumerate(rows) if not str(row.get("company_name", "")).strip()
            ]
            if missing_company_rows:
                return False, "missing company_name in rows: " + ", ".join(missing_company_rows[:10])
            return True, f"{len(rows)} rows"
    except Exception as exc:
        return False, f"csv validation error: {exc}"


def _validate_json(path: Path) -> tuple[bool, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("records", [])
        if not isinstance(data, list):
            return False, "json must be a list or a dict with records"
        if not data:
            return False, "no records found"
        missing_keys = [h for h in REQUIRED_HEADERS if h not in data[0]]
        if missing_keys:
            return False, "missing keys: " + ", ".join(missing_keys)
        return True, f"{len(data)} rows"
    except Exception as exc:
        return False, f"json validation error: {exc}"


def _validate_source_file(path: Path) -> tuple[bool, str]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _validate_csv(path)
    if suffix == ".json":
        return _validate_json(path)
    return False, "unsupported file type"


def _target_name(path: Path) -> str:
    return f"{_now_stamp()}_{_hash_file(path)}_{_safe_name(path.name)}"


def process_lead_drop_inbox(
    base_dir: str | Path,
    session_factory: Callable[[], Session] | None = None,
    auto_send: bool = False,
    include_b: bool = False,
    daily_send_cap: int = 10,
) -> LeadDropIntakeResult:
    sf = _session_factory(session_factory)
    inbox, processed, rejected = _ensure_dirs(base_dir)
    manifest_path = Path(base_dir) / "lead_drop_manifest.json"

    files_out: List[Dict[str, Any]] = []
    processed_files = 0
    rejected_files = 0
    ignored_files = 0

    candidates = sorted([p for p in inbox.iterdir() if p.is_file()])

    for item in candidates:
        if item.name.startswith("."):
            ignored_files += 1
            files_out.append(
                asdict(
                    LeadDropFileResult(
                        filename=item.name,
                        status="ignored",
                        message="hidden file ignored",
                        target_path=str(item),
                    )
                )
            )
            continue

        valid, reason = _validate_source_file(item)
        if not valid:
            target = rejected / _target_name(item)
            shutil.move(str(item), str(target))
            rejected_files += 1
            files_out.append(
                asdict(
                    LeadDropFileResult(
                        filename=item.name,
                        status="rejected",
                        message=reason,
                        target_path=str(target),
                    )
                )
            )
            continue

        outbound = run_real_lead_source_daily_outbound_v1(
            source_paths=[str(item)],
            session_factory=sf,
            auto_send=auto_send,
            include_b=include_b,
            daily_send_cap=daily_send_cap,
        )
        target = processed / _target_name(item)
        shutil.move(str(item), str(target))
        processed_files += 1
        files_out.append(
            asdict(
                LeadDropFileResult(
                    filename=item.name,
                    status="processed",
                    message=reason,
                    target_path=str(target),
                    outbound_result=asdict(outbound),
                )
            )
        )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inbox_path": str(inbox),
        "processed_path": str(processed),
        "rejected_path": str(rejected),
        "processed_files": processed_files,
        "rejected_files": rejected_files,
        "ignored_files": ignored_files,
        "files": files_out,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return LeadDropIntakeResult(
        inbox_path=str(inbox),
        processed_path=str(processed),
        rejected_path=str(rejected),
        manifest_path=str(manifest_path),
        processed_files=processed_files,
        rejected_files=rejected_files,
        ignored_files=ignored_files,
        files=files_out,
    )
