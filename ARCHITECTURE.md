# Architecture and performance

Reviewed November 1, 2026. The goal is reliable personal-data sync and responsive agent queries on one user's machine. First-use latency also includes Garmin request limits, scheduling, MCP client startup and model response time; database microbenchmarks measure only one part of that experience.

## Current choice

- **Python:** Garmin publishes the Personal API client and FIT SDK in Python. Keep the implementation close to supported libraries until profiling shows a CPU-bound workload that warrants another language or native component.
- **SQLite:** a local, transactional, single-file archive is appropriate for one collector and local read-only clients. Preserve source JSON and original activity ZIPs. Use keyed daily records, transactional FIT message replacement and indexed activity records. A separate database server adds operation and backup costs without a demonstrated benefit for this workload. [SQLite's guidance](https://www.sqlite.org/serverless.html) explains its local serverless design.
- **Read-only MCP:** use bounded tools and return coverage, freshness, source and units. The scheduler and Garmin credentials remain separate from the MCP process. Agent or model providers may receive returned data.
- **Offline-first:** a sync failure must not prevent queries over already-stored data; an unsuccessful refresh must not make stale values appear current. A successful response, including an empty one, is not proof that Garmin returned all history.

DuckDB is a strong candidate for future large analytical scans or joins, especially over columnar exports. It is not necessary for the current short, indexed queries, and introducing a second authoritative database would add consistency and deployment work. Consider it as an optional analytical reader after a representative benchmark shows a need. [DuckDB research](https://duckdb.org/pdf/SIGMOD2019-demo-duckdb.pdf) describes its embedded analytics design.

## Measurements

On the development Mac on November 1, 2026, a synthetic benchmark with 90 days of 10,000 heart-rate samples per day took a median of roughly **80 ms** for the original Python JSON parsing path. Selecting the scalar in SQLite reduced this to roughly **20 ms**. A single transaction inserting 100,000 synthetic FIT messages took about **0.29 seconds**. These are local, warm-cache measurements, not end-to-end latency guarantees or comparisons across languages and databases. Reproduce with `uv run python scripts/benchmark_archive.py`; it creates and deletes a temporary synthetic archive and needs no credentials.

A real seven-day sync succeeded with 35 health requests plus activity pagination and downloads. Network time and the deliberate per-request pause dominate that initial workflow. Endpoint window batching is promising, but must preserve per-day checkpoints, empty responses, partial failures, rate limits and source payloads; benchmark and test it before changing sync behavior. Garmin does not publish a fixed numeric Personal API quota in the terms reviewed.

## Concurrency and data safety

The current archive uses SQLite's default rollback journal with one sync protected by a process lock. Short MCP reads may briefly wait during commits. WAL can improve read/write concurrency, but changes backup behavior and requires same-host storage. SQLite documents a rare WAL-reset corruption race in versions through 3.51.2, fixed in 3.51.3 and selected backports; the development interpreter reports SQLite 3.50.4. Do not enable WAL on this installation without a patched SQLite, backup guidance and concurrent-reader tests. See [SQLite WAL documentation](https://www.sqlite.org/wal.html).

The current archive is intended for a local filesystem. Do not assume concurrent network-filesystem access is safe; [SQLite's network guidance](https://sqlite.org/useovernet.html) explains the tradeoffs. No durability settings have been weakened to improve benchmarks.

## Revisit when needed

- Compare query latency and memory on real large histories using privacy-preserving aggregate measurements; profile before choosing schema or language changes.
- Consider typed metric tables, SQL views, vectorized analytics or DuckDB if multi-year cross-metric and FIT scans are demonstrably slow.
- Evaluate a newer patched SQLite and WAL together with a coherent backup/restore command and production-like concurrency tests.
- Measure network request volume and validate API window behavior per endpoint before batching or parallelizing. Do not guess quotas or use rate-limit responses as a target.
- Validate every metric mapping against representative live payloads and the user's visible Garmin Connect values. A matching payload shape alone is not proof of semantic correctness.
