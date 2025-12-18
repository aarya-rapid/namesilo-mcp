from __future__ import annotations

import httpx
import time
import asyncio
from typing import Optional, List
import random

from ..helper.config import namesilo_settings, retry_settings


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

        start_time = time.perf_counter()
        attempt = 0
        backoff = retry_settings.initial_backoff

        async with httpx.AsyncClient(timeout=20) as client:
            while True:
                attempt += 1
                elapsed = time.perf_counter() - start_time

                # Hard stop: total wait exceeded
                if elapsed >= retry_settings.max_total_wait:
                    raise RuntimeError(
                        "NameSilo request timed out after retries "
                        f"({round(elapsed, 2)}s)"
                    )

                # Hard stop: attempt limit
                if attempt > retry_settings.max_attempts:
                    raise RuntimeError(
                        "NameSilo request exceeded max retry attempts"
                    )

                try:
                    resp = await client.get(
                        f"{self.base_url}{endpoint}",
                        params=q,
                    )

                    content_type = resp.headers.get(
                        "content-type", ""
                    ).lower()

                    elapsed = time.perf_counter() - start_time

                    # Enforce timeout even on success
                    if elapsed >= retry_settings.max_total_wait:
                        raise RuntimeError(
                            "NameSilo request succeeded but exceeded time budget"
                        )

                    if resp.status_code == 200 and "json" in content_type:
                        return resp.json()

                    # Non-JSON or throttling page
                    raise RuntimeError(
                        f"Unexpected response: {resp.status_code}"
                    )

                except Exception:
                    # Retry with linear backoff + jitter
                    jitter = random.uniform(
                        retry_settings.jitter_min,
                        retry_settings.jitter_max,
                    )
                    await asyncio.sleep(backoff + jitter)
                    backoff += 1.0


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

