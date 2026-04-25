from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import json
import re
from typing import Any, Iterable
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.integrations.apify_client import ApifyClient

_EMAIL_RE = re.compile(r"\b([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<(script|style).*?>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WS_RE = re.compile(r"\s+")


def _clean_text(value: Any) -> str:
    return _WS_RE.sub(" ", str(value or "")).strip()


def _canonical_website(value: Any) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"https://{netloc}{path}" if path else f"https://{netloc}"


def _domain(value: Any) -> str:
    website = _canonical_website(value)
    if not website:
        return ""
    return urlparse(website).netloc.lower().removeprefix("www.")


def _extract_emails(*chunks: Any) -> list[str]:
    found: list[str] = []
    for chunk in chunks:
        for email in _EMAIL_RE.findall(str(chunk or "")):
            cleaned = email.lower().strip().rstrip(".,;:")
            if cleaned not in found:
                found.append(cleaned)
    return found


def _prefer_email(emails: list[str], domain: str) -> tuple[str, str]:
    if not emails:
        if domain:
            return f"hello@{domain}", "synthetic"
        return "", ""
    prefixes = ["founder@", "owner@", "hello@", "contact@", "info@", "sales@"]
    for prefix in prefixes:
        for email in emails:
            if email.startswith(prefix):
                return email, "public"
    for email in emails:
        if domain and email.endswith(f"@{domain}"):
            return email, "public"
    return emails[0], "public"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "prospect"


def _first_non_empty(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and _clean_text(value):
            return _clean_text(value)
    return ""


def _join_listish(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_clean_text(v) for v in value if _clean_text(v))
    return _clean_text(value)


def _extract_city_region(item: dict[str, Any]) -> tuple[str, str]:
    city = _first_non_empty(item, "city", "postalCity", "municipality")
    region = _first_non_empty(item, "state", "region", "stateCode")
    address = _first_non_empty(item, "address", "fullAddress", "street")
    if address and (not city or not region):
        parts = [p.strip() for p in address.split(",") if p.strip()]
        if len(parts) >= 2 and not city:
            city = parts[-2]
        if len(parts) >= 1 and not region:
            tail = parts[-1].split()[0]
            if len(tail) <= 3:
                region = tail
    return city, region


def _raw_summary(item: dict[str, Any]) -> str:
    chunks = [
        _first_non_empty(item, "description", "about", "title", "name"),
        _join_listish(item.get("categoryName") or item.get("category") or item.get("categories")),
        _join_listish(item.get("searchString") or item.get("source_query")),
        _join_listish(item.get("snippet") or item.get("reviewsSummary")),
    ]
    return _clean_text(" | ".join(chunk for chunk in chunks if chunk))


def _target_keywords() -> list[str]:
    return [token.strip().lower() for token in settings.acq_target_keywords.split(",") if token.strip()]


def _excluded_keywords() -> list[str]:
    return [token.strip().lower() for token in settings.acq_excluded_keywords.split(",") if token.strip()]


def _looks_like_target(summary: str, website_text: str = "") -> bool:
    hay = f"{summary} {website_text}".lower()
    target_hits = any(token in hay for token in _target_keywords())
    excluded_hits = any(token in hay for token in _excluded_keywords())
    return target_hits and not excluded_hits


@dataclass
class CollectedLeadBatch:
    source_records: list[dict[str, Any]]
    crawl_records: list[dict[str, Any]]
    maps_raw_count: int
    website_enriched_count: int
    kept_count: int
    dropped_count: int


def normalize_maps_item(item: dict[str, Any], source_query: str, source_name: str = "apify_google_maps") -> dict[str, Any] | None:
    company_name = _first_non_empty(item, "title", "name")
    website = _canonical_website(item.get("website") or item.get("site") or item.get("url") or item.get("web") or "")
    domain = _domain(website)
    if not company_name and not domain:
        return None

    city, region = _extract_city_region(item)
    summary = _raw_summary(item)
    public_emails = _extract_emails(
        item.get("email"),
        item.get("emails"),
        item.get("description"),
        item.get("about"),
        item.get("contact"),
    )
    chosen_email, contact_source = _prefer_email(public_emails, domain)
    contact_name = _first_non_empty(item, "owner", "contactName")
    contact_role = _first_non_empty(item, "contactRole", "role") or "Founder"
    external_basis = "|".join([
        source_name,
        source_query,
        company_name.lower(),
        chosen_email or domain or website,
    ])
    external_id = _slugify(external_basis)[:255]

    record = {
        "external_id": external_id,
        "company_name": company_name,
        "website": website,
        "domain": domain,
        "city": city,
        "region": region,
        "phone": _first_non_empty(item, "phone", "phoneNumber", "primaryPhone"),
        "source_name": source_name,
        "source_query": source_query,
        "contact_name": contact_name,
        "contact_email": chosen_email,
        "contact_role": contact_role,
        "contact_source": contact_source or source_name,
        "website_text": summary,
        "personalization_line": "",
        "notes": _clean_text(json.dumps({"maps_item": item}, ensure_ascii=False)[:1200]),
        "payload_json": json.dumps(item, ensure_ascii=False),
    }
    return record


def _strip_html_to_text(html: str) -> str:
    html = _SCRIPT_RE.sub(" ", html)
    html = _TAG_RE.sub(" ", html)
    html = unescape(html)
    return _clean_text(html)


def _fetch_website_text_http(url: str, timeout_seconds: int = 20) -> str:
    if not url:
        return ""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AO Labs Buyer Acquisition Collector/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout_seconds, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type.lower():
                return ""
            return _strip_html_to_text(response.text)[:8000]
    except Exception:
        return ""


def _crawl_with_apify(start_urls: list[str]) -> dict[str, str]:
    actor_id = settings.apify_website_crawler_actor_id.strip()
    if not actor_id or not start_urls:
        return {}
    actor_input = {
        "startUrls": [{"url": url} for url in start_urls],
        "maxCrawlPages": max(1, min(len(start_urls), 50)),
        "maxCrawlDepth": 0,
        "proxyConfiguration": {"useApifyProxy": True},
    }
    client = ApifyClient()
    result = client.run_actor(actor_id, actor_input)
    mapping: dict[str, str] = {}
    for item in result.items:
        page_url = _canonical_website(item.get("url") or item.get("requestUrl") or item.get("loadedUrl") or "")
        text = _clean_text(item.get("text") or item.get("markdown") or item.get("title") or "")
        html = item.get("html") or ""
        if html and not text:
            text = _strip_html_to_text(str(html))
        if page_url and text:
            mapping[page_url] = text[:8000]
    return mapping


def build_maps_actor_input(queries: list[str], per_search_limit: int) -> dict[str, Any]:
    return {
        "searchStringsArray": queries,
        "maxCrawledPlacesPerSearch": per_search_limit,
        "language": "en",
    }


def collect_real_batch(
    query: str,
    locations: list[str],
    total_limit: int,
    per_search_limit: int = 20,
    maps_actor_input: dict[str, Any] | None = None,
    use_website_crawler: bool = True,
) -> CollectedLeadBatch:
    maps_actor_id = settings.apify_google_maps_actor_id.strip()
    if not maps_actor_id:
        raise ValueError("APIFY_GOOGLE_MAPS_ACTOR_ID is required")

    search_strings = [f"{query} {location}".strip() for location in locations if _clean_text(location)] or [query]
    actor_input = maps_actor_input or build_maps_actor_input(search_strings, per_search_limit)
    client = ApifyClient()
    maps_run = client.run_actor(maps_actor_id, actor_input)

    raw_records: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for item in maps_run.items:
        source_query = _first_non_empty(item, "searchString") or query
        normalized = normalize_maps_item(item, source_query=source_query)
        if not normalized:
            continue
        key = normalized.get("contact_email") or normalized.get("domain") or normalized.get("website") or normalized.get("company_name")
        if key in seen_keys:
            continue
        seen_keys.add(key)
        raw_records.append(normalized)

    websites = [record["website"] for record in raw_records if record.get("website")]
    website_text_map: dict[str, str] = {}
    if use_website_crawler and settings.apify_website_crawler_actor_id.strip():
        try:
            website_text_map = _crawl_with_apify(websites)
        except Exception:
            website_text_map = {}

    crawl_records: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    dropped_count = 0
    for record in raw_records:
        website = record.get("website", "")
        website_text = website_text_map.get(website, "")
        if not website_text and website:
            website_text = _fetch_website_text_http(website)
        if website_text:
            record["website_text"] = _clean_text(f"{record.get('website_text', '')} {website_text}")[:8000]
            crawl_records.append(
                {
                    "external_id": record["external_id"],
                    "url": website,
                    "website_text": website_text[:8000],
                    "personalization_line": "",
                }
            )
        if not _looks_like_target(record.get("website_text", ""), record.get("notes", "")):
            dropped_count += 1
            continue
        kept.append(record)

    if total_limit > 0:
        kept = kept[:total_limit]
        crawl_records = [row for row in crawl_records if row.get("external_id") in {record["external_id"] for record in kept}]

    return CollectedLeadBatch(
        source_records=kept,
        crawl_records=crawl_records,
        maps_raw_count=len(maps_run.items),
        website_enriched_count=len(crawl_records),
        kept_count=len(kept),
        dropped_count=dropped_count,
    )
