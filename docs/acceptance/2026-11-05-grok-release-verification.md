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

## Authorized older-session recovery — appended November 5

**Recovery outcome: synthetic CLI answers and actual image delivery passed through an older Grok session; shared-comparison adherence failed initially and passed only post hoc.** BREAD explicitly requested an older bot after observing different capabilities there. A new exclusive desktop grant followed Muse/MCP release. This append supplements the first-result checkpoint `f5df0efc0d2c6f88ec93ff4785afd2f33e9b64fa`; the earlier sections retain their original conditions and outcome. This was neither a fresh-conversation pass nor a controlled comparison of documentation or bot-count limits.

### Session selection and interruption

The previously accessed **Garmin Demo** bot was selected. Its existing conversation included BREAD's own capability questions and Grok's claim that git/uv/shell still worked. The observer sent:

> Yes, please try a separate fresh clone and environment for https://github.com/0xBreadguy/garmin-data-workbench at 2377478a9aded1951f917e32754e44e8c6ddaab5, using only its generated demo data outside all repositories. Check the new destinations are absent first, and leave your existing installs, archives, chats, configuration and jobs unchanged. Don't connect to Garmin, use credentials, sync, set up MCP or create recurring jobs. No authentication changes or full test-suite rerun needed. Tell me which host you're using and verify the executable/import really comes from the new version. If shell access is actually restricted, stop and say so.

Grok reported working shell access and began an isolated clone. Later its sidebar preview said the fresh clone worked on Debian 13 / Python 3.13.5. Before the full completion could be read, the selected conversation changed and Garmin Demo disappeared. CUA reported a user change, then a window-position error while refreshing navigation. BREAD explicitly confirmed accidentally deleting the bot while investigating a possible bot/subscription cap. **Garmin Demo recovery was interrupted**, not a query acceptance pass; its complete setup/import evidence was not observed. The observer did not delete or restore any bot, inspect unrelated chats, reuse its new installation or clean up its files. Incidental unrelated UI content was excluded from test inputs and this report. No evidence establishes a subscription cap or explains why capabilities differed.

BREAD authorized another chat. The observer selected the previously tested **Grok Post-Merge Retest Nov 4** bot, preserving its conversation, and sent:

> Please try the current Garmin workbench at exact revision 2377478a9aded1951f917e32754e44e8c6ddaab5 from https://github.com/0xBreadguy/garmin-data-workbench in a new absent checkout and separate new environment, with generated demo data outside all repositories. Preserve all old installations, archives, configuration and jobs; inspect prior state only by metadata/existence. Keep it synthetic and manual only: no Garmin requests, credentials, sync, live setup, MCP registration or recurring jobs. Don't change authentication or rerun the full test suite. Check your normal shell capability; if restricted, stop and report it. Please name the execution host and verify which new executable/import revision you actually use. Another bot may have just created a separate target-revision test folder; leave that unchanged too.

This bot reported an unrestricted shell, named its Debian VM before installation completed, and created a different isolated setup. No actual restriction was bypassed, authentication changed, new bot created, or subscription adjusted by the observer.

### Executed provenance and preservation

These facts are **Grok-reported**, not independently observed VM execution:

- Debian GNU/Linux 13, Linux 6.12.94 x86_64, on its shared VM; the native UI remained on the Mac.
- Clean detached checkout at full `2377478a9aded1951f917e32754e44e8c6ddaab5`. New environment executable's shebang pointed to that environment's Python. `garmin_archive` imported from the new checkout's `src/garmin_archive/__init__.py` through an editable `garmin-data-workbench` 0.1.0 installation. The package does not embed a commit; provenance is the reported editable-import-to-clean-checkout link. No target drift was reported.
- Separate new checkout/environment and a new default demo outside every repository; a second, separately labeled workout archive was also outside repositories. Absolute executable, import, source and both archive references usable on that VM were provided privately, with explicit archive selection. Private paths/host identifiers are omitted here.
- Grok said new destinations did not exist before creation. Its final explanation referred to birth times and its creation in this session, rather than exposing a pre-create metadata transcript; this claim is not independent proof of absence.
- Old checkouts at `28e2aa9` and `10672e4`, a prior `47dcd68` demo, the interrupted bot's new target folder, older demo storage, global CLI/MCP links and default config/archive locations were checked by existence/timestamps and checkout revision only. Rechecked timestamps matched its earlier session inventory. No private contents, old archive queries or job/config bodies were reported read. Metadata cannot prove unchanged file contents or all state.
- CLI only; no MCP connection/registration, live commands, Garmin requests, credential access, test-suite rerun or new recurring jobs reported. Network and forbidden-command claims were not independently audited.
- Same-conversation presence of the new executable/archive was rechecked. Persistence across a new session, logout, restart or reboot was **not tested**; filesystem persistence was only expected.

