import asyncio
import time
import httpx
import os
import random
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NAMESILO_API_KEY")
if not API_KEY:
    raise RuntimeError("NAMESILO_API_KEY not set")

BASE_URL = "https://www.namesilo.com/api/checkRegisterAvailability"

# Domains are just tokens for concurrency
DOMAINS = [
    f"rapidinnovationtest{i}.com" for i in range(1, 21)
]

MAX_ATTEMPTS = 6

# -------------------------------
# Retry-aware API call
# -------------------------------

async def call_namesilo_with_retry(
    client: httpx.AsyncClient,
    domain: str,
    *,
    max_total_wait: float = 30.0,
    initial_backoff: float = 5.0,
) -> dict:
    params = {
        "version": 1,
        "type": "json",
        "key": API_KEY,
        "domains": domain,
    }

    start_time = time.perf_counter()
    attempt = 0
    backoff = initial_backoff

    while True:
        attempt += 1
        try:
            r = await client.get(BASE_URL, params=params, timeout=10)

            content_type = r.headers.get("content-type", "").lower()
            body = r.text.strip()

            if r.status_code == 200 and "json" in content_type and body:
                return {
                    "domain": domain,
                    "ok": True,
                    "attempts": attempt,
                    "elapsed_sec": round(time.perf_counter() - start_time, 2),
                }

            raise RuntimeError(f"status={r.status_code}, non-json")

        except Exception as e:
            elapsed = time.perf_counter() - start_time

            # if elapsed >= max_total_wait:
            if attempt >= MAX_ATTEMPTS:
                return {
                    "domain": domain,
                    "ok": False,
                    "attempts": attempt,
                    "elapsed_sec": round(elapsed, 2),
                    "error": str(e),
                }

            # Linear backoff + small jitter
            jitter = random.uniform(0, 2.0)
            await asyncio.sleep(backoff + jitter)
            backoff += 1.0


# -------------------------------
# Concurrency burst
# -------------------------------

async def burst(round_no: int, concurrency: int):
    async with httpx.AsyncClient() as client:
        tasks = []

        for i in range(concurrency):
            domain = DOMAINS[i % len(DOMAINS)]
            tasks.append(
                call_namesilo_with_retry(client, domain)
            )

        results = await asyncio.gather(*tasks)

    print(f"\n=== ROUND {round_no} | concurrency={concurrency} ===")

    successes = 0
    for r in results:
        print(r)
        if r["ok"]:
            successes += 1

    print(
        f"Summary: {successes}/{len(results)} succeeded "
        f"(with retries where needed)"
    )


# -------------------------------
# Main runner
# -------------------------------

async def main(
    rounds: int = 1,
    concurrency: int = 50,
):
    for i in range(1, rounds + 1):
        await burst(i, concurrency)
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
