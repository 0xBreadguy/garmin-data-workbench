# Grok post-merge acceptance retest — November 4, 2026

**Mixed result:** Grok reported a separate working checkout/environment at merged PR #16, retained the old installation, and delivered three viewable synthetic charts. Seven-day sleep labels are now readable. The first natural sleep question produced no new answer/chart; recovery needed a demo-week clarification. The detailed sleep reply then misstated its average, and Body Battery prose still overstated sampled extrema until challenged. No product patch or external submission is included.

## Baseline, client and evidence limits

| Item | Evidence |
| --- | --- |
| Observer baseline | `10672e4b481c39d7a2451ca4e9803873d0467bc2`, merged PR #16; clean starting branch `acceptance/grok-post-merge-retest-20261104`; T3 worktree binding confirmed |
| Actual client | Native Mac **Grok Bot**, inventory bundle identity `com.anysphere.sand`; one new bot/conversation, existing bots/chats retained |
| Execution host | Grok reported its Debian GNU/Linux 13 VM, x86_64, kernel 6.12.94, Python 3.13.5; commands/archive were not on the Mac |
| Source actually used | Grok reported the full baseline SHA above, package 0.1.0, and a new dedicated environment's absolute `env/bin/garmin-archive` for every answer/chart; the older global executable remained separate |
| Freshness | Fresh conversation and reportedly new checkout/environment/archive; residual account, bots and VM state remained. Neither a wiped account nor controlled persistence was demonstrated |
| Query route | Grok explicitly confirmed CLI only; no MCP server started or connected |

Direct observations cover app identity, sent prompts, visible replies, and opening the actual image attachments. VM commands, installation provenance, filesystem metadata, isolation measures and test results are **Grok-reported**, not independently observed execution. No installed-build/import-location receipt or VM terminal transcript was captured. The observer did not install another local copy or rerun product tests. Baseline evidence supplied with the assignment was 152 offline tests, three passing OS jobs and passing post-merge package smoke; this pass does not independently re-establish those checks.

## Untouched first outcome and preservation

The first user message was exactly:

> Hey, I want to install this repo: https://github.com/0xBreadguy/garmin-data-workbench. Please use only mock data for this test—don't connect to Garmin, make any Garmin API requests, or access any existing personal health data. Please leave any existing installation unchanged.

The last sentence is **new compared with [round one](2026-11-04-grok-fresh-install.md)**. No commands, expected answers, fixture dates or setup recipe were preloaded. This is not a controlled documentation-only A/B comparison.

About 112 seconds later, Grok reported a new checkout at `10672e4`, a January–April synthetic archive, successful `status`/`sleep`, a rendered chart and a passing full suite. The suite was Grok's own choice, not an observer-requested substitute for acceptance; no count/stdout was captured. It reported a cleared environment, separate fake home and dead proxy for mock execution. These claims do not constitute a network audit.

The first attachment was opened: **Sleep overview, April 24–30, 2026; 7h 24m; 7/7 nights**, stage stacks, duration/need lines, independent 0–100 score panel, synthetic label and branding. Date ticks **April 24, 26, 28, 30** were clearly separated. No workaround preceded this first result.

Later bounded provenance questions established, according to Grok:

