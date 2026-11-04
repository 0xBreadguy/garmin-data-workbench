# Grok mock-only installation acceptance — November 4, 2026

**Outcome:** real Grok Bot conversation successfully answered mock sleep and Body Battery questions and delivered four viewable, branded, synthetic PNG charts. **Fresh installation and preservation did not pass:** Grok reused and updated an existing clone on a VM shared by its bots; prior virtual-environment state was unknown. Interpretation needed correction. No live Garmin validation was attempted.

This records interaction through the actual Mac assistant app, not a coding-model simulation. Host filesystem actions below are Grok's reported actions; the acceptance driver did not independently access its VM or capture a network trace.

## Scope and provenance

- Assigned branch: `acceptance/grok-fresh-install-20261104`; T3 binding verified against the current thread's worktree metadata and local Git state.
- Tested main revision: `28e2aa9a399346feb8068ab3a27d1e4c4adf8920`. The driver's checkout and published-main tracking ref matched at preparation. Grok subsequently reported this same source revision from its VM and setup receipt.
- Worktree was clean before preparation. No other worker's checkout was modified.
- Desktop access began only after Muse sent `DESKTOP_GRANTED`. No subagents or new T3 threads were created.
- Client identified by native UI inventory as **Grok Bot**. Created a separate bot/conversation named **Grok Mock Acceptance Nov 4**; existing conversations were preserved.
- This was a fresh conversation, **not a wiped first-use environment**. Existing bots and prior Garmin setup were visible in the initial app inventory. No existing archive, key, registration or routine was intentionally queried or changed by this test. Grok's in-place source/environment reuse limits the broader preservation claim, as described below.
- No screenshots, raw chat dumps, private account details, credentials or personal health records are included here. An unrelated existing conversation was initially selected by the app; its contents are excluded from this report and from test inputs.

## Initial experience, before coaching

First message sent to the new test bot, verbatim:

> Hey, I want to install this repo: https://github.com/0xBreadguy/garmin-data-workbench. Please use only mock data for this test—don't connect to Garmin, make any Garmin API requests, or access any existing personal health data.

Grok acknowledged that it would clone the repository onto its own computer and use mock data without Garmin connections, API calls or personal health data. No commands, recipe or checklist were supplied with this opening request.

Its first completed response arrived about 94 seconds after the prompt. It said the command-line workbench was installed, the full suite passed, and the repository generator had created 120 fake days beginning January 1, 2026. It explicitly said it skipped live setup/sync/key commands, used a separate home directory, and made no commit or push. It attached a sleep-duration PNG without being coached to render or attach it.

The image was opened in the app's full-screen viewer. It showed January 1–30, **7h 22m**, **26/30** available nights, hours, distinct missing-data markers, a visible **SYNTHETIC DATA** label and the workbench logo. This passed actual human image delivery, rather than merely file creation.

That initial response did not explain that the clone was reused. Only later provenance questions revealed the in-place update. The opening prompt was kept verbatim as required; preservation/isolation was not supplied as an extra recipe before Grok began execution. This is a limitation of this acceptance run as well as an onboarding finding.

## Host, prior state and persistence

