# Muse fresh-install acceptance — November 4, 2026

The actual Muse Mac app completed mock-only installation and answered sleep and steps questions with images visible in its chat. No setup workaround or recipe was supplied before its first result. The main observable defect was crowded date labels in the seven-day sleep chart. Host disclosure and resumable setup evidence could also be clearer.

This is a **synthetic, same-host CLI acceptance pass**, not a live Garmin, native Mac installation, MCP, or recurring-execution pass. Proposed product changes below are for coordinator review; this branch changes only this report.

## Revision and environment

| Item | Evidence |
| --- | --- |
| Baseline | Published main `28e2aa9a399346feb8068ab3a27d1e4c4adf8920` |
| Observer checkout | T3-bound `acceptance/muse-fresh-install-20261104`, clean at that exact baseline before report writing |
| Muse installation | Muse reported a fresh, clean main clone at `28e2aa9`, installed with the charts extra; no full structured VM build receipt was captured |
| Human interface | Native Muse Mac app, identified in actual app inventory; fresh side chat, existing conversations preserved |
| Execution host | Muse reported Ubuntu 24.04.5 in its own Linux VM; commands did not run on the Mac |
| Storage | Muse reported checkout, uv tool installation, and demo under persistent VM home storage; survival across a new chat/restart was not independently exercised |
| Query path | Muse explicitly confirmed workbench CLI commands in the VM, with an explicit synthetic archive directory |
| Corpus | v2, seed 42; January 1–April 30, 2026, 120 dates; simulated collection timestamp May 1, 2026; UTC profile |
| Cadence | Manual/on demand; no new recurring job requested or reported created |

Observations were made through native app accessibility and rendered image views. VM command execution, initial filesystem state, test results, archive hashes, and job inspection are **Muse-reported evidence**, not independently observed terminal transcripts. Independent local checks below use repository code and synthetic arithmetic only.

## Freshness and preservation limits

Muse reported checking before cloning: the uv tool list was empty and the working checkout/demo directories were absent. It reported that previous copies remained recoverable in trash. This was a fresh working installation, **not a wiped assistant account or memory**. A fresh side chat still inherited assistant context; the activity UI explicitly displayed memory review.

On follow-up, Muse reported no default key/configuration directory or default health archive, an unset key environment variable, and no Garmin recurring job. The follow-up expressly limited inspection to installation metadata and file existence. Existing trash, unrelated jobs, conversations, client settings, and other assistants were preserved. No purge was requested or performed by this tester.

The observer never opened a Garmin key, token cache, real archive, activity file, or real health response. No secret was requested or supplied. No Garmin authentication/sync path was authorized. Muse reported that it did not run `install`, `sync`, `save-key`, or a live connection check; its visible answers remained synthetic throughout. Network traffic was not independently audited, so this is not a packet-level no-request attestation.

## Untouched first attempt

The first message sent to Muse was exactly:

> Hey, I want to install this repo: https://github.com/0xBreadguy/garmin-data-workbench. Please use only mock data for this test—don't connect to Garmin, make any Garmin API requests, or access any existing personal health data.

No commands, checklist, setup recipe, or credentials were preloaded. Muse worked for roughly five minutes, showing environment checking and memory review, then delivered its first result without another message from the tester.

Its opening result reported a clean baseline installation with charts, 145 passing offline tests, a generated corpus, successful day/trend/sleep/Body Battery queries, and unchanged archive hash after reads. It attached three January 1–30 charts: sleep duration, sleep overview, and Body Battery. The tester saw all three thumbnails and opened the sleep overview at full size. It displayed the synthetic label, 7h 22m average, 26/30 coverage, stage bars, a separate score panel, missing-date notes, and workbench branding.

No initial safety violation or installation blocker was observed. There was no recovery prompt or workaround needed to obtain that result. Muse selected charts itself rather than asking about features, and did not explain the Mac-versus-VM host until asked.

## Conversational acceptance evidence

