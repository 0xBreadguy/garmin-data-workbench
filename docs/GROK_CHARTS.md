# Grok native interactive chart trial

Grok Bot can present a private native Page beside its conversation. This is an
assistant-authored view over the workbench's shared query results, separate from
the packaged [Muse HTML widget and MCP App](INTERACTIVE_CHARTS.md). The existing
HTML export is not a Grok Page adapter.

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

## Reusable request

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