- **Client:** local Grok Bot Mac app, identified from native app inventory; fresh bot/conversation **Grok Mock Acceptance Nov 4**. Existing chats were retained. No T3 coding model was substituted for Grok.
- **Execution host reported by Grok:** its cloud Debian 13 Linux VM, x86_64, kernel 6.12; not the Mac. Grok stated that this VM is shared by the user's bots. A new bot therefore did not provide a fresh filesystem.
- **Source reuse:** Grok initially described cloning, then clarified: “It was partly reused, not a fully fresh install.” It fast-forwarded an existing checkout to the tested revision. It did not know who created that checkout and did not investigate other bots.
- **Environment reuse:** it ran `uv sync` in that checkout but had not recorded whether `.venv` already existed. A pre-existing environment could have been updated to the lockfile. No clean installed-wheel or isolated `uv tool` installation was demonstrated.
- **New test state:** Grok reported a new sandbox home, a new 120-day demo archive, and later a separate new 320-day archive. The initial home/archive were created inside the existing checkout, contrary to the documented outside-repository archive guidance. These untracked directories caused a dirty source receipt; Grok reported no tracked edits beyond its source update. Host paths are omitted here.
- **Preservation:** the driver made no direct installation/configuration changes, but Grok's in-place checkout update and possible environment update mean this run cannot certify preservation of the prior installation. No rollback or cleanup was attempted; that could disturb prior work. No deletion was requested or reported.
- **Persistence:** Grok initially asserted that files survive new chats/restarts on its persistent disk. Asked whether it had tested this, it clarified: “I didn't test persistence after a restart.” Treat persistence as a provider/assistant expectation, not an observed restart result. Sharing with the new test bot establishes residual state, not a controlled persistence test.
- **Reported versions:** Python 3.13.5, uv 0.13.6, workbench 0.1.0, MCP 1.30.0, Matplotlib 3.11.2, NumPy 2.5.4. The VM environment used the lockfile with the charts extra. These were assistant-reported metadata, not independent driver inspection.

## Stages and results

| Stage | Observed result | Limit |
| --- | --- | --- |
| Repository discovery and command setup | Grok found the generator and produced working CLI answers/images at the tested revision. | Existing clone and possibly existing environment reused; clean install not proven. |
| Synthetic archive creation | Reported new version-2, seed-42 archives: 120 and then 320 dates beginning January 1, 2026. | Initial demo inside checkout; not an isolated tool install. |
| CLI queries | Sleep duration, detailed sleep and Body Battery answers appeared in the human conversation. Grok reported successful `status`, `trend`, `sleep`, `body-battery` and `chart`. | No raw VM command log retained; user-visible outputs independently inspected. |
| MCP | Grok reported only checking `garmin-archive-mcp --help`. | No MCP registration, discovery, handshake, query or image transport tested. CLI success does not establish MCP success. |
| Image delivery | Four attachments opened and visually inspected: initial duration, weekly duration, Body Battery maximum, full sleep overview. | Validates Grok's app attachment path; not every host or MCP display path. |
| Read-only setup receipt | Grok reported matching revision, charts available, synthetic archives, zero FIT failures, Linux scheduler `unsupported`, assistant-query/recurrence not verified by receipt. | Receipt summary supplied after prompting, not the raw receipt artifact. Zero FIT failures is not an original-file decoding test. |
| Live collection/authentication | Deliberately not exercised. No credential request or live action was proposed in the visible test conversation. | No network trace; mock-only execution is supported by Grok's account of its actions, not independently audited. |
| Scheduling/report routine | Manual/on-demand chosen explicitly; Grok confirmed no credentials or recurring jobs. | Existing jobs were not inspected; Linux `unsupported` does not establish absence of provider routines. |
| Restart persistence | Grok ultimately acknowledged it was untested. | No restart, new-chat disk probe or provider reset performed. |

### Sleep question: first answer versus follow-up

Follow-up sent naturally:

> Thanks, I'd like charts. Keep this manual and on demand only—no recurring jobs or credentials, and keep using generated demo data. How was my sleep this week?

Grok first noted that the original demo covered January–April. Without user-supplied commands, it generated a second 320-day demo ending November 16, 2026, preserving the first. It explicitly explained the extension rather than presenting old dates as current personal data.

Its answer used **October 29–November 4, 2026 inclusive**, a rolling seven-day interpretation of “this week,” and reported **7h 30m** average, October 29 **8h 05m**, November 3 **8h 03m**, October 31 **6h 45m**, and November 1 **6h 59m**. The delivered duration chart showed **7/7** coverage and synthetic labeling. It did not initially deliver the richer stages/score overview or a separate freshness line.

A conversational request for stages and score produced a table and a full branded **Sleep overview** PNG: stacked stages, duration/need lines, independent sleep-score panel, **7/7** nights, dates, units and synthetic label. This was a successful follow-up, not the untouched first sleep answer. The dotted need estimate and wearable-estimate caveats were not explained in the accompanying prose.

