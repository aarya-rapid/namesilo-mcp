from __future__ import annotations

import httpx
import time
import asyncio
from typing import Optional, List

from ..helper.config import namesilo_settings


class NameSiloClient:
    def __init__(self) -> None:
        self.api_key = namesilo_settings.api_key
        self.base_url = namesilo_settings.base_url

    async def _request(self, endpoint: str, params: dict) -> dict:
        q = {
            "version": 1,
            "type": "json",
            "key": self.api_key,
        }
        q.update(params)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{self.base_url}{endpoint}", params=q)
            resp.raise_for_status()
            return resp.json()

    async def check_availability(self, domain: str) -> dict:
        return await self._request(
            "checkRegisterAvailability",
            {"domains": domain},
        )

    async def check_availability_bulk(self, domains: list[str]) -> dict:
        if not domains:
            return {}

        if len(domains) > 200:
            raise ValueError("Maximum 200 domains allowed")

        domain_list = ",".join(domains)
        return await self._request(
            "checkRegisterAvailability",
            {"domains": domain_list},
        )

    # Concurrency probe helper
    async def probe_concurrency_level(
        self,
        concurrency: int,
        domains: list[str],
    ) -> dict:
        tasks = []

        for i in range(concurrency):
            domain = domains[i % len(domains)]
            tasks.append(self._client.probe_availability(domain))

        results = await asyncio.gather(*tasks)

        successes = [r for r in results if r.get("ok")]
        failures = [r for r in results if not r.get("ok")]

        avg_latency = (
            sum(r["latency_ms"] for r in successes) / len(successes)
            if successes else None
        )

        return {
            "concurrency": concurrency,
            "success_rate": len(successes) / len(results),
            "avg_latency_ms": avg_latency,
            "failures": failures,
        }

