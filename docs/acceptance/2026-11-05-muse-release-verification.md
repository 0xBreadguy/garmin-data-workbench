# Muse release verification — November 5, 2026

**Outcome:** the actual Muse app completed an isolated synthetic setup on the reported target revision without installation coaching, delivered two inspected sleep images, and answered filtered workout and missing-date questions. Nonempty workout totals passed in a separately requested generated scenario, not the default demo. Sleep means and shared comparison changes agreed with independent arithmetic. Some first-answer statistical wording failed and was corrected on clarification. No product code defect or critical launch blocker was established by this run.

This is a manual, synthetic CLI acceptance report. It does not certify live Garmin setup, MCP connectivity, persistence across a lifecycle boundary, or unattended execution.

## Target, client and evidence boundaries

| Item | Evidence |
| --- | --- |
| Exact target | Published main `2377478a9aded1951f917e32754e44e8c6ddaab5`, merged PR #21 |
| Observer baseline | Native T3-bound branch `acceptance/muse-release-verification-20261105`, clean at that exact full revision before preparation and report writing; no worktree creation or branch switching |
| Reused release evidence | Coordinator-supplied evidence: 171 offline tests, source/wheel builds, installed CLI/MCP smoke with and without charts, required three-OS matrix, and post-merge package smoke passed. Not independently rerun here |
| Actual assistant | Native Mac Muse, selected as `com.meta.endo`; the returned app/window identity was Muse. A new side conversation was created; old chats were retained |
| Execution host | Muse reported its own Ubuntu 24.04.5 Linux VM, Python 3.12.3 and uv 0.13.6, distinct from the Mac chat surface |
| Executed revision | Muse reported full target SHA, clean/dirty false, version 0.1.0 and charts available from the executing CLI's `version` JSON, with `garmin_archive` imported from the new source tree |
| Isolation and paths | Muse supplied same-host absolute executable, imported-package, source, environment, archive and image paths on final clarification. Source and environment were separate siblings; both archives were outside repositories. Private paths are intentionally omitted here |
| Route | Muse reported direct CLI shell calls using the new environment executable and explicit global `--data-dir`; no MCP server, registration or client connection |

Direct observations are the real app conversation, its visible answers, and two opened image attachments. VM execution, revision/import receipts, destination checks, archive hashes and preservation claims remain **assistant-reported**, not an independent VM audit. No target drift was reported; target execution is supported by Muse's receipt, not the observer checkout's SHA alone.

The first app submission attempt returned `Computer Use server error -10005: App quit`. Reopening the same Muse app restored access. A fresh empty side chat was then used, and a single successful setup message was visibly confirmed. This is an external UI recovery before the first assistant outcome, not an installation recovery or workbench defect. Composer accessibility also opened a file picker once; it was canceled without opening or attaching a file. No alternate assistant/browser was substituted.

Desktop work began only after Grok's explicit `DESKTOP_GRANTED`. A new chat did not reset assistant memory, account state or the VM filesystem. This prompt differs from earlier rounds, so no controlled documentation-only A/B claim is made.

## Exact prompts and untouched outcomes

The first natural prompt supplied no commands, hash, fixture dates or expected values:

> Hey, I want to try the current version of https://github.com/0xBreadguy/garmin-data-workbench using only generated demo data. Please leave my existing installation and data unchanged, don't connect to Garmin, and keep it manual—no recurring jobs.

**First setup: passed, assistant-reported.** Muse reported a fresh clone, separate environment and new generated archive under a new root, full target revision and imported-package provenance. Unlike the [previous retest](2026-11-04-muse-post-merge-retest.md), it did not stop at or silently reuse the old installation. It reported old checkouts still clean at `28e2aa9`, `10672e4` and `47dcd68`, checked by metadata only. The new root was reported absent before creation. It reported no old archive/configuration-content reads, no in-place pull/reinstall, and absent default Garmin configuration/archive and key environment variable. It reported the new demo hash unchanged after queries.

Muse disclosed its VM versus Mac host in the completion answer, **not before execution**, and initially gave only a root name rather than the complete absolute-path handoff. These are remaining adherence gaps. The final handoff did not separately document an absence check for the later workout-scenario destination; do not infer one from the default root check.

