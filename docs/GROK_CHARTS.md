# Grok native interactive explorer

Grok Bot can present a private native Page beside its conversation. This is a
view over the workbench's shared query results, separate from the
[Muse HTML widget and MCP App](INTERACTIVE_CHARTS.md). The workbench now packages
a native TSX renderer so the layout and behavior can stay consistent between
requests. The HTML export is not interchangeable with a Grok Page.

**Status:** the branded explorer renders and responds in the Mac Grok Bot app in
its dark theme, delivered through bounded native edits. See the
[design pass](acceptance/2026-11-06-grok-design-pass.md), which also lists what remains
untested, and the earlier [bounded-delivery trial](acceptance/2026-11-05-grok-staged-delivery.md)
and [failed one-call transfer](acceptance/2026-11-05-grok-packaged-explorer.md).
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

`ui/recovery.canvas.tsx` owns presentation and follows the branded
[Muse widget](INTERACTIVE_CHARTS.md): the same masthead and date wording, a hero
built from the logo's two bubbles and an unsmoothed data line, a date scrubber
aligned to the chart columns, four linked chart lanes, Trends / Night detail /
Compare, Last 7, period bubbles and zero-based comparison bars. Hovering with a
mouse previews a night; a press, drag, tap or arrow key selects it. Gaps keep the
PNG charts' status shapes. Body Battery is in the night summary, Night detail and
Compare rather than a fifth lane. The four sleep stages exclude awake, in the PNG
order: Deep, REM, Light, Unclassified. All period averages and differences come
from shared Python queries. The renderer cannot query, sync or send a message.
Its view state is held only in local React state, with no persistence bridge;
actual native reopening behavior remains untested. Request a new snapshot to
refresh data.

The Page has no stylesheet of its own, so states and breakpoints are inline: hover
and focus use React state, the range input is transparent over a drawn thumb, and
widths use percentages, `min()` and `clamp()`. Only `Page`, `Section`, `useState`
and `useGrokTheme` are used at runtime. Colors and the logo come from `brand.json`
and `assets/logo.svg`, applied to the template at export; a test rejects other
color literals. The surface, font and motion timing come from `useGrokTheme()`.

### What the host does to a Page

Observed in the Mac app's dark theme with diagnostic Pages, November 6, 2026. None
of this is in Grok's documentation, so recheck it if the app changes.

- **It repaints colors at runtime.** After render it tags elements
  `data-grok-adapt-ink`, `-bg` and `-fill` and overrides their computed color. A
  read at mount still shows the authored value.
- **An explicit background on an ancestor keeps text and SVG as authored**, even
  when it equals the surface. On an unset background, grey text is dimmed and white
  SVG disappears. So the explorer's root sets `background: theme.bg.base`.
- **Near-white CSS backgrounds and borders are repainted anyway.** White and
  `#d6e3fb` turned dark; `#b4d1ff` survived. Draw near-white shapes as SVG, as the
  hero dot, chart guide, need swatch and picker chevron do. A white `rect` turned
  dark, and so did a white line drawn over it. A white `path` plate stayed white in a
  44 px test but not in the real 22 px footer.
- **A coloured CSS box protects what is inside it.** Inside `#b4d1ff` the adapter
  tagged nothing, and small white SVG stays white inside blue. So the logo sits on a
  `#b4d1ff` plate in dark theme and the hero dot's white centre sits in a blue disc.
  That plate then sampled near-white in the footer, which matches Muse; why is unknown.
- **Native `p`, `h1`–`h6`, `table`, `pre`, `ul`, `ol`, `dl`, `blockquote`, `figure`
  and `hr` get host typography.** Table cells also get `!important` padding and
  borders. The explorer uses plain elements with ARIA roles instead.
- **The compiler rejects some source** by name: reading the color scheme through
  `matchMedia` (`canvas-system-color-scheme`) and reading `outerHTML`
  (`canvas-injection-sink`). Grok reports those two rules; there may be others.
  Its theme declaration asks custom visuals to skip transitions for reduced motion,
  and a `matchMedia` query for that has compiled.

A browser check cannot see the first three, so `scripts/test_grok_widget.mjs` guards
their causes: the root's background, no native elements above, and in dark theme no
near-white CSS background or border. Judge the look from the real app.

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

Calls must succeed sequentially. Stop on any transport or compiler failure and
preserve its diagnostic. Failed compilation retains the previous revision; do not
skip to the next step, guess source text or silently redesign it. Resume only
after reconciling the published `ReadCanvas` source with the expected state before
the failed step, then explicitly retry that exact call. Do not use or silently
repair an unpublished failed draft.

Bounded calls reduce transfer size; they do not eliminate model transcription
errors, and compilation does not catch a wrong identifier that still type-checks.
Expect one in a delivery. Follow the plan's `step_verification`: after every step,
compare saved response bytes with that step's `after_sha256`. A mistyped or truncated
step that compiled has already been applied, so it cannot be retried. Report the
step, offset, expected and actual text, apply the smallest `EditCanvas` that restores
exactly the plan's bytes, and check again. The handoff directory's `fix_step.py`
prints that edit from the plan and the saved source; pass exactly what it prints.
Corrections written from memory failed to compile in the native trial, and the
script's did not. Stop if it exits with an error, a correction fails, or the same
step needs a second one.

The current 14-day example uses 13 delivery calls plus one saved ReadCanvas
response and a local byte comparison. The fallback uses 13 verification edits
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

### Check the design locally

```sh
uv run --locked python scripts/preview_grok_widget.py --output-dir /absolute/new/fixtures
npm ci --prefix scripts/grok_harness
npm exec --prefix scripts/grok_harness -- playwright install chromium webkit
node scripts/test_grok_widget.mjs --fixtures /absolute/new/fixtures --output-dir /absolute/new/checks
```

This runs the exact exported source in Chromium and WebKit at 320, 390 and 728
pixels in both themes, with no host stylesheet. It uses a React stand-in for
`grok/canvas`, so it does not verify Grok's compiler, sandbox or delivery. The
Mac app is Electron; phones are expected to use WebKit.

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
