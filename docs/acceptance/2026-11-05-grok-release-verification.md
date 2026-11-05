# Grok release verification — November 5, 2026

**Outcome: blocked before installation.** The actual Grok Bot app accepted the natural setup prompt in a fresh bot, identified the target revision, then requested GitHub sign-in. One clarification established a reported session restriction: repository checkout required its authenticated command-line tool; a public archive download was not an allowed alternative. No package execution, synthetic query or chart delivery was demonstrated. This is an external assistant-session blocker, not a demonstrated workbench defect or a current-release acceptance pass.

## Baseline and evidence

- Assigned native T3 worktree branch: `acceptance/grok-release-verification-20261105`; clean before preparation, at exact target `2377478a9aded1951f917e32754e44e8c6ddaab5` (published main, PR #21). No branch switch, shell worktree, extra thread or subagent was used.
- Assignment-supplied evidence reused: all 171 offline tests, source/wheel builds, installed CLI/MCP smoke checks with and without charts, required three-OS matrix, and post-merge package smoke passed. Those checks were not repeated for this report-only task. They do not prove real-client acceptance.
- Actual client independently observed through native UI: **Grok Bot**, bundle identity `com.anysphere.sand`. A new bot/conversation was created for this test; existing bots/chats were preserved. No coding agent substituted for Grok.
- Mac UI was observed. The assignment identified Grok's shared Debian VM, but this run never established the execution host/OS through a command or provenance answer. VM paths, Python version, archive location and same-host executable references remain unknown.
- Grok's first response linked the full target commit above as the current version. This verifies a visible source reference, **not** an executed package/import revision. No actual imported package, installed version or environment was demonstrated; target drift is unknown rather than passed.
- Fresh conversation does not imply fresh memory, account or filesystem. Prior installations and conversations remained present; no observer filesystem inspection of the VM occurred.

Preparation read [setup](../SETUP.md#mock-only-setup-stop-before-credentials), [assistant guidance](../ASSISTANTS.md), [acceptance reporting](../TESTING.md#assistant-acceptance-reports), the prior [Grok initial report](2026-11-04-grok-fresh-install.md), [Grok retest](2026-11-04-grok-post-merge-retest.md), [Muse retest](2026-11-04-muse-post-merge-retest.md), and [offline comparison/workout acceptance](2026-11-05-comparisons-workouts.md). Historical passes and failures were not substituted for current outcomes.

## Untouched first result

Exact initial prompt, without commands, recipe, hash or expected numbers:

> Hey, I want to try the current version of https://github.com/0xBreadguy/garmin-data-workbench using only generated demo data. Please leave my existing installation and data unchanged, don't connect to Garmin, and keep it manual—no recurring jobs.

Grok acknowledged demo-only isolation and preservation, then said it had begun a read-only check and would not change or launch anything yet. Its completed first result said the current version supported a separate offline generated-data setup, but repository setup required a Cursor cloud-agent plan or an authenticated GitHub command-line setup. It reported the latter was installed but needed sign-in, and offered a sign-in/run button.

**First-attempt installation: blocked.** No setup completed. Neither the sign-in button nor a cloud-agent route was selected. The user-visible result introduced an authentication prerequisite; whether that reflects actual tool policy cannot be independently established from the assistant's prose. No underlying denial/error transcript was exposed to the observer. This is not evidence that the public repository itself requires authentication.

The opening prompt differs from the earlier reports. This run is not a controlled documentation-only A/B comparison.

## Separate recovery attempt

Exact clarification:

> This is a public repository. Can you use its public download without GitHub sign-in, in a new separate checkout and environment with generated data outside the repository? Please preserve existing state, use your shell, keep it manual and synthetic only, and don't set up MCP or rerun the full test suite. If your tools block that, tell me the exact limitation rather than changing authentication.

Grok checked the alternative and replied that the public repository did not itself require sign-in, but this session permitted repository checkouts only through an authenticated command-line tool, which was not authenticated. It explicitly said a public archive download was not an allowed bypass. It reported no downloads, execution, authentication changes, MCP setup or tests, and said existing installation/data remained unchanged.

**Recovery: blocked.** No further workaround, alternate identifier, surface, new authentication, secret request or attempt to evade the reported restriction followed. The blocker is assistant-reported; CUA access itself worked and did not deny app access. The observer did not inspect credential files or authenticate a GitHub account.

Preservation is supported by Grok's statements, not by a before/after VM snapshot. There is no evidence of old-install modification, but no independently verified metadata inventory either. No prior archive/config/key/token contents, real health data or GPS were requested or used. Existing jobs and registrations were not audited; no new job or registration was requested or reported. No cleanup/reset was performed.

## New features and remaining stages

After the access blocker, unexercised stages remain **not run** under the repository reporting convention. No interpretation failure or arithmetic regression can be inferred from absent answers.

| Stage | Result and evidence |
| --- | --- |
| Actual app access / fresh conversation / first prompt | **Passed**: directly observed in Grok Bot |
| Current isolated package installation, first attempt | **Blocked**: authentication prerequisite reported; nothing installed |
| Public-download recovery | **Blocked**: session restriction reported; nothing downloaded or executed |
| Separate absent checkout/environment/outside-repo archive | **Not run**: no destinations created or verified |
| Executed version/import and same-host absolute handoff | **Not run**: target link alone is insufficient |
| Goal-oriented conversation | **Not run**: “Can you help me make sense of the demo data?” was not sent after setup was blocked |
| Shared sleep comparison, units/means/change/coverage | **Not run** |
| Date/native-sport activity filtering and counted workouts | **Not run** |
| Daily/Monday-week distance/duration summaries and measurement/day coverage | **Not run** |
| Sparse/all-missing explicit date comparison / text-only preference | **Not run** |
| CLI chart JSON caption/freshness/sample limits | **Not run** |
| Visible chart attachments | **Not run**: none returned; no image opened or claimed delivered |
| MCP registration, discovery, query, image transport | **Not run**, each separately; deliberately not configured in this CLI-capable assistant task |
| Controlled restart/new-session persistence | **Not run**: no installation or lifecycle boundary exercised |
| Live Garmin authentication, sync, real-data validation | **Not run**, excluded |
| Recurrence creation / actual unattended execution | **Not run**, excluded; manual-only request retained |

The planned sleep-consistency/running-volume goal, natural latest-demo-week comparison with a chart, running workouts with counted records, explicit sparse-date/text-only follow-up and final provenance question were therefore not sent. No scripted expected answer was supplied. The final recovery answer supplied the decisive access limitation instead of an execution-host handoff.

## Independent synthetic reference checks

These are observer source/arithmetic checks, **not Grok results or an observer installation**. Inspection of [the generator](../../scripts/create_demo_archive.py) and [focused tests](../../tests/test_comparisons_workouts.py) established:

- Default v2 demo: January 1–April 30, 2026, seed 42; collection timestamps are simulated May 1, 2026, 12:00 UTC, not current live freshness.
- April 17–23 sleep seconds: `25589, 28566, 28721, 25827, 24124, 26107, 28870`, mean `26829.142857` seconds. April 24–30: `28367, 25333, 24214, 26649, 29071, 27931, 24900`, mean `26637.857143` seconds. Both have 7/7 duration observations. Independent standard-library arithmetic gives period-minus-baseline `-191.285714` seconds (about 3m 11s), `-0.712977%`; shared output should round changes to `-191.29` seconds and `-0.71%`. Rounded mean displays are 7h 27m and 7h 24m.
- March 12–18 (indices 70–76) deliberately has no checked sleep observations: 0/7 available, mean/change unavailable, never zero sleep. This gap was not exercised in Grok.
- Default activity observations are only two cycling records on January 23/24: IDs 22/23, each 10,000 meters and 1,800 seconds. There are no running records, and activity collection is not checked across every demo date. No running records must not become a fully covered zero-running conclusion. No separate synthetic workout scenario was created after the blocker.

## Proposed next action and launch implications

**WHAT:** resolve the actual Grok session's authorized repository-access prerequisite, then repeat the natural synthetic setup in a fresh conversation and continue the planned queries. **Evidence / WHY:** both setup routes stopped before execution; the recovery explicitly reported an unauthenticated required tool and a prohibited alternative. **USER BENEFIT:** users can reach a real demo without unnecessary authentication detours or assumptions about which code ran. **SEVERITY:** medium external acceptance blocker for Grok; it prevents certifying this client for the release. It is not an established code defect or evidence that the workbench release is unusable elsewhere. **Verification:** observe a permitted isolated setup, actual executable/import revision at the target, outside-repo synthetic archive, shared comparison/workout output, opened chart attachments, and qualified same-host handoff. Authentication/access resolution belongs to the coordinator/user's authorized follow-up, not this report task.

No product patch or documentation change is justified by the current evidence. The existing mock route already supports public cloning and separate environments; a Grok-specific restriction should be confirmed before adding advice. Earlier arithmetic, archive-placement and sample-caveat findings are neither reproduced nor proven resolved by this blocked run. No critical product launch defect was established; **current-release Grok acceptance remains incomplete**. Other clients and MCP verification must retain their separate evidence.

## Report verification and desktop baton

Only this sanitized report is committed. Privacy/content review, relative-link checks, diff inspection and `git diff --check` passed. No raw chats, screenshots, runtime logs, private paths/account details, health data, archives, credentials or product changes are included. No push, PR, issue, merge, tag, release, monitoring or publication was performed.

Exclusive desktop grant was supplied before testing. Immediately after observing the final recovery blocker, the next tool call was CUA `completion_summary` only. Desktop ownership was then permanently released and an explicit `DESKTOP_GRANTED` message sent to the designated Muse successor in `mode:auto`, **before report writing or commit**. All subsequent work was offline report/Git work; UI was not reacquired. The new Grok bot and existing state were retained.