The default corpus was v2, seed 42, January 1–April 30, 2026, with simulated fetch time May 1, 2026. Muse attached a sleep overview for April 24–30 immediately. The opened image showed synthetic labeling, 7h 24m mean, 7/7 coverage, readable April 24/26/28/30 labels, stage stacks, Garmin-need line, separate score panel and branding. Visible image delivery **passed** without setup coaching.

The second prompt was:

> Can you help me make sense of the demo data?

Muse gave a cross-metric overview, distinguished generated co-occurrence from cause/baseline/readiness, and asked what to dig into first, with sleep/recovery/activity/comparison choices. This was conversational topic selection rather than a direct improvement-goal question. It did not make intake a prerequisite. The observer then supplied the requested goal naturally:

> I want to understand sleep consistency and running volume. How did sleep in the latest demo week compare with the previous week? Please show me a chart too.

Muse selected April 24–30 versus April 17–23 explicitly, both 7/7 nights. It gave means of 7h 24m versus 7h 27m, roughly equal duration variability, stage/need/nap context, and examples showing that the score did not simply track duration. It also proactively queried running and explained that both April weeks were unchecked for activity, with missing distance/duration rather than zero. An earlier overview's “no activities at all” wording was broader than coverage supports; the explicit comparison clarified the gap without an observer correction.

The opened comparison image showed April 17–30, 14/14 nights, a 7h 26m combined mean, readable date labels, synthetic provenance, stages/need and independent score panel. Its content matched the broad prose. Neither attachment established MCP transport. The explicit comparison answer omitted a fresh fetch-time line; simulated freshness had appeared earlier and was detailed later.

**First-answer precision: failed in part.** “Spread” was not defined; “same score spread” overstated similarity; and “below need on 6 of 7 nights, averaging 44/42 minutes short” read as a six-night average even though those numbers used all seven signed differences. It also switched from a rounded 6h 44m minimum to 6h 43m without explaining truncation. These were assistant presentation errors, not observed query defects. Accurate means and a useful restrained overall conclusion do not erase them.

## Default workout gap, then a separate scenario

The explicit default-demo request was:

> Please list the running workouts for January 19–February 1, 2026 in this demo, and show daily and Monday-week distance and duration totals, including which workouts were counted and what coverage is missing. Keep this answer text-only.

**Passed:** Muse listed no matching running workouts and identified the excluded cycling records: synthetic indoor ride ID 22 on January 23 and outdoor ride ID 23 on January 24. Each is 10,000 m / 1,800 s. Running is zero only on those two checked dates. January 19–25 had 2/7 available days; January 26–February 1 had 0/7 and null totals. Twelve of fourteen dates were unchecked, so Muse correctly refused to call the complete period zero. Text-only was honored. The default generator contains these two cycling records and no running observations; it cannot demonstrate nonempty running volume.

Only after preserving that result, the observer requested a distinct scenario:

> The default demo running gap is clear. Please preserve it and create a separate, clearly labeled generated workout-only scenario outside all repositories, with some running and cycling across two Monday weeks, one running workout with a missing measurement, and both a known-empty and an unchecked day. Then list the running workouts and their daily and weekly distance/duration totals, with which entries counted and the limits. Keep this text-only and entirely offline/manual.

Muse reported a separate outside-repository archive with a synthetic marker, scenario definition and build script, leaving the default archive hash unchanged. This is a deliberately supplied test scenario, **not an untouched default-demo success**. Its nine reported running entries were:

| Date, 2026 | Distance, m | Duration, s |
| --- | ---: | ---: |
| Jan 19 | 5,000 | 1,500 |
| Jan 21 | 8,000 | 2,400 |
| Jan 23 | 10,000 | 3,000 |
| Jan 24 | 7,000 | 2,700 |
| Jan 26 | 6,000 | 1,800 |
| Jan 27 | 9,000 | Missing |
| Jan 29 | 4,000 | 1,200 |
| Jan 31 | 12,000 | 3,600 |
| Feb 1 | 3,000 | 900 |

