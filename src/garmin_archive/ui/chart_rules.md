# Building an interactive Garmin chart (experimental)

Build the chart this question needs. There is no fixed layout: you choose the form, the
lanes and the interaction. The starter is one small working chart and the reference is a
larger finished view. Take what helps, change or drop the rest, and add marks freely.

Decide the view first. Things being compared share one lane and one unit, such as sleep
against need in hours, or steps against a goal. Parts of a whole form a stack. Refilling
the starter's lanes is fine only if the result still answers the question. The reference
is large, so search it for a pattern such as `stage` and do not read or copy it whole.

## Data, never broken
- Show only returned values. Never fill, smooth, interpolate or invent a metric. A labeled
  difference between two returned values is allowed.
- `null` is a gap, independently per lane; no line or bar crosses it.
- A real zero gets a visible mark at the baseline, never an invisible zero-height bar.
- Mark gaps by status: `error` ×, `empty` □, `not_checked` |,
  `metric_not_returned` ◇, `response_missing` +. Key only the statuses present, and keep
  gap marks clear of other marks.
- Label inclusive calendar dates, units and each lane's `days_with_value`/`requested_days`.
- Calendar dates never pass through a time zone. Retain query freshness and source meaning.
- If `archive_provenance.synthetic` is true, show SYNTHETIC DATA. Unmarked is unknown.
- Replace SAMPLE DATA, REPLACE only after replacing all invented observations.
- No cause claims; do not imply a rise or fall is inherently good or bad.

## Know your query
These are traps, not new chart definitions. Consult the installed `agent-guide` and:
- `sleep` durations are seconds; sleep need is minutes: docs/SLEEP.md.
- Use `stages_complete`; never infer stages or draw an incomplete stack, but still list the
  stage values returned. Awake is not a sleep stage: docs/SLEEP.md.
- Source-local timestamps stay as returned; never assign today's time zone: docs/SLEEP.md.
- A `not_checked` day is not zero or a rest day, including in `workout-summary`: docs/USAGE.md.
- Body Battery charge is daily, not overnight: docs/BODY_BATTERY.md.
- A Body Battery day can say `status: ok` and still return `null`. That is a gap. Label it
  from `report_status`, or `readings_status` if that is `ok`, by adding a glyph and short
  name to `glyphs` and `names`, such as `unrecognized_response`, `?`, `unrecognized`.
  Never borrow another status's label.
Repository docs: https://github.com/0xBreadguy/garmin-data-workbench/tree/main/docs

## Colors
Layouts may differ; colors stay consistent. Use brand.json `colors` or `dark_colors`, matching
the host theme, in this order of preference:
1. One series: `primary`.
2. A reference such as a goal or need: `secondary`, dashed and labeled.
3. Several series: `series` in its listed order. A metric keeps its color across the whole
   chart; never cycle. Past five, split into lanes.
4. Sleep stages: `sleep_stages`, always Deep, REM, Light, Unclassified.
5. Gaps, axes and notes: `secondary`. Grid and dividers: `rule`.
Text stays `ink` or `secondary`, never a series color. Color never means good or bad. Two or
more series get a legend or direct labels. The Grok starter has `p.series`; Muse has
`--series-1` to `--series-5`.

## Readable, interactive charts
- Convert units for display, such as `7h 42m`; never show raw seconds. Use thousands
  separators. Write dates as `Jan 12` and ranges as `Jan 12–25, 2026`.
- Each scale is labeled, with three to five round ticks. Bars start at zero; lines are
  unsmoothed and may focus on their range. Never put two scales on one lane.
- Keep plots inset so first and last marks never clip. At most five date labels on an axis,
  directly under the plots. Date and axis labels never wrap: use `white-space: nowrap`.
  Above about 31 days, drop per-point dots but keep lone observations visible.
- Hover, tap and keyboard must reveal exact values. By default one selected date drives all
  lanes and readouts, with a slider, as the starter does. Change this if the question is
  better served; prevent text selection on drag and use `touch-action: pan-y`.
- Keep the title short. Provenance goes in the badge, not the title. No intro paragraph unless
  it says something the charts do not. No filler headings. Avoid nested scrolling.
- Work at 320 px and up, light and dark, with no horizontal scroll.
- Small footer signature, about 22 px high, preserving logo proportions and colors.

## You may not be able to see the chart
Hosted views often cannot be opened from your tools, so a chart can compile, hold correct data
and still be broken on screen. Never hard-code a scale: derive it from the values drawn, or use
a fixed domain that contains them. By script, compute where the largest and smallest values
land; every mark must fall inside its plot. A syntax check or compile is not a run: execute the
code, using a small DOM stand-in if you have no browser, and confirm every date fills in without
an error. If your tools can render a local copy, do that and look at it. If they cannot, say so.

## Grok Page — see docs/GROK_CHARTS.md
- Import only from `grok/canvas`, in strict TypeScript with typed callbacks. Inline SVG works
  for marks. Its native chart components have no selection callbacks.
- Root sets `background: theme.bg.base` and `fontFamily: theme.font.family`.
  Use `theme.motion` for motion; skip transitions for reduced motion.
- No near-white CSS backgrounds/borders or near-white `rect` shapes: the host repaints them.
  Keep the small logo on a blue plate in dark theme. Use SVG paths for pale shapes.
- No `p`, `h1`–`h6`, `table`, `ul`, `pre`; use `div`/`span` with ARIA roles.
- No `outerHTML`, `innerHTML` or `matchMedia` on the color scheme.
- Over about 12 KB, write a skeleton first, then append complete declarations with
  `EditCanvas`, so every step compiles. Check saved source bytes, not retyped copies.

## Muse widget — see docs/INTERACTIVE_CHARTS.md
- One HTML fragment with inline code; no forms, remote assets or nested frames.
- Host surface/text use `--hatch-widget-*`; choose brand colors for the host theme.
- Present with `widget.create_html_file_widget`, using a path outside
  `workspace/your_files/` and `workspace/visual_grounding/`.

## Before replying
Verify embedded dates, values, nulls, statuses and coverage by script against query JSON,
not by eye. Say what passed, what remains untested, and whether you could see the chart.
