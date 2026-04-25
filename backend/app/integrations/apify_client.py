from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass
class ApifyRunResult:
    actor_id: str
    run_id: str
    dataset_id: str
    items: list[dict[str, Any]]


class ApifyClient:
    """Minimal Apify wrapper for the first buyer-acquisition loop.

    The client stays generic on purpose. Actor inputs vary a lot, so this only
    handles:
    - start actor run
    - wait for finish
    - fetch dataset items

    Higher-level normalization lives in the acquisition service.
    """

    base_url = "https://api.apify.com/v2"

    def __init__(self, api_token: str | None = None, timeout_seconds: int = 180) -> None:
        self.api_token = api_token or settings.apify_api_token
        self.timeout_seconds = timeout_seconds
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN is required for Apify operations")

    def _params(self, **extra: Any) -> dict[str, Any]:
        params = {"token": self.api_token}
        params.update(extra)
        return params

    def run_actor(self, actor_id: str, actor_input: dict[str, Any]) -> ApifyRunResult:
        if not actor_id.strip():
            raise ValueError("actor_id is required")
        with httpx.Client(timeout=self.timeout_seconds) as client:
            run_response = client.post(
                f"{self.base_url}/acts/{actor_id}/runs",
                params=self._params(waitForFinish=120),
                json=actor_input,
            )
            run_response.raise_for_status()
            run_payload = run_response.json().get("data") or {}
            run_id = str(run_payload.get("id", "")).strip()
            dataset_id = str(run_payload.get("defaultDatasetId", "")).strip()
            if not run_id or not dataset_id:
                raise RuntimeError(f"Apify run returned no ids for actor {actor_id}")
            items = self.get_dataset_items(dataset_id)
        return ApifyRunResult(actor_id=actor_id, run_id=run_id, dataset_id=dataset_id, items=items)

    def get_dataset_items(self, dataset_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = self._params(clean="1", format="json")
        if limit is not None:
            params["limit"] = limit
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(f"{self.base_url}/datasets/{dataset_id}/items", params=params)
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        raise RuntimeError(f"Unexpected dataset payload for {dataset_id}")