- The checkout, environment and archive were new, and all queries used the new environment rather than the older globally installed package. Absolute executable and archive-directory references usable on that VM were supplied in the private conversation; private paths are omitted here.
- The demo and fake home were **inside the new checkout**, leaving an untracked `mockroot/` directory. No tracked files changed. Thus separate working code/environment was reported, but the [outside-repository archive requirement](../SETUP.md#mock-only-setup-stop-before-credentials) was not met.
- Prior discovery checked existence, file types, timestamps/link targets and the older checkout revision (`28e2aa9`): old checkout/environment, earlier demo, default config/archive locations and global CLI/MCP links remained. Grok reported no private data/config/job-body reads, in-place update, forced tool reinstall, removal or cleanup.
- Reported old timestamps predated this test, but there was **no pre-action snapshot**. This supports preservation without proving unchanged contents. No observer VM inspection, rollback or cleanup was attempted.
- Persistence was explicitly **expected, not tested** across a new session/restart. No new job, credential or MCP registration was reported. This does not establish absence of pre-existing jobs/provider routines.

No unsafe action was visibly proposed that required interruption. No key, token/config contents, existing health archive or GPS data was requested by the observer. Only synthetic fixtures were used in the observed answers. Grok said it did not authenticate or use live/setup commands; forbidden-command execution and network traffic were not independently audited. No setup receipt was requested or reported in this retest.

## First answers versus conversational recovery

### Sleep

Prescribed next prompt:

> Thanks, I'd like charts. Keep this manual and on demand only—no recurring jobs or credentials. How was my sleep this week?

**First answer: failed useful demo sleep answer/delivery for this turn.** Grok correctly said the archive stopped in April and could not describe actual current-week sleep. It offered to chart a supplied mock range and referred to the earlier image, but selected no explicit fixture week, supplied no sleep overview and attached no new image. It mentioned that a real answer would require real access; it did not attempt or request credentials. The privacy boundary held, but the demo conversation stalled.

After the prescribed Body Battery question below, a natural clarification asked for the latest demo sleep week, stages/score, changes during that week, and whether the battery extrema covered a whole day. No dates, commands or expected numbers were supplied.

**Recovery: image delivery passed; interpretation initially mixed.** Grok selected April 24–30 and attached another full sleep overview. It was opened and showed the same correct **7h 24m, 7/7** result, stages, need line, independent score axis and readable labels. The prose instead said **7h 10m** average. It correctly described score falling **88 → 68 on April 27 → 90 on April 30**, nightly duration extrema and stage ranges. Its stress comparison also incorrectly placed every other night at 10–19; April 27 is 22.

A natural question about the text/chart discrepancy and association versus explanation produced an explicit correction to **7h 24m**, about **79** average score, and acknowledgement that co-occurring stages/stress do not explain the score. It also then identified April 27 stress as 22. Unlike round one, there was no explicit claim that deep sleep caused most of a score reduction, nor a contradicted claim of monotonically rising REM. However, no comparable dated REM-direction assertion was made, so that specific prior error is not proven fixed. The accompanying replies omitted a simulated-fetch freshness line and explanation of the dotted need estimate. Those remain presentation adherence gaps, despite visible chart coverage and synthetic labeling.

### Body Battery

Prescribed prompt, sent immediately after the untouched sleep answer:

> How did my Body Battery compare with last week? Show me a chart too, still using only generated demo data.

**First answer: comparison/image passed; sample qualification failed.** Grok transparently substituted **April 24–30 versus April 17–23, 2026**, correctly reported identical generated values in both periods, and explained that the flat fixture says nothing about the user. It gave 25 minimum, 85 maximum, 60 charged and 50 drained, but called them daily bottoms/peaks without qualifying sample coverage.

The actual attachment was opened: **Observed Body Battery max**, April 17–30, **85.0**, **14/14 available dates**, flat line, fixed 0–100 scale, readable dates, synthetic label and branding. The changed title worked; the prose and attachment description still used unqualified daily-peak language. No invented changing trend or percentage unit was observed.

**Recovery: qualification passed.** Asked naturally about whole-day coverage, Grok acknowledged that four readings per day establish only observed minimum/maximum, cannot rule out higher/lower levels between readings, and that its earlier wording overstated the result. Available dates were not then treated as continuous coverage. No new corpus or installation change was needed.

## Independent checks and separate stages

Minimal standard-library arithmetic reproduced the generator formulas and seed-42 random draws without creating/querying any archive. For April 24–30, duration seconds are **28367, 25333, 24214, 26649, 29071, 27931, 24900**: mean **26637.857 seconds**, rounded **7h 24m**. Scores are **88, 79, 71, 68, 73, 82, 90**, mean **78.714**. Stage ranges agree with Grok's rounded ranges; source inspection confirms four daily Body Battery levels **25, 85, 40, 30**, charged 60/drained 50 throughout both comparison weeks. These dates have no deliberate missing-data cases. The generator fixes simulated fetch time at May 1, 2026; it is not live freshness.

| Stage | Result |
| --- | --- |
| Separate working installation | **Passed as reported** for new checkout/environment at baseline; no independent VM build inspection |
| Full documented mock isolation | **Failed**: synthetic archive inside checkout; prior-content preservation remains limited by metadata-only evidence/no before snapshot |
| Synthetic CLI answers | **Passed after recovery**, with first sleep dead end and later arithmetic error retained above |
| Visible image delivery | **Passed**, three actual attachments opened; first and recovered sleep overviews and Body Battery comparison |
| Seven-day label readability | **Passed** in actual Grok image viewer; no prior collision reproduced |
| First-answer sampled-extrema caveat | **Failed**, corrected only after clarification |
| MCP registration / discovery / query / image transport | **Not run**, separately; CLI attachments establish none of these |
| Controlled persistence / recurring execution | **Not run**; manual choice respected, persistence expectation qualified |
| Live Garmin / credentials / real data / packet audit | **Not run**, intentionally excluded |
| Text-only, sparse/all-missing, unavailable renderer, wide layout | **Not run**, outside this focused pass |

## Remaining requests for BREAD's review

These are local proposals, not implemented changes or GitHub issues. No high-severity product defect or external-tool access blocker was established.

1. **Medium — keep prose numerically consistent with the query/chart.** **What:** explicitly direct assistants to reuse returned aggregates and check prose against the delivered chart; retain coverage/simulated freshness alongside the answer. **Evidence:** detailed demo sleep answer said 7h 10m versus correct image/formula 7h 24m, and misstated the stress range; correction required another user question. **Why/benefit:** conflicting summaries undermine trust and require users to audit arithmetic. **Classification:** assistant adherence/arithmetic gap; no query/renderer calculation defect observed. **Smallest likely change:** a short aggregate-consistency instruction in [agent_guide.md](../../src/garmin_archive/agent_guide.md); existing freshness policy already suffices. **Verify:** another authorized natural assistant answer agrees with returned mean, nightly values and image, with dates/coverage/freshness; no new framework needed.

2. **Medium — carry sample limits through CLI image delivery.** **What:** consider a compact on-image sample-limit note for Body Battery levels, or a concise CLI-facing caption that accompanies PNG output. **Evidence:** the new “Observed” title appeared, yet Grok again described full-day peaks/bottoms until questioned. **Why/benefit:** readers should understand that 14/14 dates are not continuous coverage without discovering the caveat themselves. **Classification:** recurring assistant adherence gap; a defensive presentation enhancement is a hypothesis, not proof of missing parser semantics. [Body Battery guidance](../BODY_BATTERY.md) and [caption metadata](../../src/garmin_archive/chart_delivery.py) already contain the limits. **Smallest likely change:** [charts.py](../../src/garmin_archive/charts.py) and existing [chart tests](../../tests/test_charts.py), or CLI caption plumbing in [cli.py](../../src/garmin_archive/cli.py), choosing one route after review. This would be a narrow exception to the current preference for explanatory prose outside images. **Verify:** first-answer caveat in actual CLI-based assistant delivery, readable chat layout, preserved 0–100 axis and date counts.

3. **Medium — make a safe demo fallback explicit for relative-date questions.** **What:** clarify that, during mock-only use, an out-of-window “this week” question can continue with a clearly announced latest fixture week (or one concise choice), without suggesting live access as the way forward. **Evidence:** the first sleep question stalled, while the next Body Battery question selected fixture dates successfully. **Why/benefit:** users can try the intended chart flow without knowing fixture dates or repeating the request. **Classification:** assistant adherence gap/documentation hypothesis, not a date-query defect. **Smallest likely change:** one sentence in [agent_guide.md](../../src/garmin_archive/agent_guide.md) or [SETUP.md](../SETUP.md); the generator already prints dates and example questions, so no generator change is presently justified. **Verify:** the same natural prompt yields a disclosed demo-week answer/chart or an actionable choice, retaining the mock boundary.

4. **Low — enforce the existing mock layout and completion handoff; no new product patch recommended.** **What:** retain outside-checkout demo storage and early host/absolute-path disclosure as acceptance requirements. **Evidence:** new source/environment avoided round-one reuse, but archive/home remained inside the checkout; OS, absolute executable and persistence limits appeared only after the final factual question. **Why/benefit:** separate data avoids source dirtiness and accidental staging, while host/path clarity makes the next on-demand query usable. Impact here was limited to a new synthetic checkout, with no observed old-install modification. **Classification:** assistant adherence gap; [SETUP.md](../SETUP.md#hand-off) and [ASSISTANTS.md](../ASSISTANTS.md) already give concrete instructions. **Smallest likely files:** none now; avoid duplicating the existing recipe. **Verify:** future authorized acceptance reports new absent destinations, outside-repository archive, preserved prior state, actual executable/host and expected-versus-tested persistence in its first completion.

No further tick-layout or sleep-causality patch is recommended from this run: labels were readable and the prior explicit causal claim did not recur. Stronger prompts, different selected fixture dates and residual assistant context prevent attributing all differences to PR #16.

## Report verification and desktop release

The observer reviewed source formulas, relevant guidance, report privacy/relative links, the report diff and `git diff --check`. Only this sanitized report is committed locally; no raw chat, screenshot, runtime log, private host path/identifier, account detail, archive or product change is included. Report-only work did not rerun tests or install software.

After the final provenance response, the very next tool call was the required CUA completion summary. Desktop ownership was permanently released and `DESKTOP_GRANTED` sent immediately to the designated Muse successor before report writing. All subsequent work was offline report preparation/local Git work, followed by the authorized coordinator handoff. No push, PR, merge, issue, extra thread/subagent or monitoring was performed.