**Passed:** Monday-week subtotals were 30,000 m / 9,600 s across four runs with 6/7 days available, then 34,000 m / 7,500 s across five runs with 7/7 days available. The second duration covered only four runs. Overall: 64,000 m / 17,100 s, nine runs, 13/14 available dates, distance on 9/9 runs and duration on 8/9. Display distances were 18.64, 21.13 and 39.77 miles respectively. Independent addition of the reported rows agrees; the VM scenario contents were not independently read.

January 20 remained unchecked/null. January 25 and 30 were known-empty/zero. January 22 and 28 were checked cycling-only days, zero after the exact native running filter. The excluded rides were 20,000 m / 3,600 s and 15,000 m / 2,700 s. Muse explicitly limited totals to available summaries and described the missing duration and unchecked date. No sport subtype, multisport-parent or overlapping-recording case was independently exercised in this focused conversation; those remain covered only by the supplied offline evidence.

## Missing-date comparison and factual recovery

The gap prompt returned to the unchanged default archive:

> Back in the unchanged default demo, compare sleep duration for March 12–18, 2026 with March 5–11. Keep it text-only; tell me what can actually be concluded when dates are missing.

**Passed:** March 5–11 had 7/7 values and mean 27,126.57 s (7h 32m). March 12–18 had 0/7, all `not_checked`, null mean and no fetch/attempt times. Muse reported the shared comparison's unavailable change, null difference/percentage and `period_incomplete_coverage` warning. It did not invent a trend, impute values, or treat missing as zero. No image was delivered, as requested.

The final natural provenance/clarification prompt was:

> Before we wrap up, give me a compact provenance handoff: where commands actually ran versus this Mac app; the full revision and imported package/executable actually used; separate source/environment and outside-repo archives with absolute same-host paths; how you checked destinations and preserved old state; CLI versus MCP route; the exact compare, activity-filter, workout-summary and chart commands used, including whether chart metadata was used. State what freshness and persistence are simulated, claimed or actually tested, and confirm manual/synthetic limits. Also clarify what your sleep 'spread' and 'averaging short' numbers meant and their denominators, whether the score spreads were really the same, and give the shared comparison's source-unit change for the April weeks. Keep it text-only; do not inspect old archive/config contents, credentials, unrelated jobs or chats, or run any live/setup/sync/schedule operation.

**Factual recovery passed:** Muse supplied the provenance in the first table, full absolute-path references, fixed simulated `2026-05-01T12:00:00+00:00` timestamps for both archives, and distinguished creation time from fetch time. It explicitly said persistence was not tested: no restart/new-session boundary, only files still present under VM home storage with reported unchanged hashes. No persistence pass is claimed.

Muse identified spread as population standard deviation: 28.97 versus 28.99 minutes for sleep duration. It acknowledged that score spreads were not identical: ranges 24 versus 22 points and SDs 8.37 versus 7.85. It clarified all-seven signed sleep-minus-need means of −44.3 and −41.8 minutes, versus −52.7 and −49.2 over the six below-need nights. This corrected the denominator ambiguity only after the final question. These figures agree with independent standard-library reproduction of the generator's formulas/random draws.

Independent April duration expectations, in seconds:

- April 17–23: `25589, 28566, 28721, 25827, 24124, 26107, 28870`; mean **26,829.142857**.
- April 24–30: `28367, 25333, 24214, 26649, 29071, 27931, 24900`; mean **26,637.857143**.
- Shared change: **−191.29 s / −0.71%**, each mean using its own 7/7 denominator; scores **79.0 versus 78.714286**, change **−0.29 points**, percentage inapplicable to the scale.

Muse's final shared-output figures matched these expectations with no warnings. This checks generated arithmetic, not physiological meaning.

Muse reported using `version`, `metrics`, `agent-guide`, shared `compare sleep_duration` and `compare sleep_score` with explicit April/baseline bounds, and `compare sleep_duration` for the March gap. It reported `activities --from 2026-01-19 --to 2026-02-01 --type running` and the identically bounded/filtered `workout-summary` on each archive, plus unfiltered inspections. Chart invocations were `chart sleep` with explicit April 24–30 or April 17–30 dates, `--synthetic` and separate new output files. **It did not report using `chart --json`**; its answer instead discussed metadata files/chart inputs. Thus adoption of the new structured caption/freshness output was not demonstrated. Caption omissions cannot be attributed to a broken metadata API on this evidence.