After the initial outcome was recorded, the tester accepted charts, explicitly selected manual/on-demand behavior, declined credentials, and asked where the installation ran and whether the old installation was absent. Muse disclosed the VM and prior-state limitations above. It also reported that the uv binary directory was missing from the default shell PATH; later it confirmed use of an absolute CLI executable path. No shell profile changes were requested by the tester.

### Sleep, natural relative-date question

Prompt: **“How was my sleep this week?”**

Muse explicitly said there was no November data and selected **April 24–30, 2026**, the latest seven demo dates. This was a disclosed demo-date substitution, not a claim about the actual current week. It did not seek permission before making that substitution.

It delivered an actual sleep overview attachment. The tester opened the image and confirmed:

- Synthetic labeling, April 24–30 dates, 7h 24m average, and 7/7 coverage.
- Stage stacks, total-duration line, dotted Garmin-need line, and an independent sleep-score panel.
- A visible layout defect: the middle x-axis dates April 26, 27, and 28 crowd together/touch in the chat-layout image.

The answer reported duration range 6h 44m–8h 05m, average score 79, separate stage/awake/need summaries, 7/7 coverage, simulated May 1 freshness, corpus version/seed, and UTC. It treated need as Garmin's estimate, separated naps, and avoided drawing a personal baseline from seven synthetic nights. It reported an unchanged archive hash.

### Steps comparison and image

Prompt: **“Using that same demo week, how did my steps compare with the week before? Please show me a chart too.”**

Muse compared **April 24–30 with April 17–23, 2026**, seven inclusive dates in each week. It delivered a daily-steps image spanning April 17–30. The tester opened the actual image: synthetic label, 7,505 steps/day, 14/14 coverage, fourteen bars, legible date labels, zero-based steps axis, and branding were visible.

The answer correctly reported **52,532 steps in each week**, mean **7,504.57 steps/day**, 7/7 available dates per week, and matching weekdays within 42 steps. It explained the synthetic sine pattern and did not present near-identical weeks as evidence of real personal stability. Freshness and corpus provenance were stated again.

### Text-only and all-missing week

Prompt: **“Text only this time: how was sleep March 12–18 in the demo? Also, are you answering through the workbench CLI in your VM or through MCP?”**

Muse returned a seven-row table, **0/7 values**, every date `not_checked`, and no image. It explained that duration, scores, stages, need and naps were unavailable, with no fetch timestamp; there was nothing to average. Missing observations were not turned into zero sleep or a trend. It explicitly confirmed CLI use and said that it had not started an MCP session or verified a client connection.

## Stages kept separate

| Stage | Result and limit |
| --- | --- |
| Package installation | Reported successful in Muse VM, charts extra present; observed downstream image delivery supports renderer availability |
| Generated archive | Reported corpus v2; outputs and selected arithmetic agree with the checked-in generator |
| CLI queries | Human-facing sleep, steps comparison, and missing-week answers passed; CLI use explicitly confirmed by Muse |
| MCP executable | Reported installed alongside CLI; no actual MCP discovery/session/query was tested |
| Image delivery | Passed in actual Muse app: attachments appeared and sleep/steps images opened as rendered images, not just file links |
| Live Garmin/key entry/sync | Deliberately not tested or authorized |
| Scheduling | Manual choice respected; existing jobs reported preserved; recurring execution not tested |
| Persistence | Reported persistent VM storage; a new-chat/restart resumption test remains open |

## Reproductions and ranked proposals

### 1. Prevent short-range chart date collisions — medium priority

**Observed:** The seven-day April sleep image has crowded consecutive middle dates; the 14-day steps image is legible. The renderer currently chooses five rounded quarter positions. For seven points this yields indexes `[0, 2, 3, 4, 6]`, putting three labels on consecutive days.

**Offline reproduction at the baseline:** Generate a new synthetic archive outside the checkout, then render its seven-day sleep overview. Both commands are offline; the destination must not already exist, and the PNG path must be new:

```sh
uv run --quiet --locked --extra charts python scripts/create_demo_archive.py /absolute/new/synthetic-demo
uv run --quiet --locked --extra charts garmin-archive --data-dir /absolute/new/synthetic-demo chart sleep --from 2026-04-24 --to 2026-04-30 --layout chat --output /absolute/new/synthetic-week.png
```