### Natural questions and first recovered answers

Exact goal prompt:

> Can you help me make sense of the demo data?

Grok gave a concise corpus overview and offered a conversational choice of sleep, Body Battery, steps/activity or another topic. It explained fixture dates, simulated fetch times, duration seconds versus need minutes, scores, and sampled Body Battery extrema. It did not ask a personal goal directly, but invited a direction; no extra intake question was forced. Its approximate “about 110 good days each” was not independently verified and should not be treated as a coverage receipt.

Exact sleep/goal prompt:

> I want to understand sleep consistency and running volume. How did sleep in the latest demo week compare with the previous week? Show me a chart too.

Grok selected April 24–30 versus April 17–23 transparently, reported **7h 24m versus 7h 27m, 7/7 nights each**, similar duration spread (about 29 minutes), score about 79 each, and lower latest-week sleep need. It described synthetic estimates without claiming a personal baseline or a cause. The means, ranges, score means and duration spread match independent generator arithmetic. It immediately identified two cycling records and no running observations, calling that a fixture gap rather than inventing a running trend.

The actual attachment was opened in Grok's media viewer. **Sleep overview, April 17–30, 2026; 7h 26m; 14/14 nights** showed readable separated date labels, stage stacks, total/need lines, a separate 0–100 score panel, coverage marks, branding and a prominent **SYNTHETIC DATA** label. Its combined mean and plotted course agree with the fixture and prose. One actual image was delivered/opened in this recovery; earlier-image previews were not counted. The accompanying prose did not carry simulated fetch freshness or explain the dotted need line. This is image delivery through a CLI-capable assistant, not MCP image transport.

Exact default-workout/text-only follow-up:

> For January 19–February 1, can you list the running workouts and give daily and Monday-week distance and duration totals, including which workouts were counted and how complete the data is? Keep it text-only for this answer. Also, what was the exact sleep change between those two April weeks?

Grok returned no running records, excluded cycling IDs 22/23, and qualified zero totals as covering only January 23/24. It stated **2/14 available days**, the remaining twelve `not_checked`, January 19–25 with two available days and zero runs, and January 26–February 1 with no available days and null totals. It preserved meters/seconds and displayed miles where appropriate. It did not infer a fully covered fortnight of no running. Text-only preference held.

The same reply gave April duration means **26637.86 versus 26829.14 seconds**, change **−191.29 seconds (−3.2 minutes)**; score **78.71 versus 79, −0.29 points**; need **485.71 versus 491.43 minutes, −5.71 minutes**; awake **1020 versus 814.29 seconds, +205.71 seconds**. These agree with independent arithmetic. Percentage change was not included until the provenance clarification below.

Exact missing-date prompt:

> Compare sleep duration March 12–18 with March 5–11, 2026, text only. Can we conclude the later week had less sleep?

Grok correctly refused that conclusion: March 5–11 had **7/7 observations**, about **27127 seconds / 7h 32m** mean; March 12–18 had **0/7**, all unchecked, with missing duration. It explicitly distinguished missing from zero and gave no decreasing-sleep conclusion. No attachment accompanied this text-only answer.

### Separate positive workout scenario

The default fixture's lack of running observations was recorded before this coached, separate scenario. Exact request:

