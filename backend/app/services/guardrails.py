from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

SAFE_PLACEHOLDER = "your agency"

_PROFANITY_PATTERNS = [
    r"\bfuck\b",
    r"\bfucking\b",
    r"\bshit\b",
    r"\bbitch\b",
    r"\bcunt\b",
    r"\bmotherfucker\b",
]

_SELF_HARM_PATTERNS = [
    r"\bkms\b",
    r"kill myself",
    r"want to die",
    r"wanna die",
    r"end my life",
    r"suicide",
    r"self-harm",
    r"self harm",
]

_JUNK_PATTERNS = [
    r"^idk$",
    r"^test$",
    r"^asdf+$",
    r"^qwer+$",
    r"^n/?a$",
    r"^none$",
    r"^blah+$",
]


@dataclass
class ClientGateResult:
    status: Literal["ok", "needs_more_detail", "unsafe"]
    reason: str


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def contains_profanity(text: str) -> bool:
    norm = _norm(text)
    return any(re.search(p, norm) for p in _PROFANITY_PATTERNS)


def contains_self_harm(text: str) -> bool:
    norm = _norm(text)
    return any(re.search(p, norm) for p in _SELF_HARM_PATTERNS)


def looks_like_junk(text: str) -> bool:
    norm = _norm(text)
    if not norm:
        return True
    if any(re.fullmatch(p, norm) for p in _JUNK_PATTERNS):
        return True
    words = re.findall(r"[a-zA-Z0-9']+", norm)
    if len(words) < 4:
        return True
    meaningful = [w for w in words if len(w) >= 3]
    return len(meaningful) < 3


def clean_agency_name(name: str) -> str:
    raw = (name or "").strip()
    cleaned = re.sub(r"[^A-Za-z0-9&.,'\- ]+", " ", raw)
    cleaned = re.sub(r"[!?.]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_,.!?")

    if not cleaned:
        return SAFE_PLACEHOLDER
    if contains_profanity(cleaned) or contains_self_harm(cleaned):
        return SAFE_PLACEHOLDER

    words = re.findall(r"[A-Za-z0-9']+", cleaned)
    alpha_words = [w for w in words if re.search(r"[A-Za-z]", w)]
    if len(alpha_words) < 2:
        return SAFE_PLACEHOLDER

    lowered = _norm(cleaned)
    if any(re.fullmatch(p, lowered) for p in _JUNK_PATTERNS):
        return SAFE_PLACEHOLDER

    if len(cleaned) > 80:
        cleaned = cleaned[:80].rstrip(" -_,.!?")

    return cleaned or SAFE_PLACEHOLDER


def clean_bottleneck(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned or looks_like_junk(cleaned) or contains_profanity(cleaned) or contains_self_harm(cleaned):
        return "delayed follow-up after calls"
    if len(cleaned) > 120:
        cleaned = cleaned[:120].strip()
    return cleaned


def clean_website(text: str) -> str:
    cleaned = re.sub(r"\s+", "", (text or "").strip())
    if not cleaned:
        return ""
    if not re.search(r"[A-Za-z0-9-]+\.[A-Za-z]{2,}", cleaned):
        return ""
    return cleaned[:120]


def clean_calls_per_week(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    m = re.search(r"\d+", raw)
    if not m:
        return ""
    value = int(m.group(0))
    if value <= 0 or value > 200:
        return ""
    return str(value)


def _anchor_categories(text: str) -> set[str]:
    norm = _norm(text)
    categories: set[str] = set()

    # substantive business anchors only
    if re.search(r"lead quality|tracking|attribution|crm|landing page|campaign|ads|consult|proposal|scope|budget|retainer|booked consult|front desk|service line", norm):
        categories.add("problem_or_system")

    if re.search(r"\d+|percent|%|calls per week|leads|consults|locations|months|weeks|days|90-day|90 day", norm):
        categories.add("metric_or_quantity")

    if re.search(r"decision|timeline|deadline|commit|approve|budget", norm):
        categories.add("decision_or_timeline")

    # action / outcome anchors
    if re.search(r"want|need|goal|outcome|improve|increase|reduce|clarer 90-day|clearer 90-day|clear 90-day", norm):
        categories.add("desired_outcome")

    if re.search(r"next step|audit|strategy engagement|send|scope|proposal|follow up|follow-up|review|clarify", norm):
        categories.add("next_step")

    return categories


def validate_client_notes(raw_notes: str) -> ClientGateResult:
    norm = _norm(raw_notes)
    if contains_self_harm(norm):
        return ClientGateResult(status="unsafe", reason="submitted text contains self-harm or crisis language")

    word_count = len(re.findall(r"[a-zA-Z0-9']+", norm))
    categories = _anchor_categories(norm)

    substantive_categories = categories.intersection({"problem_or_system", "metric_or_quantity", "decision_or_timeline"})
    action_categories = categories.intersection({"desired_outcome", "next_step"})

    if word_count < 12:
        return ClientGateResult(status="needs_more_detail", reason="submitted notes are too short or too vague")

    if not substantive_categories:
        return ClientGateResult(status="needs_more_detail", reason="submitted notes are too vague for a reliable business handoff")

    if not action_categories:
        return ClientGateResult(status="needs_more_detail", reason="submitted notes are missing a clear outcome or next move")

    return ClientGateResult(status="ok", reason="usable business notes")
