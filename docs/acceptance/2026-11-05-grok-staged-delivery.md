# Bounded Grok delivery trial — November 5, 2026

## Scope and result

The actual packaged recovery explorer rendered in the native Mac Grok Bot app
through bounded `WriteCanvas` / `EditCanvas` calls. This follows the
[failed one-call transfer](2026-11-05-grok-packaged-explorer.md); it does not
change that earlier result. The user requested reliable delivery before a later
design pass. The visual components stayed unchanged apart from transport decoding.

The existing conversation was reused. Every new observation and Page in this
trial was synthetic. Personal Pages, archives, credentials, installed environments
and scheduled jobs were preserved. The new Page's Share menu directly showed
**Only you**. There was no push, merge or public sharing.

## Implementation

`widget sleep-recovery --host grok --handoff-dir /absolute/new/directory`
creates the source and an optional private handoff bundle. It contains an ordered
plan, bounded JSON argument files, expected source identity and separate source
verification calls. Python generates instructions; the assistant executes native
tools. No Crumb harness extension, undocumented endpoint or production dependency
is involved.

The versioned string/tuple codec retains every field consumed by the renderer:
exact dates, provenance, nulls, zeroes, statuses, source times, all four stages,
completeness, comparison values, independent coverage, freshness and warnings.
It performs no metric calculations. Inert strings are joined before JSON parsing,
so even a split inside an escape sequence preserves the value. The renderer still
uses the shared Python snapshot and comparisons.

The tested 14-day source was 32,103 UTF-8 bytes. Its expected input SHA-256 was
`853e0fda500a81b9e61f5c019be44f5b5ea4f6a1c5411ef79a106a7a44f72680`.
It required ten delivery calls. The conservative 12,000-byte argument budget,
including reserved Page ID space, is a project guardrail, not a vendor limit.
Larger snapshots add bounded data declarations rather than a larger single call.
Every step must succeed before the next; the final edit activates the App.

## Native evidence

Grok reported ten successful native compilations, one replacement per delivery
edit, no skipped or repaired source, and full `ReadCanvas` inspection with no
content disagreement. Native inspection directly confirmed the delivered Page,
its synthetic April 17–30 inclusive range and the following interactions:

| Check | Directly observed result |
| --- | --- |
| Initial April 30 | Sleep 6h55m, need 7h55m, HRV 56 ms, RHR 60 bpm, score 90, Body Battery charge 60 |
| Linked selection and Left key | April 23 selected across all five lanes: sleep 8h01m, HRV 49 ms, RHR 58 bpm, score 92, charge 60 |
| Last 7 and Night detail | Selection clamped to April 24; sleep 7h53m, need 7h50m, deep 1h56m, light 4h09m, REM 1h47m, unclassified 0 |
| Compare | April 17–23 versus April 24–30, each metric 7/7 coverage; sleep 7h27m vs 7h24m, HRV 49.7 vs 47, RHR 58.3 vs 58, score 79 vs 78.7, charge 60 vs 60 |
| Privacy | Native Share menu: Only you |

### Source verification contract

An identical old/new edit is rejected as `no_change`; it does not prove a match.
A native probe established that ordered atomic edits can change a fragment,
restore it, then change only a temporary trailing comment before compilation.
The first verifier repeated every source fragment four times. Grok mistyped one
replacement as `nconst`; compilation rejected it and retained the published
revision. An explicit retry compiled but added an underscore to the temporary
comment. Readback caught that discrepancy and the sequence stopped. An explicit
cleanup removed that comment only and restored the original April program.
Neither attempt counts as complete verification.

The revised verifier replaces each fragment with a unique temporary slot, then
restores it in the same atomic batch before advancing the comment. This copies
each fragment twice, reducing the 14-day verification from sixteen calls to nine:
setup, seven overlapping fragment batches and cleanup. Each final compiled
program differs only in its trailing comment, which cleanup removes.

Full `ReadCanvas` comparison remains necessary to exclude extra or reordered
source. The tool returns text with a wrapper and supplies no machine-readable
source hash. Input hashes and locally reconstructed hashes are not remote hash
receipts. Tool-reported matches, assistant readback inspection and observed UI
behavior are separate evidence.

**Pending:** the nine-call verifier's final native result, the independent
failed-HRV/missing-sleep case and final restoration. The revised sequence was
submitted, but native control returned `cgWindowNotFound` before its result could
be inspected. These checks are not passed by the local harness results below.

## Local verification

- **Passed:** 206 offline tests after transport, handoff and CLI implementation.
- **Passed:** 24 focused Grok tests after final delivery-guidance wording.
- **Passed:** 194 packaged-decoder and static-render equivalence assertions against
  independently specified canonical fields, in both themes and all views.
- **Passed:** 72 browser assertions through the optional local React shim, including
  gaps, failed fields, valid zeroes, incomplete stages, keyboard/focus, drag and
  emulated touch. This shim is not Grok's SDK.
- **Passed:** build and installed-wheel smoke checks in base and charts modes.
- **Passed:** local 2/14/90-day source reconstruction, bounded verification and
  ID binding, private exclusive writes, collision/link refusal and incomplete
  manifest handling.

The native trial is on macOS only. Physical-phone touch, native mobile delivery,
restart persistence, cross-device state and Windows/Linux native integration
remain untested. The snapshot does not refresh itself; selection uses local
React state. A design and copy pass remains separate from functional acceptance.
