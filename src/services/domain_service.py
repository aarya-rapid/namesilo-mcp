from __future__ import annotations
import re
from typing import List, Optional
import asyncio
import time

from ..services.namesilo_client import NameSiloClient
from ..constants.schema import AvailabilityOutput, PricingOutput

DEFAULT_TLDS = [
    ".com", ".ai", ".io", ".app",
    ".dev", ".co", ".net", ".org"
]

PREFIXES = ["", "get", "try"]
SUFFIXES = ["", "app", "ai"]


def _normalize_query(q: str) -> str:
    q = q.lower().strip()
    q = re.sub(r"[^a-z0-9 ]+", "", q)
    return q.replace(" ", "")


def _normalize_available(reply: dict) -> list[dict]:
    available = reply.get("available", [])

    # NameSilo edge cases
    if available is None:
        return []
    if isinstance(available, int):
        return []
    if isinstance(available, dict):
        return [available]
    if isinstance(available, list):
        return [d for d in available if isinstance(d, dict)]
    return []

def _closeness_score(domain: str, base: str) -> int:
    """
    Lower score = closer to query
    """
    name = domain.split(".", 1)[0]

    # exact base match
    if name == base:
        return 0

    score = abs(len(name) - len(base))

    # structural similarity
    if name.startswith(base):
        score += 1
    if name.endswith(base):
        score += 1

    # penalize known prefixes
    for pre in PREFIXES:
        if pre and name.startswith(pre):
            score += 2

    # penalize known suffixes
    for suf in SUFFIXES:
        if suf and name.endswith(suf):
            score += 2

    return score


class DomainService:
    def __init__(self, client: NameSiloClient | None = None) -> None:
        self._client = client or NameSiloClient()

    async def check_domain(self, domain: str) -> dict:
        return await self._client.check_availability(domain)
    
    async def check_domains(self, domains: list[str]) -> dict:
        return await self._client.check_availability_bulk(domains)

    def _build_domains(
        self,
        query: str,
        tlds: Optional[List[str]],
    ) -> List[str]:
        base = _normalize_query(query)
        if not base:
            return []

        tlds_final = tlds or DEFAULT_TLDS
        tlds_final = [
            t if t.startswith(".") else f".{t}"
            for t in tlds_final
        ]

        labels = {
            f"{pre}{base}{suf}"
            for pre in PREFIXES
            for suf in SUFFIXES
        }

        domains = [
            f"{label}{tld}"
            for label in labels
            for tld in tlds_final
        ]

        return sorted(set(domains))
    

    async def search_domains(
        self,
        query: str,
        tlds: Optional[List[str]] = None,
        max_results: int = 50,
    ) -> dict:
        domains = self._build_domains(query, tlds)

        if max_results and max_results > 0:
            domains = domains[:max_results]

        if not domains:
            return {
                "query": query,
                "domains_checked": 0,
                "raw": {},
            }

        raw = await self._client.check_availability_bulk(domains)
        reply = raw.get("reply", {})

        available = _normalize_available(reply)

        return {
            "query": query,
            "domains_checked": len(available),
            "raw": raw,
        }

    async def search_domains_under_budget(
        self,
        query: str,
        budget: float,
        count: int,
        tlds: Optional[List[str]] = None,
    ) -> dict:
        base_query = _normalize_query(query)

        # Reuse existing search logic (as in Namecheap MCP)
        base = await self.search_domains(query, tlds)
        raw = base["raw"]
        reply = raw.get("reply", {})

        available = _normalize_available(reply)

        priced = []

        for d in available:
            if not isinstance(d, dict):
                continue
            if "domain" not in d or "price" not in d:
                continue

            try:
                price = float(d["price"])
            except (TypeError, ValueError):
                continue

            priced.append({
                "domain": d["domain"],
                "price": price,
                "premium": bool(int(d.get("premium", 0))),
                "renew": d.get("renew"),
                "closeness": _closeness_score(d["domain"], base_query),
            })

        # If nothing priced, return early
        if not priced:
            return {
                "query": query,
                "budget": budget,
                "requested_count": count,
                "found_count": 0,
                "total_price": 0.0,
                "feasible": False,
                "min_possible_total": None,
                "selected_domains": [],
            }
        
        # # ---- MINIMUM POSSIBLE TOTAL (PRICE-ONLY, Namecheap semantics) ----
        # price_sorted = sorted(priced, key=lambda x: x["price"])
        # cheapest_n = price_sorted[:count]
        # min_possible_total = sum(item["price"] for item in cheapest_n)

        # ---- SORT: closeness first, then price ----
        priced.sort(key=lambda x: (x["price"], x["closeness"]))

        # ---- Minimum possible total (Namecheap logic) ----
        cheapest_n = priced[:count]
        min_possible_total = sum(item["price"] for item in cheapest_n)

        # ---- Best-effort selection under budget ----
        selected = []
        total = 0.0

        for item in priced:
            if len(selected) >= count:
                break

            if total + item["price"] > budget:
                continue  # skip expensive, try next

            selected.append(item)
            total += item["price"]

        feasible = len(selected) == count

        return {
            "query": query,
            "budget": float(budget),
            "requested_count": count,
            "found_count": len(selected),
            "total_price": total,
            "feasible": feasible,
            "min_possible_total": min_possible_total,
            "selected_domains": selected,
        }
    
    async def probe_concurrency_level(
        self,
        concurrency: int,
        domains: list[str],
    ) -> dict:
        async def _probe(domain: str) -> dict:
            start = time.perf_counter()
            try:
                await self._client.check_availability(domain)
                latency_ms = (time.perf_counter() - start) * 1000
                return {
                    "ok": True,
                    "latency_ms": latency_ms,
                }
            except Exception as e:
                latency_ms = (time.perf_counter() - start) * 1000
                return {
                    "ok": False,
                    "latency_ms": latency_ms,
                    "error": str(e),
                }

        tasks = []
        for i in range(concurrency):
            domain = domains[i % len(domains)]
            tasks.append(_probe(domain))

        results = await asyncio.gather(*tasks)

        successes = [r for r in results if r["ok"]]
        failures = [r for r in results if not r["ok"]]

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
