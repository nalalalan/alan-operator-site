from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class ClientGateDecision:
    status: str
    message: str
    client_form_url: str = ""
    client_label: str = ""


def _load_gate_entries() -> list[dict[str, Any]]:
    raw_json = os.getenv("CLIENT_GATE_CODES_JSON", "").strip()
    default_url = os.getenv("CLIENT_INTAKE_URL", "").strip()

    if raw_json:
        try:
            data = json.loads(raw_json)
            if isinstance(data, list):
                entries: list[dict[str, Any]] = []
                for item in data:
                    if isinstance(item, dict):
                        code = str(item.get("code", "")).strip()
                        if not code:
                            continue
                        entries.append(
                            {
                                "code": code,
                                "label": str(item.get("label", "")).strip(),
                                "client_form_url": str(item.get("client_form_url", "")).strip() or default_url,
                            }
                        )
                return entries
        except json.JSONDecodeError:
            pass

    raw_codes = os.getenv("CLIENT_GATE_CODES", "").strip()
    if not raw_codes:
        return []

    entries = []
    for code in [x.strip() for x in raw_codes.split(",") if x.strip()]:
        entries.append(
            {
                "code": code,
                "label": "",
                "client_form_url": default_url,
            }
        )
    return entries


def redeem_client_access_code(access_code: str) -> ClientGateDecision:
    code = str(access_code or "").strip()
    if not code:
        return ClientGateDecision(
            status="error",
            message="missing access code",
        )

    for entry in _load_gate_entries():
        if code == entry["code"]:
            form_url = str(entry.get("client_form_url", "")).strip()
            if not form_url:
                return ClientGateDecision(
                    status="error",
                    message="client form url not configured",
                )
            return ClientGateDecision(
                status="ok",
                message="access granted",
                client_form_url=form_url,
                client_label=str(entry.get("label", "")).strip(),
            )

    return ClientGateDecision(
        status="denied",
        message="invalid access code",
    )
