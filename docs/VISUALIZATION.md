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

### Experimental in-chat explorer

`explore_sleep_recovery(start, end)` returns the shared sleep report plus HRV, resting heart rate and daily Body Battery charge from one read snapshot. It references `ui://garmin-workbench/sleep-recovery-v1.html` with MIME type `text/html;profile=mcp-app`. An MCP Apps-capable host renders the packaged HTML inside the conversation. Ordinary MCP support alone does not establish interactive rendering support.

The component provides linked day inspection, full night details, date loading, explicit two-period comparisons and an optional “Ask about this night” action through the host. The comparison action calls the app-visible `compare_sleep_recovery` tool; definitions, covered means and change calculations remain in Python's shared query layer. All four sleep stages must reconcile before stacking; zeros, missing fields and failed retained values preserve their query meanings. Source wall times are not converted using today's profile zone.

The template contains no health observations. JavaScript, styles and D3 7.9.0 (ISC license included) ship in the wheel; it requests no network origins or device permissions. No server, CDN, browser navigation, live sync or scheduler is required. Results can still reach the selected AI provider and the host may retain rendered results as conversation content. Loading a date range rereads the archive, not Garmin. Default range is 14 days, maximum 90 inclusive dates. Comparisons accept two nonoverlapping periods of at most 90 days each.

This is an experimental local-trial feature, not a claim of compatibility with every assistant. Verify tool/resource discovery, the host's `ui/initialize` handshake, initial display, touch/keyboard inspection, in-frame tool calls and conversation follow-up separately. Hosts without MCP Apps retain the structured result and existing PNG/table fallback. Do not open an external page as a substitute for an in-chat request. See [the local trial guide](INTERACTIVE_CHARTS.md).

