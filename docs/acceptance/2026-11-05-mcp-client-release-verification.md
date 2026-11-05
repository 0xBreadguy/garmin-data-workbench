# Actual MCP client release verification — November 5, 2026

**Outcome:** Claude Code discovered the isolated synthetic stdio server and made model-originated MCP calls for sleep, PNG chart transport, deterministic period comparison, activity filtering and covered workout totals. Numerical results matched independent synthetic expectations. This is a real assistant/client exchange, beyond the SDK-only transport smoke. **Visible image delivery remains not run** in this headless client path; no graphical-client pass or live launch certification is claimed.

## Target, executed package and client

- Assigned T3-bound branch: `acceptance/mcp-client-release-verification-20261105`. The worktree started clean at the exact target, `2377478a9aded1951f917e32754e44e8c6ddaab5` (published main, PR #21). Product source was not edited.
- Reused the supplied release evidence: 171 offline tests, builds, installed CLI/MCP checks with and without charts, required three-OS matrix and post-merge package smoke. These were not rerun as a substitute for client acceptance. See [existing feature acceptance](2026-11-05-comparisons-workouts.md).
- Actual client: **Claude Code 2.1.318**, installed executable on the Mac's PATH. Its initialization identified model `claude-opus-5-5`. Supported print-mode sessions were used, rather than another coding agent impersonating Claude or an observer-created MCP SDK `ClientSession`.
- Actual command, server and archive host: the same local **macOS 27.0.1, build 26A434**, Python **3.12.13**, uv **0.11.2**. The model uses the provider service; execution/storage here did not take place in Muse's VM.
- Authentication was checked through the client's supported status command; existing subscription authentication was available. No credential file was opened, copied or changed, and no new secret was requested. Account metadata is omitted.
- Created a new absent temporary root outside the worktree. Exported the exact target with `git archive` into a new `source/` snapshot, created a separate `env/` using `uv sync --locked --extra charts`, and generated a new `demo/` outside repositories. This is a fresh source snapshot/environment/archive, not a new Git clone or a published-wheel installation.
- Independently observed the environment's Python and imported `garmin_archive.__file__` resolving to that snapshot's `src/garmin_archive/__init__.py`. The MCP configuration used that environment's absolute `bin/garmin-archive-mcp` and an explicit absolute synthetic `--data-dir`. Compared executed server/query/comparison/workout modules and the generator byte-for-byte against the target Git objects; all matched. Version `0.1.0` alone was not treated as revision evidence. No target drift was found.

Private absolute paths are intentionally omitted from Git. In the temporary evidence root, the same-host references are `env/bin/python`, `env/bin/garmin-archive-mcp`, `demo/archive.sqlite3`, `workouts/archive.sqlite3`, and the two session configuration JSON files. These are disposable test locations, not a durable user installation or a portable path handoff.

## Isolation and preserved state

Claude Code was chosen because its supported `--mcp-config` plus `--strict-mcp-config` route can select one uniquely named test server without persistent registration. Each initialization reported only `garmin-synthetic-release-20261105`, connected from dynamic configuration. No personal/default Garmin registration could be selected through this configuration. See the official [CLI reference](https://code.claude.com/docs/en/cli-reference) and [print-mode documentation](https://code.claude.com/docs/en/headless), also checked against installed `--help`.

The test used a new empty client working directory, `--setting-sources ""`, session settings disabling hooks, `--tools ""` to remove built-in shell/file tools, and an explicit allowlist of read-only synthetic MCP tools. `configure_sync` remained advertised by the server but was never allowed or invoked. No permission bypass flag was used. Sessions used `--no-session-persistence`; fresh conversations do not prove wiped provider context or a controlled persistence boundary.

Prior client executable presence and authentication were checked by supported metadata commands. Existing registrations/configuration contents, tools, chats, jobs, health archives, key files and token caches were not inspected or changed. Their contents/revisions remain unknown. No old environment was synchronized, tool replaced, app restarted, session closed, public endpoint/tunnel created, or existing archive queried. No Garmin request, authentication, sync, schedule modification or provider job occurred.

Raw client streams, stderr, synthetic fixtures and the received PNG stayed outside the repository. The streams contain model tool-use names/arguments and correlated tool results; these provide direct evidence rather than relying on an assistant's filesystem claims. Both synthetic database SHA-256 values were unchanged across the query sessions.

## Natural prompts and first outcomes

The first intended prompt was exactly:

> Use only the connected garmin-synthetic-release-20261105 MCP server and its generated synthetic archive. Do not use a shell, other servers, personal archives, credentials, Garmin requests, sync, schedules or jobs. Keep this manual and read-only. How was sleep April 24–30, 2026 inclusive? Show the sleep chart, with dates, coverage, units, synthetic provenance and freshness; if this client cannot display the returned image, explain the limitation. How did mean sleep duration that week compare with April 17–23, 2026? Also list cycling activities and summarize daily and Monday-week cycling distance and duration for April 24–30, 2026. Finally, text only: what sleep data is available January 12, 2026, and can I treat it as a zero?

**First attempt limitation:** the launcher inherited stdin from its Python heredoc. Claude reported additional launcher-script text after the request and declined to execute it. Exact model-visible stdin bytes were not independently captured, so the contamination mechanism remains an observer-harness inference from that response. This attempt is conservatively not counted as a pristine natural-prompt trial. No shell tool was available. The requested MCP queries still ran and a completed answer was captured before recovery.

Claude selected `agent_guide`, `archive_status`, `get_sleep`, `chart`, `compare_periods`, `list_activities` and `get_workout_summary`. Its additional `setup_status` request was denied because the observer omitted that read-only tool from the allowlist. Claude reported the denial and did not retry it or change a schedule. This is a harness permission gap, not a product or desktop-tool access denial.

Privacy-safe first-call evidence, with the common server prefix omitted:

| Tool | Model-selected arguments | Observed result |
| --- | --- | --- |
| `get_sleep` | `start=2026-04-24`, `end=2026-04-30` | Seven valid nights, synthetic provenance and simulated freshness |
| `chart` | `metric=sleep`, same bounds | PNG image block plus caption/coverage/provenance JSON |
| `compare_periods` | `metric=sleep_duration`, same bounds, `baseline_start=2026-04-17`, `baseline_end=2026-04-23` | Correct separate available-day means and change |
| `list_activities` | April bounds, `limit=100` | Empty list; first call did not apply native-sport filtering |
| `get_workout_summary` | April bounds, `activity_type=cycling` | All seven dates `not_checked`; null totals |
| `get_sleep` | `start=end=2026-01-12` | Failed-refresh data masked, no zero substituted |

The first answer gave 7h 24m mean sleep, score 78.7, 7/7 coverage, explicit synthetic labeling and simulated May 1 freshness. It preserved the failed January night as unknown. It correctly explained that the default April activity period has **0/7 checked dates, not zero cycling volume**. Monday buckets were clipped to April 24–26 and April 27–30. The default demo does contain two January cycling observations, but not in this requested April period; it did not demonstrate positive April workout totals.

The client received an actual `image/png` block: **79,181 bytes, 832 × 1400 pixels** after base64 decoding. Its accompanying contract-v1 metadata identified April 24–30 inclusive, duration/score/need coverage each 7/7, synthetic corpus v2 seed 42, hours for duration/need, score units, and simulated fetch time `2026-05-01T12:00:00+00:00`. The caption and alt text included dates, coverage, synthetic/wearable labeling and missing-value limits. The assistant acknowledged that it could only return text and could not confirm client display; it supplied a nightly table. Receipt and valid PNG bytes pass transport, not actual user-visible image delivery.

## Independent expected values

Sleep duration expectations were calculated directly from the generator formula `round((7.4 + 0.7*sin(i*1.3))*3600)`, independently of production query functions:

| Period, inclusive | Source seconds, in date order | Expected available-day mean |
| --- | --- | --- |
| April 17–23 | 25589, 28566, 28721, 25827, 24124, 26107, 28870 | 26829.142857… s; 7/7 |
| April 24–30 | 28367, 25333, 24214, 26649, 29071, 27931, 24900 | 26637.857142… s; 7/7 |

Period minus baseline is **−191.285714… seconds, −0.712977…%**. MCP returned rounded means 26829.14 and 26637.86 seconds, difference −191.29 seconds and −0.71%, with no warnings. The first human-facing comparison matched. January 12 is generator index 11: retained sleep followed by a synthetic failed refresh; masked duration and other fields are expected, not zero.

## Separate workout scenario

After retaining the default-demo outcome, a new marked synthetic `workouts/` archive was created using the generator's empty mode and the archive write APIs, following the independent fixture pattern in [comparison/workout tests](../../tests/test_comparisons_workouts.py). This intentionally added scenario has no live observations. Activity dates/IDs and source fields were:

| Date | Synthetic inputs |
| --- | --- |
| January 4 | Running ID 1: 1609.344 m, 600 s; running ID 2: missing distance, 300 s |
| January 5 | Running ID 3: 3218.688 m, 900 s; cycling ID 4: 999 m, 999 s |
| January 6 | Checked empty activity search |
| January 7 | Running ID 5: retained 99999 m / 99999 s, then failed refresh |
| January 8 | Unchecked |

The new session selected only this archive with the same uniquely named server. Its exact prompt was:

> This is a separate, explicitly labeled synthetic workout scenario, not the default demo. Use only the connected garmin-synthetic-release-20261105 MCP server. Stay read-only: no shell, personal data, credentials, Garmin requests, sync, schedules or jobs. Text only, no images. List only native sport running activities dated January 4–8, 2026 inclusive. Summarize running distance and duration for that period, each day and each Monday-start week. Explain per-field coverage and distinguish checked-empty, failed refresh and unchecked dates; do not turn missing data into zeros. Use both source units and the profile distance units.

This launcher explicitly disconnected stdin. Claude called both unfiltered and **`activity_type=running`** `list_activities`, then `get_workout_summary` with the exact January bounds and native running filter. Cycling ID 4 was excluded; failed ID 5 appeared with masked values in the list and was excluded from totals. It additionally attempted five `get_day` calls; those were not allowlisted and were denied. It completed from the returned workout data and disclosed the limitation. No chart call occurred in this text-only scenario.

Independent arithmetic: distance is 1609.344 + 3218.688 = **4828.032 m = 3 mi**, from **2/3** available runs; duration is 600 + 300 + 900 = **1800 s**, from **3/3** available runs. Available dates are **3/5**: two successful days plus one checked-empty day. January 6 has genuine stored zeros; January 7 and 8 remain unavailable. Week starting December 29, clipped to January 4, has 1609.344 m / 900 s; week starting January 5, clipped to January 5–8, has 3218.688 m / 900 s. MCP and final prose/tables matched all of these. The answer also warned against calculating pace from mismatched distance/duration coverage.

## Recovery and stage results

The original default-demo prompt was repeated in a separate fresh print-mode session with stdin disconnected and read-only `setup_status` allowlisted. This is a harness recovery, not an untouched first pass. No expected numbers, tool recipes or revised product guidance were supplied to coach arithmetic.

**Recovery completed:** discovery, sleep/chart receipt, comparison and failed-night masking succeeded again. The final answer repeated 7h 24m, −3m 11s / −0.71%, synthetic provenance, simulated freshness and unavailable April workout totals. It included the returned chart caption and a table, expressly disclaiming image attachment/display. The January denominator explanation now used actual 0/1 coverage rather than assuming a six-night denominator. Supplemental `get_day` and `get_trend` requests were denied by the narrow allowlist; Claude disclosed them, used permitted results and did not retry. The read-only status tool reported a schedule belonging to another archive; Claude left it untouched. This is status metadata, not authorization to inspect or change that schedule. Both final archive hashes remained unchanged. No graphical-client recovery was attempted.

| Stage | Result | Limit |
| --- | --- | --- |
| Isolated package/environment with charts | Passed | Exact-target editable snapshot; not client-led installation or published distribution |
| Actual client discovery | Passed | Claude initialization reports unique server connected and tools available |
| Model-originated MCP data calls | Passed | Correlated tool-use/result evidence; shell tools unavailable |
| Sleep and period comparison | Passed | Dates, seconds, means, change, coverage and provenance match independent expectations |
| Default-demo workout missingness | Passed | All-unchecked April period remains null, not zero |
| Positive workout/date/native-sport filtering | Passed | Separate scenario only; checked-empty, failed, unchecked and missing fields preserved |
| Failed sleep refresh | Passed | January 12 masked, not reported as current or zero |
| MCP PNG/caption transport | Passed | Actual image block and structured metadata received by real client |
| Actual visible image delivery | Not run | Headless print interface; receipt does not prove UI display |
| Text-only workout delivery | Passed | No chart requested/invoked in separate scenario |
| Read-only archive behavior | Passed | Both synthetic database hashes unchanged; no write tool invoked |
| Controlled session/restart persistence | Not run | Temporary storage and new processes do not establish lifecycle persistence |
| Live credentials/sync/Connect comparison | Not run | Explicitly excluded |
| Actual unattended execution | Not run | No schedule/provider job created or observed |

## Remaining issues and minimal proposals

No numerical query, filtering or renderer code defect, or critical product launch blocker, was established by this run. The following limitations should stay explicit rather than being promoted into full client certification:

1. **Medium, acceptance gap / external client surface. WHAT:** arrange a separately authorized graphical MCP-client delivery test if launch wording promises visible in-chat MCP charts. **WHY/evidence:** Claude received PNG content, but this print-mode run produced text only and expressly disclaimed display. **USER BENEFIT:** avoids promising a chart people cannot see. **VERIFY:** actual assistant-selected chart appears in that client's human-facing image interface, with dates/caption/coverage; do not substitute a path, SDK transport or observer-opened PNG. No product patch is justified by this evidence alone.
2. **Low, observer harness. WHAT:** disconnect stdin for scripted prompt arguments and allowlist the needed read-only status/day tools in future tests. **WHY/evidence:** first prompt included unintended launcher text; one first-run status call and five supplemental workout day calls were denied. **USER BENEFIT:** cleaner acceptance evidence and fewer irrelevant permission detours. **VERIFY:** a fresh client run receives only the stated prompt, completes intended read-only calls and preserves archive hashes. Keep schedule-changing tools unapproved. No repository framework or product permission change is proposed.
3. **Low, assistant adherence. WHAT:** qualify inferred average denominators by actual returned coverage. **WHY/evidence:** the first answer generalized that a seven-day window containing the failed January night would have denominator six; that assumes all other dates have values. **USER BENEFIT:** missing observations cannot silently inflate confidence. **VERIFY:** ask about a window with multiple distinct missingness cases and compare the denominator to returned `days_with_value`. Existing query semantics and guidance already require this; no demonstrated code fix is needed.

## Report verification and desktop release

Only this report is in scope for the local checkpoint. Review covers privacy, relative links, diff and `git diff --check`; no full suite is needed for this documentation-only change. Temporary raw chats, runtime logs, screenshot/image evidence and private paths are excluded from Git. There was no push, PR, issue, merge, tag, release, additional thread/subagent, monitoring or publication.

Desktop ownership began only after Muse's explicit grant. This client path used no CUA, browser or native-app control, so no CUA completion-summary call was applicable. Final client completion and permanent desktop release are reported to the coordinator before the report handoff. With the predecessor's grant and this final release, all three serialized verification desktop turns are finished; this does not imply all three tests passed.