> Since the default demo can't show positive running totals, please make a clearly separate, labeled synthetic workout example in a new absent archive outside repositories, leaving the default demo unchanged. Include a few runs across a Monday boundary, a cycling workout to exclude, a known empty day, an unchecked day and one run with missing distance. Then show which runs were counted and the daily and Monday-week distance/duration totals, measurement counts, day coverage and limits. Keep it text only, synthetic and manual, using the new installed workbench queries; don't change product code.

Grok reported a new `workout-example-1`, seed 7 archive; the default demo remained unchanged. It used the new CLI and reported the following invented inputs/results. The observer checked arithmetic over those stated inputs, not the VM database or fixture script. This does not prove the default demo can answer positive running-volume questions.

| Date in 2026 | Synthetic input / counted running result |
| --- | --- |
| January 10 | Run 101: 5000 m, 1800 s; both field counts 1 |
| January 11 | Run 102: 3000 m, 1200 s; both field counts 1 |
| January 12 | Run 103: 4000 m, 1500 s; both field counts 1 |
| January 13 | Cycling 104 excluded by native `running` type filter; checked zero runs |
| January 14 | Checked empty day; zero runs/distance/duration |
| January 15 | Run 105: missing distance, 900 s; distance count 0, duration count 1 |
| January 16 | Stored run 106 without checked collection state; excluded from totals, day counts unknown |

Reported coverage was **6/7 available days: five ok, one empty, one unchecked**. Week starting Monday January 5 was clipped to January 10–11: **8000 m, 3000 s, two runs**, two measurements of each field and two available days. Week starting January 12 was clipped to January 12–16: **4000 m from one distance field, 2400 s from two duration fields, two counted runs**, four available days. Overall **12000 m / 12 km from three distance measurements**, **5400 s / 90 minutes from four duration measurements**, four counted runs. Independent addition confirms those totals. Missing distance remained null on January 15 and made total distance partial; an unchecked day did not become zero. Grok qualified summary duration versus deduplicated elapsed time and clipped Monday buckets. No product code change or chart was requested/returned for this scenario.

### Final provenance clarification and separate post-hoc recovery

Exact final prompt:

> For my final verification notes, which exact commands powered the April and missing-week comparisons: the workbench's shared comparison command or your own arithmetic over another query? Please give the source units and returned change/coverage, including whether a percentage is valid. Did the sleep chart use the structured caption output, and what simulated freshness and sampling limits did it return? Confirm the host/OS, full executed source revision, version and import location, separate checkout/environment and outside-repository archive, CLI versus MCP route, and absolute executable/archive references usable on that same host. Were the new destinations absent before creation and prior metadata unchanged? What persistence was actually tested versus merely expected? Please use metadata/existence only for old state, no private contents, credentials or job/config bodies.

Grok explicitly admitted **both first comparisons used `sleep` JSON plus its own arithmetic, not `compare`**. Correct answers therefore do not pass initial shared-comparison adherence. It then separately labeled post-hoc `compare sleep_duration` results, not the route that powered the earlier answers:

- April: source unit seconds, field `sleepTimeSeconds`; baseline **26829.14**, period **26637.86**, both 7/7 ok; available change **−191.29 seconds / −0.71%**, percentage valid, no warnings.
- March: baseline **27126.57 seconds**, 7/7 ok; period mean null, 0/7 all unchecked; unavailable difference/percent, `period_incomplete_coverage` warning. No percentage is valid without the later-period mean.

These reported outputs agree with independent source arithmetic and semantics, but the observer did not capture exact full invocations or raw CLI output. Initial command selection **failed**; post-hoc shared-output retrieval **passed as reported**, after a direct route question.

Grok confirmed `chart sleep --json` produced structured caption/alt text but the answer used freeform prose instead. It reported duration/score/need coverage **14/14**, simulated earliest/latest fetch **2026-05-01T12:00:00+00:00**, and metadata explaining the dotted need estimate and independent score panel. It correctly noted that sleep chart metadata does not supply Body Battery sampling limits; those came from separate guidance/query context. Thus caption generation was reported successful, while original caption/freshness reuse was incomplete.