### PNG delivery

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
uv run --quiet --locked garmin-archive --data-dir ../garmin-demo sleep --from 2026-04-24 --to 2026-04-30
uv run --quiet --locked --extra charts garmin-archive --data-dir ../garmin-demo chart sleep --from 2026-04-24 --to 2026-04-30 --synthetic --output ../garmin-demo/synthetic-sleep-overview.png
```

The generator prints the inclusive date window, synthetic/manual state, a first question and full `sleep` / `chart sleep` commands using the selected archive's absolute path. This is offline generation, with no credentials, Garmin requests, sync, assistant registrations or recurring jobs configured by the command. Existing installations and jobs are left alone. Keep demo directories and PNGs outside Git; never point these examples at a personal archive.

The **v2, seed-42 default covers January 1–April 30, 2026 inclusive** (120 dates). Start with: **“How was sleep in the synthetic demo April 24–30, 2026? Show the sleep overview.”** This latest demo week has seven available sleep nights. The `sleep` query includes stages, score, need, naps and source times; `chart sleep` gives the overview with independent duration/need and score coverage. `sleep_duration` alone answers the narrower duration question. Read the installed `garmin-archive agent-guide` for presentation and interpretation guidance, plus [sleep report semantics](SLEEP.md).

Dates never move to today. A current “this week” outside the corpus has **no observations**, not zero sleep or live values. During explicitly mock-only use, state the requested actual dates and missing coverage. When the user's demo intent is clear, continue with the latest available fixture week, explicitly naming the substitution and its exact inclusive dates before answering. For the default corpus: “There are no demo observations for your current week; I'll demonstrate sleep with the synthetic April 24–30, 2026 week.” Select dates from the actual chosen corpus; April 24–30 is not a universal fallback for custom or empty demos. If intent is ambiguous, ask one concise choice: “Use the latest fixture week, or keep the requested period with no observations?” Never override explicit dates, imply the user's real current week was measured, or require credentials/live access to continue a mock-only demo. Preserve text-only requests and report gaps if no fixture observations are available. Query defaults still follow the current date, so use explicit `--from` and `--to` for demos. The fixed simulated fetch timestamp is **May 1, 2026 at 12:00 UTC**; archive generation time is recorded separately and does not make fixture observations current.

For a comparison, select existing fixture weeks such as **April 17–23 versus April 24–30, 2026**. Each query/chart accepts at most 90 inclusive dates. Sleep windows, awake time and stage proportions vary. Coverage failures differ by dataset; **March 12–18 is entirely unchecked**. Other cases include incomplete/inconsistent stages, duration without score, missing need, missing nap episode detail, and reordered/ambiguous Body Battery samples. January 16 has **synthetic zero** steps/distance. Synthetic activity summaries/details include GPS-present and GPS-absent examples; original FIT sensor fixtures live in the offline tests.

If you need later fixture dates, generate a **separate** longer corpus in another nonexistent directory outside the repository. `--days` accepts 1–366 dates, always starting January 1, 2026; it does not extend or rewrite an existing archive. For example, 320 dates end November 16, 2026:

```sh
uv run --quiet --locked python scripts/create_demo_archive.py ../garmin-demo-320 --days 320
uv run --quiet --locked garmin-archive --data-dir ../garmin-demo-320 sleep --from 2026-10-29 --to 2026-11-04
uv run --quiet --locked --extra charts garmin-archive --data-dir ../garmin-demo-320 chart sleep --from 2026-10-29 --to 2026-11-04 --output ../garmin-demo-320/synthetic-sleep-overview.png
```

These later dates are still invented, and retain the same fixed May 1 simulated fetch timestamp; they do not establish live freshness or a chronological collection history. Keep the default archive for its known-answer checks. Use `--profile metric-dst` for a separate metric/Europe-Berlin archive spanning the March DST change, `--empty` for a marked archive with no observations, or `--days 30` for a shorter example. Never combine profiles or demo and real data into one archive.

Synthetic sleep scores and stage proportions are generated by **independent formulas**. A low score alongside less deep sleep does not explain the score's cause; these fixtures cannot establish physiological causality. Body Battery intentionally repeats four readings (**25, 85, 40, 30**) with **60 charged / 50 drained**, apart from missingness and descriptor/ambiguity cases. It demonstrates observed-sample semantics and coverage, but cannot demonstrate changing weekly Body Battery trends. Available readings' extrema do not establish whole-day extrema. Neither corpus is a population or personal baseline.

`known-answers.json` records version, seed, expected scalar points, means, coverage and masked dates for selected ranges. Expectations come from scenario definitions, independently of production queries; tests pin the default corpus fingerprint. Changing expected answers requires intentional corpus-version review. The database records synthetic provenance, so copying it preserves the label; `SYNTHETIC.txt` is retained for legacy recognition.

Demo charts are labeled synthetic automatically, including legacy archives with `SYNTHETIC.txt`. The optional CLI `--synthetic` flag adds that label for other explicitly generated examples; it does not anonymize real data. Provenance reports fixture timestamps separately from archive generation time; an unmarked archive has unknown provenance.

## Keep images concise

The [README sleep preview](../assets/sleep-example.png) uses the default v2 demo (seed 42), April 24–30, 2026, and the `wide` layout. To refresh it, generate a new default demo outside the checkout, then render `garmin-archive --data-dir /absolute/new/demo chart sleep --from 2026-04-24 --to 2026-04-30 --layout wide --output /absolute/new/sleep-example.png`, replacing the demo and output paths. Inspect the image and synthetic label before replacing the documentation asset; keep the archive and metadata outside Git.

Lead with the measurements. Keep dates, units, denominators, legends and meaningful missing-data indicators on the image; omit repeated explanations and routine source or fetch-time paragraphs. Explain relevant freshness, estimates, limitations and interpretation in the accompanying response. For custom charts, apply the same approach and preserve the distinction between missing values and zero.

## Agent delivery

For an explicitly requested interactive view in Grok Bot, use its [native private Page route](GROK_CHARTS.md)
when available. Export the shared snapshot with `widget sleep-recovery --host grok`
to a new `.canvas.tsx` file, with `--handoff-dir` for bounded native create/edit
calls. Execute and verify the plan sequentially; the native writer does not
accept file references. Treat source verification and native compilation as
separate acceptance gates. The packaged HTML
widget is not interchangeable with a Grok Page. Verify visible interaction
separately from successful generation.

Create images in a private location and deliver them through the host's supported attachment/image interface. A local path alone may not be visible to the user. If rendering or delivery is unavailable, explain the limitation and provide a concise table from `trend`. Do not substitute image-generation models for plotting actual measurements.

Query results and images can reach the selected AI provider. Do not publish/upload them elsewhere without authorization. Avoid precise coordinates and routes by default; the chart command does not draw routes. Charting does not authorize syncing or reconfiguring services.

The optional [skill](../skills/garmin-visualization/SKILL.md) can be read directly by any agent with repository access. Discovery and installation differ by host; it is not automatically installed. MCP access alone does not imply filesystem access or image display support.
