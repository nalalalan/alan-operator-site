from __future__ import annotations

from typing import Any, Dict, List

import httpx

from app.core.config import settings


class ApolloClient:
    base_url = "https://api.apollo.io/api/v1"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Api-Key": settings.apollo_api_key,
            "Cache-Control": "no-cache",
        }

    async def search_people(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/mixed_people/search",
                headers=self._headers(),
                json=payload,
            )
            print("APOLLO STATUS:", response.status_code)
            print("APOLLO BODY:", response.text)
            response.raise_for_status()
            return response.json()

    async def enrich_person(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/people/match",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def bulk_enrich_people(self, payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for payload in payloads:
            try:
                results.append(await self.enrich_person(payload))
            except Exception as exc:  # pragma: no cover
                results.append({"error": str(exc), "input": payload})
        return results