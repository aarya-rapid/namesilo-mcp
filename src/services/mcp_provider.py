from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from typing import List
import asyncio

from ..services.domain_service import DomainService
from ..constants.schema import AvailabilityOutput, PricingOutput


mcp = FastMCP("namesilo-domains", json_response=True)
_service = DomainService()


@mcp.tool()
async def search_domains(
    query: str,
    tlds: List[str] = [],
    max_results: int = 50,
) -> dict:
    """
    Search NameSilo for domains based on a query.
    """
    return await _service.search_domains(
        query=query,
        tlds=tlds or None,
        max_results=max_results,
    )


@mcp.tool()
async def search_domains_under_budget(
    query: str,
    budget: float,
    count: int,
    tlds: List[str] = [],
) -> dict:
    """
    Search domains and select domains under a given budget.
    """
    return await _service.search_domains_under_budget(
        query=query,
        budget=budget,
        count=count,
        tlds=tlds or None,
    )


@mcp.tool()
async def check_domain_availability(domain: str) -> dict:
    """
    Raw NameSilo availability response for a domain.
    """
    return await _service.check_domain(domain)


@mcp.tool()
async def check_domains_availability(domains: List[str]) -> dict:
    """
    Check availability for multiple domains using NameSilo.
    Accepts up to 200 domains.
    Returns raw NameSilo JSON response.
    """
    return await _service.check_domains(domains)


@mcp.tool()
async def probe_rate_limit(
    domains: List[str],
    max_concurrency: int = 5,
    samples_per_level: int = 3,
    latency_threshold_ms: int = 1200,
    cooldown_seconds: int = 2,
) -> dict:
    """
    Observational probe to determine safe concurrency limits
    for the NameSilo API. Stops at first instability.
    """

    results = []

    for concurrency in range(1, max_concurrency + 1):
        level_results = []

        for _ in range(samples_per_level):
            r = await _service.probe_concurrency_level(
                concurrency=concurrency,
                domains=domains,
            )
            level_results.append(r)
            await asyncio.sleep(0.5)

        avg_success = sum(
            r["success_rate"] for r in level_results
        ) / len(level_results)

        latencies = [
            r["avg_latency_ms"]
            for r in level_results
            if r["avg_latency_ms"] is not None
        ]
        avg_latency = sum(latencies) / len(latencies) if latencies else None

        results.append({
            "concurrency": concurrency,
            "avg_success_rate": avg_success,
            "avg_latency_ms": avg_latency,
        })

        # 🚨 Stop conditions
        if avg_success < 0.95:
            break
        if avg_latency and avg_latency > latency_threshold_ms:
            break

        await asyncio.sleep(cooldown_seconds)

    # ✅ LATENCY-AWARE RECOMMENDATION
    safe_concurrency = [
        r["concurrency"]
        for r in results
        if r["avg_success_rate"] >= 0.95
        and (
            r["avg_latency_ms"] is None
            or r["avg_latency_ms"] <= latency_threshold_ms
        )
    ]

    max_safe = max(safe_concurrency) if safe_concurrency else 1

    return {
        "api": "namesilo",
        "probe_type": "concurrency",
        "results": results,
        "recommendation": {
            "max_safe_concurrency": max_safe,
            "preferred_strategy": "bulk_requests",
            "note": (
                "Latency increases rapidly with concurrency. "
                "Bulk requests are recommended for reliable throughput."
            ),
        },
    }
