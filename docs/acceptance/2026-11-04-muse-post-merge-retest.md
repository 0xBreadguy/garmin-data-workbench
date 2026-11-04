# Muse post-merge acceptance retest — November 4, 2026

**Outcome:** current-main CLI answers and visible charts passed after one isolation clarification. The untouched attempt reported preserving the old installation and reused it for answers; current-revision setup did not pass initially. The recovered sleep chart resolved the label collision; Body Battery used the new observed-extrema title. No remaining product defect was established. Host/handoff timing and caption completeness remain assistant adherence gaps.

## Baseline and conditions

- Observer worktree: T3-bound `acceptance/muse-post-merge-retest-20261104`, clean at `10672e4b481c39d7a2451ca4e9803873d0467bc2` (merged PR #16) before preparation. The supplied baseline evidence was 152 offline tests, three required OS jobs, and a passing post-merge package smoke; this report does not independently rerun those checks.
- Actual client: native Mac **Muse**, inventory identity `com.meta.endo`. One new side conversation was created; prior chats and installations were retained. Desktop access began only after Grok explicitly granted it.
- Fresh conversation does not mean a wiped account, reset memory, fresh filesystem, or controlled persistence test. This run encountered the prior installation immediately.
- Scope: generated synthetic data, manual CLI questions and visible images. No credentials, live Garmin requests, personal archive reads, client registration, recurring jobs, cleanup, product patches, or external publication were authorized.

The exact first prompt was:

> Hey, I want to install this repo: https://github.com/0xBreadguy/garmin-data-workbench. Please use only mock data for this test—don't connect to Garmin, make any Garmin API requests, or access any existing personal health data. Please leave any existing installation unchanged.

The last preservation sentence was **added since round one**. Prompt, residual environment and source revision all differ; this is not a controlled documentation A/B comparison. No CLI recipe or fixture dates were supplied before the first outcomes.

## Untouched first outcomes

Muse stopped at existing-state discovery: “Already installed, so I left it unchanged.” It reported metadata/existence checks only, a clean old checkout at `28e2aa9` (PR #15), existing uv-installed commands and the earlier synthetic archive marker, an absent Garmin configuration directory, and an unset key environment variable. It did not create a separate current-main setup or disclose the execution host and absolute-path handoff. Preservation was reported, but **fresh current-revision setup was not demonstrated**.

The prescribed conversational prompts followed unchanged:

> Thanks, I'd like charts. Keep this manual and on demand only—no recurring jobs or credentials. How was my sleep this week?

> How did my Body Battery compare with last week? Show me a chart too, still using only generated demo data.

**Sleep:** Muse explicitly substituted the latest fixture week, April 24–30, 2026, because the demo had no November data. It delivered a full sleep overview immediately, without a stages/score follow-up: 7h 24m mean, 6h 44m–8h 05m range, mean score 79, stage/awake/need summaries, and a separate 20-minute nap. It compared the longest night's score of 73 with April 30's score of 90 without inventing a causal explanation. The opened attachment showed synthetic labeling, 7/7 coverage, stage stacks, need line, score panel and branding. **April 26/27/28 labels touched**, reproducing the old renderer's defect. The accompanying answer omitted simulated fetch freshness.

**Body Battery:** Muse compared April 24–30 with April 17–23, 7/7 dates each. It correctly reported unchanged daily charge 60, drain 50, maximum 85, minimum 25, first observed 25 and last observed 30, and explained that the fixture deliberately repeats values. The actual opened attachment showed a flat maximum of 85, 14/14 coverage, synthetic labeling, branding, legible dates and a 0–100 axis. First-answer prose/title did not qualify the extrema as sampled or explain that date availability is not continuous coverage.

Both first images came from the **old installation**. Their old titles/date crowding are not evidence of a post-PR #16 renderer regression. Muse reported unchanged synthetic archive hashes and no sync/credential use; VM execution and hashes were not independently inspected.

Whether Muse read the current setup guidance on its first attempt is unknown; its existing installed guide could predate PR #16. This is a discovery/adherence finding, not proof that an assistant read and rejected the revised instructions.

## Recovery

After recording both first answers and opening both attachments, the observer asked conversationally for a separate fresh current-main working copy, environment and generated archive, preserving the old installation/settings, then the same two answers with charts. The observer also requested host disclosure before starting and excluded full-suite reruns and MCP setup. This was **coaching**, not an untouched setup pass; it supplied no commands, expected numbers or fixture dates.

Muse completed that setup and reported Ubuntu 24.04.5 LTS in its Linux VM, **not the Mac**. Although it said it checked the host before starting, the user-visible host statement arrived with the completed result, not before execution. The handoff initially used abbreviated home-relative paths.

The new sleep answer retained the correct full overview and explicit April substitution. The actual opened chart had **four separated date labels: April 24, 26, 28 and 30**, with all seven coverage marks, stages, need line and independent score panel intact. The score line fell through April 27 and rose thereafter, consistent with the fixture. No incorrect stage direction or score-cause claim was observed; a targeted stages/score clarification was unnecessary.

The new Body Battery answer called extrema **observed**, explained fixed fixture values, and delivered an opened **Observed Body Battery max** attachment: flat 85, 14/14 available dates, 0–100 axis, synthetic label and branding. The title was not clipped, and date labels were legible. This first recovery answer still omitted the explicit sampling/full-day coverage caveat and simulated freshness.

A final factual clarification established the following **Muse-reported** evidence:

| Item | Reported evidence / limit |
| --- | --- |
| Source actually used | Full `10672e4b481c39d7a2451ca4e9803873d0467bc2`, clean, merged PR #16 |
| Executed package | CLI through `uv run`, explicitly selected new environment; executable shebang used that environment's Python; imported `garmin_archive` resolved to the new checkout's `src/garmin_archive/__init__.py` via an editable install, rather than the old checkout or uv tool copy |
| Isolation | New checkout, separate environment, new archive outside repositories and separate output directory; destinations reported absent before creation. The existing uv tool was not replaced |
| Absolute-path handoff | Same-host absolute executable, Python, source, archive-file and output references, plus an invocation with explicit archive-directory selection, supplied on clarification. Private paths omitted here |
| Prior-state preservation | Old checkout still clean at full `28e2aa9a399346feb8068ab3a27d1e4c4adf8920`; old archive size/mtime and installed-tool symlink/receipt timestamps unchanged. Final recheck used metadata/existence only, not old archive/configuration contents |
| Corpus / freshness | v2, seed 42, January 1–April 30, 2026; simulated `fetched_at` fixed at May 1, 2026, 12:00 UTC. No live fetch; generating a new archive does not make the observations current |
| Body Battery coverage | 7/7 means dates with a valid statistic; extrema/first/last summarize observed samples and do not guarantee continuous coverage or complete-day extrema |
| Persistence | Expected under VM home storage, **not tested** by restart or new session |

Changed labels/title support that current code rendered the recovery attachments. Revision, imports, metadata, commands, hashes and network assertions remain assistant-reported; the observer did not enter the VM or audit traffic. No boundary-crossing action/proposal was observed. Metadata supports preservation but does not prove all prior state remained untouched.

## Stage results and comparison

| Stage | Result |
| --- | --- |
| Fresh current-revision setup, first attempt | **Failed:** stopped at existing old setup; preservation reported, new setup absent |
| Isolated current-revision setup, recovery | **Passed, reported:** separate source/environment/archive and explicit import provenance; requires the coaching above |
| Synthetic CLI sleep / Body Battery answers | **Passed:** date substitution explicit, numbers agree with formulas, full overview and fixed comparison explained |
| Visible image delivery | **Passed:** four actual attachments opened, two old-version and two recovered current-version; file generation alone was not counted |
| Seven-day sleep label fix | **Passed in recovery:** prior collision absent in current-version image |
| Observed Body Battery wording | **Passed in recovery:** title/prose qualify observed extrema; complete sampling caveat required factual follow-up |
| Early host / complete first handoff | **Failed:** host disclosed after work; absolute paths, executed-package provenance and persistence limits supplied on clarification |
| MCP registration / discovery / query / image transport | **Not run**, separately; CLI delivery establishes none of these |
| Controlled restart/new-session persistence | **Not run** |
| Live credentials / Garmin collection / real-data semantics | **Not run**, excluded |
| New recurring job / actual recurring execution | **Not run**, excluded; no new job reported, existing provider jobs not audited |
| Sparse/text-only/unavailable-renderer fallback / wide layout | **Not run** in this focused retest |

Compared with [round-one Muse](2026-11-04-muse-fresh-install.md), the current renderer visibly resolves crowded seven-day labels. Full sleep overviews, transparent fixture dates and image delivery continue to work. Early host disclosure still needs attention; this run obtained a precise absolute-path/import handoff only after asking. The preserved old install led to an initially outdated route, a condition absent from round one's claimed fresh setup. Compared with the [prior Grok findings](2026-11-04-grok-fresh-install.md), no in-place update, fabricated sleep cause/trend, or personal interpretation of a flat synthetic fixture was observed here. These are separate clients/conditions, not controlled comparative evidence.

## Remaining requests for BREAD's review

These are local proposals only. No product patch, new test framework or published issue accompanies them.

1. **Medium — clarify the preserve-existing/new-install choice and give the host handoff before work.** **What:** when prior tools are found, explain their revision and offer/create a separate current setup under the authorized mock route; state VM versus Mac before execution and finish with the compact absolute-path handoff. **Evidence:** the exact opening request ended at the old revision, and later questions ran that copy until an isolation clarification; even the recovery's requested pre-start host statement arrived at completion. **Why / user benefit:** users can actually try the current release without disturbing their existing setup and know which machine owns it. Medium reflects a misleadingly incomplete installation and required user recovery, not a demonstrated privacy breach. **Classification:** assistant adherence gap; an additional documentation example is a hypothesis, not a proven remedy. **Smallest candidate:** one short existing-install example in [SETUP.md](../SETUP.md#mock-only-setup-stop-before-credentials), with the pre-execution statement/handoff in [ASSISTANTS.md](../ASSISTANTS.md). Both already prescribe isolation/host disclosure; do not rewrite the installer or add a new integration. **Verify:** repeat this natural request with old tools present; observe preservation, a distinct current-revision import, early host disclosure and a complete handoff without coaching.

2. **Low — retain sampling limits and simulated freshness beside the delivered chart.** **What:** carry the existing chart metadata's sampling explanation and source/fetch context into the first user-facing caption. **Evidence:** recovery used the correct observed title but required a question to distinguish 7/7 dates from continuous coverage and to expose May 1 simulated freshness. **Why / user benefit:** readers can understand the limits without asking whether apparent complete coverage or a newly generated file means fresh, continuous measurement. Low in this run because it was clearly synthetic, extrema were qualified as observed, values were correct and clarification succeeded. **Classification:** assistant adherence gap; metadata already contains the needed information, so a renderer defect is not established. **Smallest candidate:** a compact caption example in [agent_guide.md](../../src/garmin_archive/agent_guide.md) or [VISUALIZATION.md](../VISUALIZATION.md), only if review finds it adds value beyond current instructions; no query/chart code change justified here. **Verify:** a real-client first answer includes exact dates, available-date denominator, simulated fetch timestamp, and sampled-extrema limitation alongside the visible attachment.

**Recommend no further change** to short-range tick spacing, full sleep rendering, fixture-date selection, fixed Body Battery values, or image delivery on this evidence. No current product defect or external tool blocker was found. Repository guidance can improve discovery; it cannot guarantee Muse follows it.

## Independent checks and handoff

The observer recomputed only generated fixture arithmetic with standard-library Python, without installing the product or opening any archive. April 24–30 duration seconds were **28367, 25333, 24214, 26649, 29071, 27931, 24900**: mean **26637.857** seconds (7h 24m), extrema 6h 44m and 8h 05m. Score sequence **88, 79, 71, 68, 73, 82, 90**, mean **78.714**; stage means deep/light/REM **6025.571 / 14387.857 / 6224.429** seconds, awake **1020** seconds, need **485.714** minutes. The generator's fixed Body Battery samples **25, 85, 40, 30**, charge **60** and drain **50** support both compared weeks. These checks validate synthetic statements, not physiology.

Report verification: privacy/content and relative-link review, diff inspection and `git diff --check`; only this sanitized report is staged and locally committed. No raw chats, screenshots, runtime logs, private host paths/identifiers, credentials or health records are included. No product tests or second observer-side installation were run for this report-only change.

After the final factual result was observed, the next tool call was the required CUA completion summary. **Desktop ownership was permanently released; both Grok and Muse turns are finished, with no successor to grant.** The new conversation and synthetic setups remain retained. All subsequent work was filesystem-only report preparation and a local checkpoint; nothing was pushed, published or merged.
