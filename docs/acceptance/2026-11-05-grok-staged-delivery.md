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

**Passed (Grok-reported native tool receipts):** the revised verifier completed
all nine calls and 23 replacements without another copying error or source
repair. Cleanup removed the verification markers. Grok reported that full
readback matched the expected April program, including whitespace, order and
final newline. The separate data-only edge edit then compiled with one
replacement. These are native tool results reported by Grok, not an independently
retrieved remote hash.

**Passed (direct native inspection):** the January 14–18 synthetic fixture
rendered with a visible HRV gap on January 16 and missing sleep on January 17.
Selecting January 16 showed sleep **7h49m**, HRV **Unavailable / Refresh failed**,
RHR **61 bpm**, score **74** and Body Battery charge **60**. Advancing to January
17 and opening Night detail showed sleep, need, score and awake time unavailable;
the stage breakdown was unavailable rather than invented. HRV remained **40 ms**,
RHR **61 bpm** and Body Battery charge **60**. Each metric retained its own
missingness and coverage. This was inspected in the actual native Page, including
its SVG geometry, rather than inferred from the local harness.

**Passed (restoration):** the initial data-only restore compiled but its full
readback detected one extra closing character in an embedded JSON string. This
demonstrates that TypeScript compilation alone does not verify embedded data.
An explicitly authorized minimal correction removed only that mismatch. Grok
reported a complete byte match with the original April source, including its
final newline and absence of markers. Direct native inspection then confirmed
the April 17–30 chart, April 30 values and 14/14 coverage, working previous/next
selection, and **Only you** sharing again.

### Preferred machine readback

The final trial clarified a supported mechanism that was missing from the
earlier tool-contract description. Grok's native dynamic-tool bridge accepts:

```json
{
  "namespace": "cursor",
  "toolName": "ReadCanvas",
  "arguments": {"canvas_id": "<returned Page ID>"},
  "write_to_file": true
}
```

`write_to_file` is a bridge option, not a ReadCanvas argument. Grok reported that
the bridge serialized the actual saved-Page response directly into an asset file
at a tool-returned path. The response contained a title/URL header, full source,
two wrapper newlines after the source's own final newline, and a closing wrapper.
Its comparison excluded only that wrapper without trimming source whitespace.
No model-reproduced source was used. This mechanism and its byte-comparison
results are Grok-reported; native rendering and behavior were directly inspected
from this agent. No server-attested hash is claimed.

The workbench now recommends that machine comparison instead of the nine extra
verification edits when the host exposes saved response bytes. The atomic checks
remain a fallback for hosts with text-only readback. The successful nine-call
trial above remains separate evidence; it is no longer the preferred workflow.
Bounded writes still require faithful argument transfer, and readback is mandatory:
the trial caught both a compiler-rejected typo and a compiled data discrepancy.

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
