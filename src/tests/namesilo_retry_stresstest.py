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
DOMAINS = [f"rapidinnovationtest{i}.com" for i in range(1, 101)]

# Retry policy (tuned from experiments)
MAX_TOTAL_WAIT = 30.0       # seconds
INITIAL_BACKOFF = 5.0       # seconds
MAX_ATTEMPTS = 6            # hard safety cap
JITTER_RANGE = (0.0, 2.0)   # seconds


# ----------------------------------------
# Retry-aware NameSilo API call
# ----------------------------------------

async def call_namesilo_with_retry(
    client: httpx.AsyncClient,
    domain: str,
) -> dict:
    params = {
        "version": 1,
        "type": "json",
        "key": API_KEY,
        "domains": domain,
    }

    start_time = time.perf_counter()
    attempt = 0
    backoff = INITIAL_BACKOFF

    while True:
        attempt += 1
        elapsed = time.perf_counter() - start_time

        # Enforce total timeout BEFORE attempting again
        if elapsed >= MAX_TOTAL_WAIT:
            return {
                "domain": domain,
                "ok": False,
                "attempts": attempt - 1,
                "elapsed_sec": round(elapsed, 2),
                "error": "MAX_TOTAL_WAIT_EXCEEDED",
            }

        # Enforce max attempts
        if attempt > MAX_ATTEMPTS:
            return {
                "domain": domain,
                "ok": False,
                "attempts": attempt - 1,
                "elapsed_sec": round(elapsed, 2),
                "error": "MAX_ATTEMPTS_EXCEEDED",
            }

        try:
            r = await client.get(BASE_URL, params=params, timeout=10)

            content_type = r.headers.get("content-type", "").lower()
            body = r.text.strip()

            elapsed = time.perf_counter() - start_time

            # Enforce timeout EVEN IF SUCCESS
            if elapsed >= MAX_TOTAL_WAIT:
                return {
                    "domain": domain,
                    "ok": False,
                    "attempts": attempt,
                    "elapsed_sec": round(elapsed, 2),
                    "error": "TIMEOUT_EXCEEDED_BEFORE_SUCCESS",
                }

            if r.status_code == 200 and "json" in content_type and body:
                return {
                    "domain": domain,
                    "ok": True,
                    "attempts": attempt,
                    "elapsed_sec": round(elapsed, 2),
                }

            raise RuntimeError(f"status={r.status_code}, non-json")

        except Exception:
            # Retry with linear backoff + jitter
            jitter = random.uniform(*JITTER_RANGE)
            await asyncio.sleep(backoff + jitter)
            backoff += 1.0


# ----------------------------------------
# Concurrency burst
# ----------------------------------------

async def burst(round_no: int, concurrency: int):
    async with httpx.AsyncClient() as client:
        tasks = []

        for i in range(concurrency):
            domain = DOMAINS[i % len(DOMAINS)]
            tasks.append(call_namesilo_with_retry(client, domain))

        results = await asyncio.gather(*tasks)

    print(f"\n=== ROUND {round_no} | concurrency={concurrency} ===")

    success = 0
    for r in results:
        print(r)
        if r["ok"]:
            success += 1

    print(
        f"Summary: {success}/{len(results)} succeeded "
        f"(bounded retries, strict timeout)"
    )


# ----------------------------------------
# Main runner
# ----------------------------------------

async def main():
    rounds = 1
    concurrency = 50   # adjust as needed

    for i in range(1, rounds + 1):
        await burst(i, concurrency)
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
