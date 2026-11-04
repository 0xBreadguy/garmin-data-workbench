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

The script creates generated values for all supported numeric metrics, including sleep stages, score, stress, daily nap duration, sleep need and Body Battery for January 1–30, 2026. January 4 is unchecked, January 8 is empty, January 12 has a failed refresh over retained data, and January 17 lacks the metric. January 16 has genuine **synthetic zero** steps/distance. A `SYNTHETIC.txt` marker identifies the archive. There are no credentials, network calls, syncs, assistant registrations or schedules.

The same demo works with `chart sleep` for a multi-panel report.

Always pass `--synthetic` for demo charts. It places a compact visible label on the chart and identifies the source as a synthetic demo archive. The flag labels the input you supplied; it does not anonymize real data or detect whether values are synthetic.

## Keep images concise

Lead with the measurements. Keep dates, units, denominators, legends and meaningful missing-data indicators on the image; omit repeated explanations and routine source or fetch-time paragraphs. Explain relevant freshness, estimates, limitations and interpretation in the accompanying response. For custom charts, apply the same approach and preserve the distinction between missing values and zero.

## Agent delivery

Create images in a private location and deliver them through the host's supported attachment/image interface. A local path alone may not be visible to the user. If rendering or delivery is unavailable, explain the limitation and provide a concise table from `trend`. Do not substitute image-generation models for plotting actual measurements.

Query results and images can reach the selected AI provider. Do not publish/upload them elsewhere without authorization. Avoid precise coordinates and routes by default; the chart command does not draw routes. Charting does not authorize syncing or reconfiguring services.

The optional [skill](../skills/garmin-visualization/SKILL.md) can be read directly by any agent with repository access. Discovery and installation differ by host; it is not automatically installed. MCP access alone does not imply filesystem access or image display support.
