---
name: garmin-visualization
description: Visualize health and activity trends from a Garmin Data Workbench archive, using the workbench logo and colors when a chart helps answer the question.
---

Read [the visualization guide](../../docs/VISUALIZATION.md) for commands, coverage semantics, generated demo data and delivery.

For sleep stages and scores use `sleep`/`get_sleep` and `chart sleep`; read [sleep semantics](../../docs/SLEEP.md). For Body Battery use `body-battery`/`get_body_battery` and its scalar trend charts; read [observed-reading semantics](../../docs/BODY_BATTERY.md). Sleep need is in minutes and its next-night value has a separate date. Do not re-extract raw JSON when the shared summary answers the question. Run installed `agent-guide` for interpretation and delivery rules.

Prefer the bundled `garmin-archive chart` command: it uses shared metrics and applies the approved branding. Put global `--data-dir` before `chart`. Use `--synthetic` for generated examples; the flag labels supplied data, not anonymizes it. The chat layout is the default; use `--layout wide` for reports.

When authoring a custom chart, run `garmin-archive brand` for the shared settings and local logo paths. Use its primary blue for the main series across metrics, navy for titles, and the supplied conversation-bubble asset as a small footer signature. Preserve the logo's shape and colors. Keep dates, units, denominators and dated gaps on the image; put relevant source, freshness, estimates and interpretation in the accompanying response. Keep images focused on the data; never treat missing values as zero or plot stale values after a failed refresh. Use real plotting tools for measurements.

Deliver the image using the host's supported attachment/image interface. If unavailable, state the limitation and use a concise table. Images and queries contain private health data. Making a chart does not authorize sync, configuration changes or publishing elsewhere.