Those reproduction commands are proposed for coordinator use; the actual observed image came from Muse. The tick-index behavior was independently confirmed by reading the baseline renderer.

**Proposed change:** Choose ticks using minimum label spacing or reduce short-range tick count, while retaining inclusive endpoint dates and the gap strip. Verify rendered label bounds for seven-day chat layout and visually check both chat/wide layouts. Likely files: `src/garmin_archive/charts.py`, `tests/test_charts.py`. No renderer patch is included here.

### 2. Make the assistant's host and executable handoff visible early — medium priority

**Observed:** The initial answer said installation was complete but omitted that this was in Muse's VM. The user had to ask; persistence was only asserted, and the default PATH lacked the tool directory. Absolute CLI invocation worked in the existing chat.

**Proposed change:** Reinforce a short completion handoff naming the archive host, explicit synthetic/manual state, query path, and absolute executable/archive references. Ask or explain the execution host before a long setup, and distinguish claimed persistence from a tested new session. Keep private paths out of public compatibility reports. Likely files: `docs/SETUP.md`, `docs/ASSISTANTS.md`, `src/garmin_archive/agent_guide.md`; review `install.py`'s Muse handoff before adding anything redundant.

The docs already require host discovery and absolute paths, and the Muse handoff already produces absolute CLI commands. This finding primarily concerns assistant adherence and presentation; it is not evidence that a new Muse MCP integration is required.

### 3. Make the fixed demo date window explicit during onboarding — low priority

**Observed:** The first completion named January–April, but the next natural “this week” question needed a substitution to April. Muse handled it transparently and delivered a useful chart, with no extra coaching.

**Proposed change:** At demo setup completion, offer “latest demo week, April 24–30” as the first question and state that relative current dates have no observations. Keep production date semantics unchanged; do not shift fixture timestamps silently. Likely files: `docs/VISUALIZATION.md`, `docs/SETUP.md`, `src/garmin_archive/agent_guide.md`, or the demo generator's printed handoff. This is a clarity improvement, not a failed query.

## Verification and remaining gaps

- T3 confirmed the assigned worktree/branch; local HEAD matched the full requested baseline, with no pre-existing changes.
- The test used the actual Muse app and a fresh side conversation; no substitute coding model, extra thread, or subagent performed the test.
- Native UI inspection confirmed first-response attachments, opened sleep and steps images, and final text-only table.
- Independent arithmetic from `scripts/create_demo_archive.py` gives April 24–30 mean sleep **26,637.857 seconds** (7h 24m rounded), minimum **24,214 seconds**, maximum **29,071 seconds**, and average score **78.714**. Both compared steps weeks total **52,532**, mean **7,504.571**. The March 12–18 unchecked case is explicit in the generator.
- Muse reported 145 passing offline tests and unchanged archive hashes; this observer did not rerun that suite or independently hash the VM archive. This report-only change requires diff/privacy review, not a duplicate code test suite.
- Report verification passed: staged whitespace/diff review, referenced-file existence checks, private-path/VM-identifier checks, and independent synthetic steps/tick arithmetic. Only this sanitized report is staged; no chat dump, screenshot, runtime log, credential, or archive is included.
- Not covered: VM full revision receipt/Python version, packet-level network audit, Mac-local installation state, fresh-session persistence, real MCP discovery or image transport, unavailable-renderer fallback, partially sparse/single-night answers, wide-layout delivery, live Garmin semantics, secure key entry, or recurring execution.
- No safety reminder or installation recovery was necessary. Absolute CLI use and explicit demo-date substitution are working adaptations, not evidence of a failed first install. The chart label issue remains proposed work.

## Desktop and handoff

After the final response was observed, the CUA portion was completed with its required completion summary. Desktop/client setup access was permanently released for this turn and `DESKTOP_GRANTED` was sent to the designated Grok acceptance thread. All subsequent work was offline report writing. The coordinator receives this report and a local checkpoint commit; no push, PR, merge, or main-branch change is authorized or performed.
