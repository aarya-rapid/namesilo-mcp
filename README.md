
# NameSilo MCP Server

This project provides a Model Context Protocol (MCP) server for interacting with the NameSilo domain API.  
It is designed to be **robust under strict rate limits**, prioritizing correctness and eventual success over raw throughput.

---

## Overview

The server exposes MCP tools for:

- Searching for available domains based on a query
- Selecting domains under a given budget
- Checking availability of a single domain
- Checking availability of multiple domains (bulk)

To run the server, run the following command from the project root:

```
uv run python src.server
```
The server can be connected to at `http://localhost:8000/mcp` via any standard tool such as Postman.


All tools are backed by the NameSilo API and are safe to use under NameSilo’s **1 request per second per IP** limitation.

---

## Rate-Limit Handling Strategy

NameSilo enforces a strict rate limit, which makes naïve concurrent requests unreliable.

To handle this, the system uses:

### Bounded Retry with Backoff

- Requests that fail due to rate limiting or transient errors are **retried**
- Each retry waits progressively longer before reattempting
- Retries are **bounded** by a maximum total wait time
- If the request does not succeed within that window, an error is returned

This approach trades latency for reliability and ensures **eventual success under load** without overwhelming the external API.

---

## Why This Design

- Prevents request storms
- Avoids hard failures under concurrency
- Produces predictable, tunable behavior
- Matches real production constraints of third-party APIs

The primary bottleneck is the external NameSilo API, not the MCP server itself.

---

## Testing

### Retry Stress Test

A retry stress test script is included to validate behavior under concurrent requests:

- Multiple domain availability checks are issued concurrently
- Calls that hit rate limits are retried with backoff
- The test measures time-to-success rather than raw throughput

To run it, run the following command from the project root:

```
uv run python src/tests/namesilo_retry_stresstest.py
```
This test demonstrates that the system remains stable and eventually succeeds even when concurrency exceeds the API’s rate limit.

> **Note:** MCP itself is not benchmarked for throughput.  
> Testing focuses on retry correctness and external API behavior.

---

## Environment Variables

```env
NAMESILO_API_KEY=your_api_key_here
NAMESILO_BASE_URL=https://www.namesilo.com/api/ (Optional)
````