The fuller answer also introduced two errors before correction:

- It attributed the November 1 score of 68 “mostly because deep sleep dropped.” The synthetic score is generated independently from the stages; this causal claim was unsupported.
- It said REM “rose over the last three nights,” while its own table showed **1h 47m → 1h 54m → 1h 52m** for November 2–4.

Asked naturally about those claims, Grok corrected both. It acknowledged that the data did not establish a cause, and described the final REM dip accurately. The correction passes conversational recovery; the initial interpretation remains a finding.

### Body Battery comparison: first answer versus clarification

Prompt:

> How did my Body Battery compare with last week? Show me a chart too, still using only the generated demo data.

Grok compared **October 22–November 4, 2026 inclusive**, reported identical values in both weeks, and explained that the fixture uses fixed daily values: **85** maximum, **25** minimum, **60** charged and **50** drained. The delivered **Body Battery maximum** chart showed a flat 85, the 0–100 axis, **14/14** available dates, synthetic label and workbench branding. It did not invent a personal trend or use percentage units.

Its initial “peaks”/“bottoms out” wording lacked the observed-sample qualification. A natural follow-up elicited the correct explanation: four synthetic readings per day; extrema describe those readings and cannot guarantee full-day extrema. No fixed-position guessing, current-level claim or fabricated recovery score was observed.

## Reproductions and independent cross-checks

The user-facing sequence above is reproducible in a fresh Grok conversation, but reproducing the shared-VM prior state would require a separately authorized environment. Do not wipe or reuse a user's live setup just to recreate it.

For the synthetic numeric/renderer cases, use a **new isolated checkout/environment** at the tested revision, install the locked charts extra, and choose nonexistent archive/output destinations outside the repo. These are offline commands; do not run `install`, `sync`, `save-key`, `setup`, or the live connection checker:

```sh
uv sync --locked --extra charts
uv run --locked --extra charts python scripts/create_demo_archive.py /absolute/new/demo-320 --days 320
uv run --locked --extra charts garmin-archive --data-dir /absolute/new/demo-320 sleep --from 2026-10-29 --to 2026-11-04
uv run --locked --extra charts garmin-archive --data-dir /absolute/new/demo-320 body-battery --from 2026-10-22 --to 2026-11-04
uv run --locked --extra charts garmin-archive --data-dir /absolute/new/demo-320 chart sleep --from 2026-10-29 --to 2026-11-04 --output /absolute/new/sleep.png
```

The driver did not run a second installation as a substitute for the assistant test. It independently recomputed the fixture's duration/score formulas using standard-library Python, without opening any archive or making network requests:

- January 1–30 valid sleep mean: **26,490.15 seconds**, 26 available nights → **7h 22m**, matching the initial image. Masked dates were January 4, 8, 12 and 17.
- October 29–November 4 duration seconds: **29123, 26889, 24290, 25134, 28184, 28972, 26344**. Mean **26,990.86 seconds** → **7h 30m**; cited rounded nightly durations match.
- Same-week score sequence: **91, 84, 74, 68, 70, 77, 86**; average **78.57** → about 79, matching the detailed answer.
- Source inspection confirms fixed Body Battery readings **25, 85, 40, 30**, daily charge 60 and drain 50. These support the reported comparison and the later sample caveat.

## Proposed repository changes

These are coordinator-review proposals, not implemented patches. More guidance can reduce these failure modes; it cannot guarantee a third-party assistant follows it.

