# Grok native interactive explorer

Grok Bot can present a private native Page beside its conversation. This is a
view over the workbench's shared query results, separate from the
[Muse HTML widget and MCP App](INTERACTIVE_CHARTS.md). The workbench now packages
a native TSX renderer so the layout and behavior can stay consistent between
requests. The HTML export is not interchangeable with a Grok Page.

**Status:** the packaged source passes local export and interaction tests. Native
delivery of that exact source remains experimental: the observed writer accepts
inline source but has no supported file-to-tool binding. The earlier,
assistant-authored Page was visibly interactive; that does not establish native
acceptance of this packaged renderer.
See the [packaged trial report](acceptance/2026-11-05-grok-packaged-explorer.md)
for the source-transfer failure and the separately passing local checks.

## Packaged framework

```sh
garmin-archive --data-dir /absolute/existing/archive widget sleep-recovery \
  --host grok --from 2026-04-17 --to 2026-04-30 \
  --output /absolute/new/recovery.canvas.tsx
```

Use dates actually covered by the selected archive. The command reads 1–90
inclusive dates (default 14) and exclusively creates a private file. It embeds
the same coherent snapshot and midpoint comparison used by Muse. The two halves
retain independent metric coverage; one date has no comparison. No Garmin
credentials, sync, Node runtime, CDN, chart extra or network listener is needed.
The workbench applies a 1 MiB export guardrail; this is not a documented Grok
host limit. The file contains health observations when the archive is personal.

`ui/recovery.canvas.tsx` owns presentation: a linked selected date across five
chart lanes, Trends / Night detail / Compare, Last 7, pointer and keyboard
selection, light/dark colors, explicit unavailable states and segmented gaps.
The four sleep stages exclude awake. All period averages and differences come
from shared Python queries. The renderer cannot query, sync or send a message.
Its view state is held only in local React state, with no persistence bridge;
actual native reopening behavior remains untested. Request a new snapshot to
refresh data.

### Native delivery boundary

The observed contract is `WriteCanvas({contents: source, title: "Sleep & recovery"})`.
`contents` must be the complete source string. A file path or `$file:` reference
is rejected. A reported update uses the same call with `canvas_id`; `ReadCanvas`
can read a Page by ID or URL. Confirm the current tool contract before use.

In the tested session, file tools could read/hash the attachment and Shell could
read it on disk, but neither could bind those bytes directly into `WriteCanvas`.
An exported file is therefore not yet the one-step native handoff available in
Muse. Do not silently replace it with a newly invented chart and call that the
packaged renderer. If the model copies source inline, compare saved source
against the export and report any normalization or differences. Check actual
compilation, owner-only access and visible interaction separately.

A follow-up two-day synthetic export (48,146 source bytes) was submitted through
the normal inline path once. Grok reported truncated tool-argument JSON and an
unterminated string at position 20,379. No Page or compiler result was produced.
This is an observed failure of that attempt, not a documented universal size
limit. Compact transport could be explored, but reducing bytes alone does not
establish faithful transfer or native rendering.

The dependable integration needs a supported file reference/upload on the native
writer, or supported orchestration that passes file contents into its argument.
This boundary belongs to the Grok host integration. The query/export/rendering
framework belongs to Garmin Workbench; no Crumb harness change is required to
generate it. A local harness change cannot supply an unavailable Grok API.

### Next design and copy pass

Keep this framework while refining the surface: establish a consistent spacing
and type scale; strengthen the selected-night hierarchy and shared cursor;
balance chart density against night details; shorten repeated status/source copy;
and tune stage contrast, focus treatments and touch targets in both themes.
`palette`, `Lane`, `StageDetail`, `ComparisonView` and the formatters isolate these
changes from query semantics. Compare screenshots against Muse's actual delivered
widget, then repeat native keyboard, touch, reopen and narrow-screen checks.
Native compilation and exact-source delivery come before claiming that polish
is consistently available in Grok.

## What has been observed