## Stage results and remaining work

| Stage | Result |
| --- | --- |
| Fresh isolated target setup | **Passed, assistant-reported**, no setup coaching; remote revision/filesystem claims not independently audited |
| Host before work / complete first absolute handoff | **Failed**; host arrived at completion, absolute references on final clarification |
| Goal-oriented conversation | **Passed** topic selection and goal use; no forced intake question |
| Shared sleep comparison means/change/coverage | **Passed**, shared route reported and arithmetic independently checked |
| First sleep statistical wording | **Failed** in part; denominator and score-spread recovery **passed** separately |
| Default native-sport/date filtering and missing coverage | **Passed**, no default running data fabricated |
| Nonempty daily/Monday-week totals | **Passed** in separate requested synthetic scenario; partial measurement/date coverage explicit |
| All-missing explicit comparison / text preference | **Passed**, null remains missing; no unwanted image |
| Visible image delivery | **Passed**, two actual attachments opened and inspected |
| CLI structured chart-caption adoption | **Failed** to demonstrate instructed `--json` use; freshness omitted beside explicit comparison image |
| MCP registration, discovery, query, image transport | **Not run**, each; CLI acceptance does not establish any MCP stage |
| Controlled restart/new-session persistence | **Not run** |
| Unavailable-renderer fallback / wide-layout delivery | **Not run** in this focused conversation |
| Live credentials, Garmin requests/sync, real-field validation | **Not run**, excluded |
| Recurring/provider-job creation and actual unattended execution | **Not run**, excluded |

No real key, token cache, personal archive, raw health response or GPS record was intentionally accessed. No live setup, credential entry, Garmin request, sync, shared client configuration, scheduling or provider job was authorized or observed. Muse confirmed these exclusions; traffic and all prior VM state were not independently audited. Old tools, registrations, jobs and conversations were not intentionally altered. No observer installation or product test rerun was used as a substitute for acceptance.

## Minimal proposals for coordinator review

No product patch is justified by this run. These are nonblocking assistant-adherence findings; documentation effectiveness remains a hypothesis, not a demonstrated fix.

1. **Low — label statistics and preserve their denominators. WHAT:** retain source comparison changes and explicitly name population SD, range, signed seven-night deficit or below-need-only deficit. **Evidence/WHY:** the first answer conflated the latter denominators and called differing score spreads the same; clarification corrected both. **USER BENEFIT:** reliable, understandable sleep comparisons without a follow-up audit. **Verification:** a fresh natural comparison should state exact denominators and source-unit changes consistently; check against these independent expectations. Existing [agent guidance](../../src/garmin_archive/agent_guide.md) already requires aggregate/denominator fidelity; prefer adherence over new query code.
2. **Low — complete the host/caption handoff on the first answer. WHAT:** follow existing [setup](../SETUP.md#hand-off) and [assistant guidance](../ASSISTANTS.md) before execution and use `chart --json` captions/freshness in delivery. **Evidence/WHY:** VM host came after setup, complete paths arrived late, and the chart command receipt omitted `--json`; comparison freshness was absent. **USER BENEFIT:** users know where the installation lives and why a newly rendered demo image is not current health data. **Verification:** observe early host disclosure, an immediate same-host absolute handoff, and a chart answer with dates, denominator and simulated freshness without coaching. Consider a compact example only if it adds to existing guidance; no installer/renderer change is established as necessary.

## Verification and desktop handoff

Report-only checks: privacy/content review, relative-link existence, diff inspection and `git diff --check`. Only this report is staged and locally committed; raw chats, screenshots, logs, private paths/account identifiers and archives are excluded. No pushes, PRs, issues, merges, releases or monitoring were performed.

Immediately after observing the final Muse answer, the next tool call was CUA `completion_summary` only. Desktop ownership was then permanently released and `DESKTOP_GRANTED` sent with `t3_thread_send mode:auto` to the designated MCP successor **before report writing/commit**. All later work was filesystem-only. The coordinator retains all integration and release authority.