1. **High — make mock setup isolation explicit before modifying a reused host.** Put a short mock-only branch near the top of [SETUP.md](../SETUP.md): discover existing code/environment by metadata only, use a new dedicated checkout/environment and outside-repo demo directory, preserve installed tools/registrations, and report reuse honestly. Add the matching pointer to [AGENTS.md](../../AGENTS.md). Reproduction: a fresh Grok bot shares an existing clone; the natural install request led to `pull`/`uv sync` in place. A separate sandbox home protected default-path access according to Grok, but did not isolate the source/environment. No privacy breach was observed; preservation was not established.
2. **High — reinforce evidence limits in sleep interpretation and demo provenance.** Add a concise counterexample to [agent_guide.md](../../src/garmin_archive/agent_guide.md) and [SLEEP.md](../SLEEP.md): a low overall score plus low deep sleep does not reveal the score's cause; check the actual sequence before asserting a rising trend. Make the demo's independent score/stage generation explicit in [VISUALIZATION.md](../VISUALIZATION.md) and the generator/manifest notes. Reproduction: the stages/score follow-up produced both an unsupported cause and a contradicted REM trend, later corrected conversationally. Existing guidance already cautions against causal conclusions; this is an adherence gap as well as a documentation opportunity.
3. **Medium — surface “observed” Body Battery semantics in chart-facing metadata.** Consider “Observed Body Battery maximum/minimum” in [queries.py](../../src/garmin_archive/queries.py) titles and a specific sample-coverage explanation in [chart_delivery.py](../../src/garmin_archive/chart_delivery.py), retaining the notes already present in [body_battery.py](../../src/garmin_archive/body_battery.py). Reproduction: chart/prose used unqualified daily extrema until asked about whole-day coverage. Preserve the 0–100 scale and avoid cluttering the plot.
4. **Medium — improve discovery of the full sleep overview and its caption contract.** Have the demo generator print a `sleep`/`chart sleep` example, rather than only `chart sleep_duration`, and cross-link the installed guide prominently. Likely files: [create_demo_archive.py](../../scripts/create_demo_archive.py), [SETUP.md](../SETUP.md), [agent_guide.md](../../src/garmin_archive/agent_guide.md). Reproduction: the first broad sleep answer was duration-only; a follow-up successfully delivered the richer existing renderer. Existing caption metadata already provides coverage, freshness and need-line explanations, but Grok did not carry all of them into its reply.
5. **Low — make demo-date and comparison limits clearer.** Explain how to select a fixture week or safely create a separate longer corpus, and note that fixed Body Battery values intentionally cannot demonstrate a changing week-to-week trend. Likely files: [VISUALIZATION.md](../VISUALIZATION.md), [create_demo_archive.py](../../scripts/create_demo_archive.py), [test_demo_provenance.py](../../tests/test_demo_provenance.py). Preserve v2 known answers; any variable-Body-Battery corpus should be a deliberate new version or scenario. Grok worked around the date mismatch successfully without coaching; this was friction, not a blocker.

## Verification and remaining gaps

**Observed directly:** actual app identity; fresh conversation and exact first prompt; subsequent user-visible answers; four opened chart attachments and their labels/layout; conversational corrections; final admission of reuse and untested persistence.

**Reported by Grok:** 145 offline tests passed (it said it reran the full suite when asked for provenance); CLI checks passed; version/OS/receipt metadata; fresh demo/home directories; skipped live actions and credentials. The driver checked that this revision contains 145 named test methods, but did not receive VM test stdout or independently rerun the suite. This report-only change does not warrant another full suite.

**Driver checks:** T3 binding, clean starting checkout, correct branch/revision, independent synthetic arithmetic, relevant source/doc inspection, report-relative links, report content review and `git diff --check`. Only this sanitized report is committed; no product code, raw chat dump, screenshot, health data, environment state or credential is included.

**Remaining gaps:** fully isolated fresh install; preservation of prior VM environment; restart/new-chat persistence; MCP end-to-end use; live authentication/collection and comparison with Garmin Connect; actual recurring execution. Live stages were intentionally excluded, not failed.

**Desktop handoff:** Muse granted access before testing. After the final Grok outcome was observed, the driver sent the required CUA completion summary and permanently released desktop access to Dot with `DESKTOP_GRANTED`. No desktop actions were taken after that handoff. The test bot and synthetic setup were retained; no further cleanup or execution is pending from Grok.
