# Architecture

One user's archive, one collector, multiple query clients. Reviewed November 1, 2026.

```text
Garmin Personal API -> sync -> SQLite + source JSON + original ZIPs
                               |-> CLI / CSV / SQL / notebooks
                               `-> read-only MCP data tools -> chosen AI client
```

`configure_sync` is separate from data queries: it changes the local macOS schedule, without making an immediate Garmin request.

## Choices

| Layer | Choice and reason |
| --- | --- |
| Collection | Python, close to Garmin's official Personal API client and FIT SDK |
| Storage | SQLite: transactional, portable, no database service to operate |
| Queries | Shared definitions in `queries.py` for CLI and MCP |
| Agent access | Bounded results with units, dates, freshness and coverage; no coordinates in default samples |

Keep collection separate from queries. Stored data remains queryable when Garmin is unavailable; failed refreshes must not make old values look current. Preserve source units, timestamp meaning and originals. Null, empty, failed and zero are distinct. Returned tool data may reach the AI provider.

[Schema and SQL](docs/USAGE.md#sql-and-source-data) · [Sync behavior](docs/USAGE.md#sync-and-recovery)

## Concurrency and durability

SQLite uses its default rollback journal. A process lock serializes syncs per archive; short reads can briefly wait for commits. Use a local filesystem, not assumed-safe concurrent network storage. See [SQLite's network guidance](https://sqlite.org/useovernet.html).

Don't enable WAL without patched SQLite, backup guidance and concurrent-reader tests. At review, the development interpreter used SQLite 3.50.4; SQLite documents a WAL-reset race through 3.51.2, fixed in 3.51.3 and selected backports. See [WAL documentation](https://www.sqlite.org/wal.html). Don't weaken durability for benchmark gains.

## Measurements and next decisions

On the development Mac, a warm-cache synthetic 90-day query with 10,000 heart-rate samples/day took about 80 ms parsing JSON in Python and 20 ms selecting scalars in SQLite. Inserting 100,000 FIT messages in one transaction took about 0.29 s. Reproduce with:

```sh
uv run python scripts/benchmark_archive.py
```

These measure local database work. A live seven-day sync made 35 health calls plus activity pagination/downloads; requests and pacing dominated initial collection.

Profile representative workloads before adding typed tables, DuckDB, another language or API batching. Any batching must preserve per-day checkpoints, empty responses, partial failures and rate-limit behavior. Validate metric meaning against Connect before expanding analysis. Preserve overlapping recordings and source timestamps; don't silently merge them or assume the current profile time zone applies to historical activities.
