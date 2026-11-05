# Comparisons and workout summaries — offline acceptance

November 5, 2026. Implementation starts from public main `f2e2312`. This report covers synthetic queries on the development macOS host, with Python 3.12.13. It does not establish a live Garmin or third-party assistant acceptance pass.

## Exercised behavior

The full 171-test offline suite passed with charts installed. Independent synthetic cases verify comparison arithmetic from unrounded observations, distinct zero/missing/scale percentage reasons, unequal/incomplete/current-period warnings, failed-retained masking, date bounds, weekly boundaries, per-field coverage, exact sport filtering and multisport parent exclusion before date/type filtering. Ordinary overlapping recordings remain separate.

Installed-wheel checks passed with and without chart dependencies. Each creates a disposable environment and a separate outside-checkout synthetic archive. Real CLI subprocesses and stdio MCP sessions read that archive from outside the checkout. Both interfaces return identical comparison and workout-summary results; independent smoke expectations are a 1,234-step mean difference / 100% change, and a 5,000-meter / 1,800-second running total. The activity filter selects the expected ID. Archive bytes remain unchanged. Existing checks also exercise PNG/MCP image transport when charts are installed and explicit dependency-unavailable behavior otherwise.

The first extended smoke attempt incorrectly assumed every ordinary MCP response had `structuredContent`. The smoke reader now accepts JSON text as well, matching the existing MCP query convention; both installation modes then passed. This was a verification-script defect, not evidence of failed query transport.

Builds and source diff checks passed. Required platform checks and the final PR revision are recorded by GitHub CI; local macOS checks alone do not validate live Windows/Linux installations.

## Outstanding stages

| Stage | Result / next evidence needed |
| --- | --- |
| Actual assistant interpretation of the new tools | Not run; ask a supported client to compare two explicit synthetic periods and summarize a filtered workout week without coaching. |
| Visible image delivery in a third-party assistant | Not run here; installed MCP PNG transport is separate evidence. Existing client reports retain their original scope. |
| Controlled provider new-session/restart persistence | Not run; verify the same synthetic installation/archive across the actual lifecycle boundary. Separate local processes are not that boundary. |
| Private live key entry and Garmin Connect comparison | Not run; requires authorized live setup and representative source-value checks. No credentials or personal archive were accessed here. |
| Actual unattended sync / report delivery | Not run; no scheduler or provider routine was configured. Verify a real opted-in execution and inspect freshness/failures separately from delivery. |
| Native Windows storage ACL privacy | Not run; remains a separate prerequisite for claiming private live Windows setup. |

Provider-specific scheduling remains the assistant/provider's responsibility. Existing catch-up, locking, routine templates and status evidence remain the foundation; this change adds no scheduler integration. Diagnostic changes should follow demonstrated operational failures. See [testing](../TESTING.md#assistant-acceptance-reports) for stage-by-stage reporting and [usage](../USAGE.md#compare-periods-and-summarize-workouts) for query limitations.