### Recovery stages and bounded findings

| Stage | Older-session recovery result |
| --- | --- |
| Garmin Demo shell/setup attempt | **Blocked by interruption** after reported clone success; bot deleted accidentally by BREAD, full result unread |
| Alternate old-session isolated target setup/import | **Passed as reported**, with explicit editable-import linkage; not an observer VM audit |
| Goal conversation and use of stated goal | **Passed**: offered direction and addressed sleep consistency/running volume |
| Initial shared comparison command selection | **Failed**: own arithmetic over sleep JSON |
| Sleep arithmetic / dates / units / coverage | **Passed**, independently checked; no arithmetic correction needed |
| Post-hoc shared comparison output | **Passed as reported**, separately labeled after provenance question |
| Visible sleep image delivery / readability | **Passed**, one actual opened attachment |
| Structured chart JSON generation | **Passed as reported**; original caption/freshness reuse **failed completeness** |
| Default native-sport filtering / coverage-qualified workout answer | **Passed**; absent running observations retained honestly |
| Separate positive workout summary | **Passed as reported**, independently checked arithmetic over reported synthetic inputs; coached scenario |
| All-missing date comparison / text-only preference | **Passed** |
| MCP discovery/query/image transport | **Not run**, each separately; CLI result does not establish connection |
| Controlled persistence / live Garmin / unattended execution | **Not run**, each separately |

No critical product defect or query/renderer calculation bug was established. No product patch was made. Two nonblocking assistant-adherence findings remain:

1. **WHAT:** use shared `compare` results for comparisons before composing prose. **Evidence / WHY:** the older session calculated both answers independently despite existing [installed guidance](../../src/garmin_archive/agent_guide.md); matching post-hoc results do not establish initial adherence. **USER BENEFIT:** preserves deterministic percentage/missingness semantics and reduces arithmetic drift. **SEVERITY:** medium adherence gap, not a demonstrated calculation defect in this run. **Minimal change:** enforce this in acceptance review; consider one compact comparison example only if the existing guide needs better discovery. No new framework or query implementation is justified. **Verification:** a natural repeat uses shared output initially, with changes/coverage/units matching prose and no post-hoc coaching.
2. **WHAT:** carry the existing chart JSON caption's essential freshness/need explanation into the first image reply. **Evidence / WHY:** metadata was generated but freeform prose omitted these fields. **USER BENEFIT:** users understand a newly rendered synthetic image is not current health data and what the dotted line estimates. **SEVERITY:** low adherence gap here; synthetic labeling and coverage were visible, and overview guidance already said fetch times were simulated. **Minimal change:** use the existing caption contract; a documentation example is only a hypothesis if another change is needed. **Verification:** first answer includes exact dates/coverage, simulated freshness and a concise need-line explanation with the displayed image.

The earlier fresh-bot access restriction remains recorded, but older sessions demonstrably reached useful answers through their normal surface. That prevents generalizing the initial blocker to all Grok bots. No causal explanation involving subscription, bot count or provider-policy changes was established. The bot deletion also prevents claiming uninterrupted preservation of all conversations by the overall session; the observer itself performed no deletions.

### Recovery checkpoint verification and final release

The observer repeated only standard-library fixture arithmetic: duration/score/need/awake means and duration spread for both April weeks, March baseline mean/range, and sums over the separately reported workout inputs. No observer installation, archive read, full suite or product patch was added. Report privacy, relative links, diff and `git diff --check` were reviewed before this new local checkpoint; the original checkpoint was not amended or rewritten.

Immediately after the final provenance response was observed, the next tool call was CUA `completion_summary` only. The observer permanently released desktop access and immediately sent the coordinator `DESKTOP_RELEASED` before writing this append. No successor was assigned; the coordinator owns launch-film notification. All subsequent work was offline report/Git work, with no UI reacquisition, push, publication or cleanup.
