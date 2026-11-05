# Architecture

One user's archive, one collector, multiple query clients. Reviewed November 3, 2026.

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

The MVP uses only Garmin's official Personal API. [The coverage contract](docs/API_COVERAGE.md) covers its 26 documented endpoints. Daily responses stay in `daily_data`; current profile/zones and activity details/workouts use `source_snapshots` with independent refresh status and retained JSON. This additive table is compatible with schema version 1; read-only queries never create it, and older archives report uncollected sources as `not_checked`. The next writer creates it without rewriting existing rows. No durability settings change.

`sources.py` owns collection routes; the packaged response contract owns schema discovery. `api_data.py` provides shared bounded native field access and scalar series. Native access preserves source values, flags and sentinels; interpreted daily metrics in `queries.py` apply documented mappings and validity rules. Every field is accessible without requiring a separate tool or invented daily aggregate. Coordinates are omitted from default MCP responses and require an explicit native-source opt-in.

`comparisons.py` compares existing metric trends using two explicit periods and available-day denominators. `workouts.py` owns shared activity filtering and daily/weekly volume totals from search summaries. Failed activity refreshes mask measurements; stored multisport parent IDs prevent counting parents alongside their children. These are read-only interpretations over the existing schema, with no collector, scheduler or dependency additions. Provider-specific automation remains with the assistant; native schedule configuration is not proof of unattended execution.

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

## Archive provenance and chart delivery

The additive `archive_provenance` table stores explicitly generated corpus version, seed and creation time. Unmarked archives remain unknown; readers recognize legacy `SYNTHETIC.txt` markers without migration or filesystem timestamp inference. Copying a marked database retains provenance. No durability settings change.

CLI and MCP share query definitions, deterministic chart metadata and an in-memory PNG renderer. MCP returns image content and structured metadata without filesystem output; CLI exports use exclusive private creation. Brand resources are fixed packaged PNG/SVG assets. Host image display remains a separate acceptance check.
