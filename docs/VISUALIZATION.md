# Visualizing your archive

Follow the canonical [presentation policy](../src/garmin_archive/agent_guide.md#present-and-visualize), also available through installed `agent-guide`: normally deliver a chart for multi-day trends, sleep and Body Battery, followed by a short interpretation and coverage/freshness line. The policy enumerates text-only, single-day, sparse-data and unavailable-delivery exceptions. Charts read the existing archive without syncing or requiring Garmin credentials.

## Render a chart

Install the optional chart dependencies from the repository:

```sh
uv tool install --from '.[charts]' garmin-data-workbench
```

For development, use `uv sync --locked --extra charts` and prefix commands with `uv run --quiet --locked --extra charts`. Quiet mode keeps uv's setup messages out of machine-parsed stderr; launcher/setup failures can still be non-JSON. See the [automation output contract](USAGE.md#output-and-automation).

```sh
garmin-archive --data-dir /absolute/private/archive chart sleep_duration --from 2026-01-01 --to 2026-01-30 --output sleep.png
```

The global `--data-dir` option goes **before** `chart`. Omit it to use the default archive. Output must be a new PNG; existing files are never overwritten. The default `--layout chat` is sized for conversations and phones; `--layout wide` gives a wider report figure. Both include the same data, branding and coverage details.

The [shared metrics](USAGE.md#summaries-units-and-dates) and 90-day limit apply. Dates default to the same seven-day window as `trend`. Charts divide sleep/stage/nap seconds by 3,600 and sleep-need minutes by 60 to display **hours**, with the summary average in hours/minutes; structured `trend` output retains **seconds** without changing stored data. Distance follows saved profile preferences; other units come from the query. Averages use available values only and state their denominator.

Steps and distance use bars starting at zero. Sleep, resting heart rate and HRV use unsmoothed lines. Line scales can focus on the observed range; read the labeled axis. Zero stays a value. Unavailable days are gaps, with a dated coverage strip and notes distinguishing failed, empty, unchecked and unreturned values. Retained data from a failed refresh stays masked. Fetch times are available in query results; explain freshness in the accompanying response when relevant. Sparse data does not establish a trend, and movement up or down is not inherently good or bad.

For a detailed sleep question, use `chart sleep --from 2026-01-01 --to 2026-01-30 --output sleep-overview.png`. It combines total duration and complete stage bars with a separate score panel. See [sleep report semantics](SLEEP.md); stages and scores are estimates, and incomplete breakdowns are never filled with zeros. Scalar score/stress charts use a 0–100 axis.

Run the installed `agent-guide` for the same presentation and interpretation rules in shell-only or MCP workflows.

Body Battery scalar charts follow the [observed-reading definitions](BODY_BATTERY.md). Level charts use a fixed 0–100 scale; charged/drained amounts use bars starting at zero. The latest observed sample is not a live current value. `chart sleep` also shows Garmin's adjusted need as a distinct dotted line; need is an estimate, not a prescribed target.

## MCP chart delivery

The read-only `chart` tool accepts `metric` (`sleep` or any trend metric), `start`, `end` and `layout` (`chat`/`wide`). Dates are inclusive and bounded to 90 days. It returns a PNG as MCP image content plus identical JSON in structured content and a text block: contract version, title/metric, dates, rendered units, layout, per-series denominators/status counts, available-value fetch timestamps, synthetic provenance, caption/alt text and explanations. Sleep duration, score and need retain independent coverage.

Rendering happens in memory; the tool accepts no filesystem output path and creates no chart file. Images are bounded to 1600 × 4096 pixels and 4 MiB. The CLI remains the file-export fallback. Missing plotting dependencies return `dependency_unavailable` with no image; invalid metrics, dates/layouts or archive errors are tool failures. Use query values for a small table if delivery is unavailable. A returned image does not prove a host displayed it to the person; run the host acceptance check.

`brand` works without chart dependencies or an archive. It returns settings and three `garmin-brand://assets/…` URIs, readable as correctly typed PNG/SVG MCP resources, so a remote client need not resolve local logo paths.

## Use the workbench brand

```sh
garmin-archive brand
```

This emits JSON without opening an archive or requiring chart dependencies: exact logo colors, font, chart types, layout rules and local paths to the SVG logo and square SVG/PNG icon. The assets ship inside the installed package. Repository originals remain in [assets/](../assets/); the shared settings live in [brand.json](../src/garmin_archive/brand.json).

Use **blue `#0863E8` for the main series across all metrics** and **navy `#0B2855` for titles and summary values**, matching the approved conversation-bubble logo. White and the supplied muted colors support the layout. Keep the logo small in the footer, preserve its aspect ratio and colors, and leave room around it. Use supplied assets rather than recreating the mark. For comparisons, add line styles, markers or direct labels so color is not the only distinction.

The built-in renderer applies this automatically. An agent using its own plotting or presentation tools should read `brand`, use the returned assets, and follow the same conventions. DejaVu Sans ships with Matplotlib; if a different host cannot use it, choose a readable sans-serif fallback and retain the hierarchy. Instructions guide custom renderers; they cannot force a host to support particular assets or image delivery.

## Try generated demo data

From a repository checkout, create a **new** directory outside the repo. The script refuses any existing destination, including an empty directory:

```sh
uv run --quiet --locked python scripts/create_demo_archive.py ../garmin-demo
uv run --quiet --locked --extra charts garmin-archive --data-dir ../garmin-demo chart sleep_duration --from 2026-01-01 --to 2026-01-30 --synthetic --output ../synthetic-sleep.png
```

The v2 default corpus has 120 days starting January 1, 2026, with a fixed seed and simulated collection timestamps. Sleep windows, awake time and stage proportions vary. Coverage failures differ by dataset; March 12–18 is entirely unchecked. Later cases include incomplete/inconsistent stages, duration without score, missing need, missing nap episode detail, and reordered/ambiguous Body Battery samples. January 16 has **synthetic zero** steps/distance. Synthetic activity summaries/details include GPS-present and GPS-absent examples; original FIT sensor fixtures live in the offline tests.

Use `--profile metric-dst` for a separate metric/Europe-Berlin archive spanning the March DST change, `--empty` for an empty archive, or `--days 30` for a shorter example. Never combine profiles into one user's archive. `known-answers.json` records version, seed, expected scalar points, means, coverage and masked dates for selected ranges. Expectations come from scenario definitions, independently of production queries; tests pin the default corpus fingerprint. Changing expected answers requires intentional corpus-version review. The corpus is illustrative, not a population or personal baseline.

The database records synthetic provenance, so copying it preserves the label. `SYNTHETIC.txt` is retained for legacy recognition. There are no credentials, network calls, assistant registrations or schedules.

The same demo works with `chart sleep` for a multi-panel report.

Demo charts are labeled synthetic automatically, including legacy archives with `SYNTHETIC.txt`. The optional CLI `--synthetic` flag adds that label for other explicitly generated examples; it does not anonymize real data. Provenance reports fixture timestamps separately from archive generation time; an unmarked archive has unknown provenance.

## Keep images concise

Lead with the measurements. Keep dates, units, denominators, legends and meaningful missing-data indicators on the image; omit repeated explanations and routine source or fetch-time paragraphs. Explain relevant freshness, estimates, limitations and interpretation in the accompanying response. For custom charts, apply the same approach and preserve the distinction between missing values and zero.

## Agent delivery

Create images in a private location and deliver them through the host's supported attachment/image interface. A local path alone may not be visible to the user. If rendering or delivery is unavailable, explain the limitation and provide a concise table from `trend`. Do not substitute image-generation models for plotting actual measurements.

Query results and images can reach the selected AI provider. Do not publish/upload them elsewhere without authorization. Avoid precise coordinates and routes by default; the chart command does not draw routes. Charting does not authorize syncing or reconfiguring services.

The optional [skill](../skills/garmin-visualization/SKILL.md) can be read directly by any agent with repository access. Discovery and installation differ by host; it is not automatically installed. MCP access alone does not imply filesystem access or image display support.