In the native Mac app's Health Buddy conversation, a returned Page card opened
beside chat and its counter visibly changed from **0 to 1** when clicked. This
establishes native rendering and one interaction. The subsequent Garmin Page
also displayed and responded to chart clicks, dragging, arrow keys and night
navigation. A repaired stage breakdown and UTC source-time labels were directly
checked; the Share menu showed **Only you**. See the [trial report](acceptance/2026-11-05-grok-interactive-charts.md)
for initial defects and evidence limits. Physical touch, mobile delivery,
restart persistence and cross-device state remain untested.

Grok reported `WriteCanvas`, `EditCanvas`, `ReadCanvas` and `ListCanvases` tools
for private Pages. Its reported authoring contract is a self-contained
`.canvas.tsx` file importing only `grok/canvas`, with embedded data, React state,
and native chart components or inline SVG. Raw HTML, D3, iframes and `fetch` are
not this route. A numeric payload-size limit was not documented in the reported
tool guidance; keep the snapshot small and inspect actual tool errors instead
of borrowing Muse's 1 MB limit.

Grok's own browser encountered a Cursor sign-in redirect during inspection.
That did not prevent the Page from displaying and responding in the native app.
Record browser inspection and actual native delivery separately; a browser
failure alone does not establish missing chart delivery.

## Reuse an existing archive

Use the authorized archive and installed executable on Grok's actual execution
host. The Mac chat surface does not establish where its commands or archive
run. Read `agent-guide` and `brand`, then query an explicit, bounded date range:

- `sleep --from YYYY-MM-DD --to YYYY-MM-DD` supplies stages, duration, score,
  need and source times together.
- `trend overnight_hrv`, `trend resting_heart_rate`, and optionally
  `trend body_battery_charged` accept the same date flags.
- If comparing periods, use `compare` with explicit earlier and later dates;
  preserve each metric's independent coverage and shared calculated result.

Pass the same global `--data-dir` archive argument to each command. Query at most
90 inclusive dates, initially 7–14. Read-only queries need no Garmin credentials
or sync. Do not reinstall, schedule, publish, or share the Page to produce the
view. For a synthetic demo, use its actual fixture dates and synthetic label;
do not move observations to the current week. Real embedded observations remain
health data even when displayed in a private Page.

Use each sleep night's `stages_complete` flag. The four sleep stages are deep,
light, REM and unclassified; awake is separate and excluded from total sleep.
Keep raw seconds until display formatting. Do not test completeness by summing
rounded labels or including awake. Preserve the query's `timing` semantics:
source-local wall times without offsets must not acquire today's profile zone
or a guessed fixed UTC offset. Prefer exact UTC fetch timestamps for freshness.

Preserve every requested calendar date when preparing chart series. Filtering
out null observations can connect a line across an unobserved day. Use the host's
documented gap value or separate contiguous segments, independently per metric.
Verify a three-day case with values on either side of a missing middle date;
data-projection assertions alone do not establish visible gap rendering.

## Assistant-authored prototype fallback

This request describes the earlier prototype route, not acceptance of the
packaged export. Keep that distinction visible if the packaged handoff is blocked.

> Use this conversation's existing Garmin archive read-only to create a private
> native interactive Page for [inclusive start–end dates]. Use bounded `sleep`
> and `trend` results from the installed workbench, with its brand settings.
> Build a self-contained `.canvas.tsx` using only the supported `grok/canvas`
> imports, embedded observations, React state, and native charts or inline SVG.
> Present its Page card here. Do not sync, change scheduling, publish, or enable
> public sharing. Keep one selected date linked across sleep, HRV, resting heart
> rate and score, with click/tap selection and keyboard-accessible controls.
> Include a selected-night detail view and a visible date/units/coverage line.
> Preserve nulls and independent missing or failed fields; never fill them with
> zero or invent stages. Retain archive provenance and fetch freshness. Sleep
> duration and stages are seconds; sleep need is minutes. Attribute score,
> stages and need to Garmin estimates. If adding comparisons, use the shared
> `compare` results and each metric's denominator. Treat the Page as a fixed
> snapshot; query again explicitly for another date range. Verify the actual
> native Page rather than inferring delivery from a browser preview.

Before claiming chart acceptance, inspect the returned Page, select another
date, check linked values against the query results, exercise keyboard controls,
and inspect a missing-data case. Test touch, reopening and mobile separately.
A generated source file, tool-success receipt or clickable card alone does not
prove these behaviors.
