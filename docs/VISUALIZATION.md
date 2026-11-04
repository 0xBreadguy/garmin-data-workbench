# Visualizing your archive

For a change over time, a chart can make patterns and gaps easier to see. Use a table or prose when it answers the question better. The chart command reads the existing archive; it does not sync or require Garmin credentials.

Install the optional chart dependencies from the repository:

```sh
uv tool install --from '.[charts]' garmin-data-workbench
```

For development, use `uv sync --locked --extra charts` and prefix commands with `uv run --locked --extra charts`.

```sh
garmin-archive chart sleep_duration --from 2026-01-01 --to 2026-01-30 --output sleep.png
```

`--data-dir` precedes `chart` when selecting a different archive. The output must be a new PNG file; existing files are never overwritten. Dates default to the same seven-day window as `trend`. The same five metrics and 90-day limit apply. Distance follows saved profile preferences; sleep is shown in hours. Other units come from the shared query. Gaps represent unavailable values, including failed refreshes; coverage and status counts are printed on the chart. Zero is a value. Do not infer a trend from sparse coverage or treat a chart as medical advice.

Agents: when a visual helps, create it in a private location and deliver it through the host's supported attachment or image interface. A local path alone may not be visible to the user; if delivery is unavailable, explain that and provide a concise table using `garmin-archive trend`. Query results and images can reach the AI provider; do not publish or upload them elsewhere without authorization. Avoid routes and precise coordinates by default. This command does not draw routes.

The optional [skill entry point](../skills/garmin-visualization/SKILL.md) can be read directly by any agent with repository access. Skill discovery and installation differ by host; it is not automatically installed or registered. If an agent cannot execute local commands, use its available rendering tools with the structured trend result, or use a table. Do not assume MCP access provides filesystem or image display access.
