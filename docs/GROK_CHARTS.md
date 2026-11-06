# Grok native interactive explorer

Grok Bot can present a private native Page beside its conversation. This is a
view over the workbench's shared query results, separate from the
[Muse HTML widget and MCP App](INTERACTIVE_CHARTS.md). The workbench now packages
a native TSX renderer so the layout and behavior can stay consistent between
requests. The HTML export is not interchangeable with a Grok Page.

**Status:** bounded native edits delivered the packaged explorer in the Mac Grok
Bot app. The shortened source-verification sequence passed, and linked selection,
keyboard navigation, Last 7, night details, comparisons and independent missing
observations responded visibly. See the [bounded-delivery trial](acceptance/2026-11-05-grok-staged-delivery.md).
This is separate from the earlier
[failed one-call transfer](acceptance/2026-11-05-grok-packaged-explorer.md).
Native tool receipts, source verification and actual interaction remain distinct
acceptance checks; a local export alone proves none of them.

## Packaged framework

```sh
garmin-archive --data-dir /absolute/existing/archive widget sleep-recovery \
  --host grok --from 2026-04-17 --to 2026-04-30 \
  --output /absolute/new/recovery.canvas.tsx \
  --handoff-dir /absolute/new/grok-handoff
```

Use dates actually covered by the selected archive. The command reads 1–90
inclusive dates (default 14) and exclusively creates a private file. It embeds
a versioned compact projection of the same coherent snapshot and midpoint
comparison used by Muse. It retains every field consumed by this renderer,
including nulls, statuses, source times, stages and independent coverage. The two halves
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

### Bounded native delivery

Use the handoff directory's `plan.json`. It contains the expected source identity,
ordered tool calls and separate source verification calls. Each call also has a
small JSON argument file. The complete manifest is written last; a directory
without `plan.json` is incomplete. The directory/files are private on POSIX and
existing paths are never overwritten. If handoff creation fails after export,
the CLI names the saved source so it can be recovered without regenerating data.

The agent performs the calls through Grok's supported tools:

1. `WriteCanvas({contents, title})` creates a new private Page with a temporary
   placeholder. Bind the returned `canvas_id` in subsequent calls.
2. `EditCanvas({canvas_id, old_string, new_string, replace_all: false})` appends
   complete declarations at one unique anchor. The final edit activates the
   packaged App. Do not combine the calls into one large source submission.
3. Prefer a machine comparison of the actual `ReadCanvas({canvas_id})` response.
   The observed native dynamic-tool bridge accepts top-level `write_to_file: true`
   beside `namespace`, `toolName` and `arguments`; this is **not** a ReadCanvas
   argument. It saves the actual response to a returned asset path. Compare its
   complete source bytes with `source.canvas.tsx`, excluding only the identified
   response header/footer without trimming source whitespace. Never substitute a
   model-reproduced file. The bridge is a host capability to check, not an API
   implemented by this package. This comparison replaces the fallback edit checks.
4. If actual response bytes are unavailable, run `verification_steps` in order.
   Direct identical old/new edits are rejected. Atomic `edits` instead replaces a
   bounded fragment with a unique temporary slot and restores it before compilation,
   then advances only a trailing comment. Overlapping fragments cover the expected
   source and its boundaries; cleanup removes the comment. Complete ReadCanvas
   text inspection remains necessary to exclude extra or reordered content.
   Report the limits of text-only inspection. Fragment matches alone do not
   establish full byte identity.

Finally inspect the Page, exercise selection and check **Only you**. No method
here supplies a server-attested source hash: a hash of actual saved response
bytes is a local comparison result, distinct from the expected input hash.

Calls must succeed sequentially. Stop on any mismatch, transport or compiler
failure and preserve its diagnostic. Failed compilation retains the previous
revision; do not skip to the next step, guess source text or silently redesign
it. Resume only after reconciling the published `ReadCanvas` source with the
expected state before the failed step, then explicitly retry that exact call.
Do not use or silently repair an unpublished failed draft. Bounded calls reduce
transfer size; they do not eliminate model transcription errors. The native
trial caught a copying typo during verification and rejected its compilation
while preserving the working Page.

The current 14-day example uses ten delivery calls plus one saved ReadCanvas
response and a local byte comparison. The fallback uses nine verification edits
before readback inspection. Its 12,000-byte conservative
argument budget includes reserved ID space; it is a workbench guardrail, not a
vendor limit. Compact string/tuple packing reduces repeated data; inert bounded
string declarations allow even a 90-day snapshot to be assembled without a
large argument. Strings are joined before JSON parsing, including escape
sequences that cross a boundary. No `eval`, runtime package or network access is
introduced. The optional local test harness checks canonical field parity and
rendering equivalence.

A file path or `$file:` reference is not accepted by the native writer. The
bounded edit route uses the tools already present in Grok; it requires no Crumb
harness change or undocumented API. It does involve more native calls than
Muse's direct file handoff. Native mobile delivery and cross-device behavior
still require their own acceptance tests.

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
