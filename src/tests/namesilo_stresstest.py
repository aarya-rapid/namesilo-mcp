import asyncio
import time
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NAMESILO_API_KEY", "")
BASE_URL = "https://www.namesilo.com/api/checkRegisterAvailability"

DOMAINS = [
    "rapidinnovationtest1.com",
    "rapidinnovationtest2.com",
    "rapidinnovationtest3.com",
    "rapidinnovationtest4.com",
    "rapidinnovationtest5.com",
]

async def call_namesilo(client, domain):
    params = {
        "version": 1,
        "type": "json",
        "key": API_KEY,
        "domains": domain,
    }
    start = time.perf_counter()

    try:
        r = await client.get(BASE_URL, params=params, timeout=10)
        latency = time.perf_counter() - start

        content_type = r.headers.get("content-type", "")
        text = r.text.strip()

        if "json" not in content_type.lower() or not text:
            return domain, r.status_code, latency, {
                "error": "NON_JSON_RESPONSE",
                "raw": text[:200]
            }

        return domain, r.status_code, latency, r.json()

    except Exception as e:
        return domain, "EXCEPTION", None, str(e)

async def burst(round_no):
    async with httpx.AsyncClient() as client:
        tasks = [call_namesilo(client, d) for d in DOMAINS]
        results = await asyncio.gather(*tasks)
        print(f"\n=== ROUND {round_no} ===")
        for r in results:
            print(r)

async def main(rounds=3):
    for i in range(1, rounds + 1):
        await burst(i)
        await asyncio.sleep(1)  # spacing between bursts

asyncio.run(main())
