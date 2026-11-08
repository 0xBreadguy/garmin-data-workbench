# Muse vault authentication probe — November 7, 2026

**Outcome:** an isolated dummy credential entered through Muse's native private
card produced a reported HTTP 401 through its documented shell credential
helper, matching a direct dummy control. A malformed control returned 400.
This supports a local authentication adapter using the existing vault; it is
not a working workbench integration or a real-key authentication result.
A resumed raw-key experiment failed when the adapter added the prefix locally,
while the complete-header positive control continued to return 401. Automatic
prefix handling is not established by the tested Muse interfaces.

## Scope and evidence

BREAD requested a direct conversation with Muse to find a simpler connection
without a new service. The observer used Muse's native macOS app to converse
with its assistant and complete one explicitly dummy-only card. The assistant
reported running the probes in its Linux VM. Its exact checkout revision was
not captured. No workbench implementation changed during this investigation.

Directly observed in the app:

- Muse created a separate `custom.garmin-test-dummy` registration, labelled
  **Garmin Test Dummy**, with a private-entry card.
- The observer entered a public synthetic value containing `ApiKey ` followed
  by a known dummy string. The form accepted it, including the prefix.
- Muse reported the bounded probe results below in the conversation.

The helper contracts, host restrictions, registration isolation and HTTP
execution are **Muse-reported evidence**, not independently audited VM or
network traces. No real credential value was requested or entered by the
observer. Muse was instructed to reference only the dummy provider, discard
response bodies, print statuses only, disable redirects, and make one request
per arm with a 15-second timeout. No sync or health queries were authorized.

## Findings that correct the earlier brief

Muse reported reading its connector setup skill, `dynamic_credentials.py`,
connector templates and the existing Garmin connector metadata:

- The documented custom-connector pattern is callable from a shell process:
  obtain a surrogate, enforce the registered destination, and use
  `add_surrogate_to_request()` with a `urllib.request.Request`.
- `custom_header:Authorization` places the surrogate as the complete header
  value. No inspected schema prohibited storing a complete authorization
  value containing a scheme and space.
- The earlier echo probe used an **unregistered host**. It could not establish
  that shell requests categorically fail to receive substitution.
- Earlier Garmin 400 responses also did not establish non-substitution:
  a substituted bare key would still lack the required authorization scheme.
- The duplicate-prefix objection applies to feeding a complete header into
  the normal SDK key path. A dedicated exchange using the helper's complete
  header placement would not prepend `ApiKey ` again.

## Reported probe results

Destination: Garmin's Personal API token endpoint on
`personal.connectapi.garmin.com`. The dummy registration used
`custom_header:Authorization`; the real Garmin registration was excluded.

| Arm | Reported result |
| --- | --- |
| Direct public dummy with `ApiKey ` prefix | HTTP 401 |
| Documented helper, whole-header surrogate for the isolated dummy | HTTP 401 |
| Malformed public dummy without the prefix | HTTP 400 |

These controls support usable authorization formatting through the vault route.
They do not reveal the exact substituted bytes, prove successful authentication,
or establish every client's routing behavior. Whole-value substitution with no
substring substitution is a hypothesis consistent with the observed outcomes,
not a verified platform specification.

## Candidate implementation and intended user flow

The candidate is a local adapter, with no hosted service or listening process:

1. Request a native private-entry card for the complete authorization value:
   `ApiKey ` followed by the user's key. Adding the prefix automatically is
   not an established card capability.
2. Use the documented helper's whole-header placement for the token exchange.
3. Keep the bearer token inside the sync process and pass it to
   `GarminPersonalApiClient`; never return it in model/tool output.
4. Reacquire through the vault on later runs. Define bounded expiry/error
   handling rather than unbounded retries.

Implementation must cover setup readiness (`ensure_key`) as well as sync token
acquisition. The existing SDK environment/file route remains a separate path;
a complete header must not be treated as its raw API key. Host-specific helper
availability needs an explicit capability check. Token lifetime, scheduling,
failure handling and any caching policy still require design and tests.

## Limits and remaining state

- No adapter, installer integration, real-key authentication, successful sync,
  unattended execution or Android interaction was verified in this probe.
- No real Garmin credential, archive, schedule or sealed-handoff prototype was
  intentionally changed. Preservation inside the VM remains assistant-reported.
- The **Garmin Test Dummy** and **Garmin Test Raw** registrations remain as
  disposable test state. Initial cleanup was blocked by window access; the
  resumed investigation performed only the raw-key test below. Do not confuse
  either registration's connected status with a live Garmin connection.
- A candidate adapter must use the tested complete-header stored value;
  raw-key-only entry requires another supported prefix mechanism. Real-key
  validation remains separate and needs the user's authorization. The dummy
  probes alone do not justify advertising live Muse setup as supported.

## Follow-up: automatic prefix handling

BREAD asked whether the integration could add `ApiKey ` so users enter only
their raw key. The observer inspected the installed application's shipped
`Contents/Resources/hatch/index.html`, without accessing user settings,
credentials, sessions or conversations through filesystem APIs.

Inspected application: Muse 11.1, build `1109246656`. The HTML bundle SHA-256
was `309ba1eb17d775f951f6bbabb72caf4db2212b18b9c6bf0023ffad67289e7095`.
This is evidence about this desktop build, not Android or future releases.

- `useApiKeyConnect` trims the entered string and calls
  `submitApiKeyConnection` with that value.
- The dynamic-credential request builder forwards entry name, type, placement
  and the trimmed value. It does not use an entry prefix/transform parameter.
- The custom API-key connector request builder also forwards the trimmed key.
  Its token-placement specification is forwarded separately; this inspection
  does not establish undocumented server behavior for extra placement fields.

An offline Node check of the two extracted, unmodified request-builder
functions with public dummy input confirmed that both forward the value
unchanged apart from trimming. A synthetic `prefix` property on a dynamic
credential entry was not forwarded. The check made zero network requests and
did not register credentials. No shipped application files were changed.

**Source-inspection conclusion:** adding a prefix during entry is not implemented
by the inspected native form path. A repository change cannot assume that form
will transform a raw key. The initial complete-header probe did not test a raw
dummy stored in the vault with the prefix added by the adapter.

That independent test could not be completed in this follow-up: native app
access returned `cgWindowNotFound`, and two browser snapshot attempts returned
`Preview automation snapshot timed out after 15000ms`. The observer closed
the newly opened browser tab. No new credential registrations or live requests
were made during that blocked attempt. The user subsequently unlocked the Mac,
allowing the controlled follow-up below.

## Resumed raw-key experiment

Muse prepared a separate **Garmin Test Raw** card under
`custom.garmin-test-raw`, reportedly restricted to the same Garmin host and
`custom_header:Authorization`. The observer entered only the same public dummy
string, without `ApiKey `. The native form accepted it. On card submission,
Muse reported automatically running the four previously specified dummy-only
probes; no further confirmation message was sent. Real credentials, the real
registration, health queries and sync were excluded from the instructions.

Muse reported confirming the two dummy providers' placement before executing
one token POST per arm, with 15-second timeouts, no redirects, bodies discarded
and status-only output:

| Arm | Reported result |
| --- | --- |
| Direct `ApiKey ` plus public dummy | HTTP 401 |
| Locally added `ApiKey ` plus raw-provider surrogate | HTTP 400 |
| Raw-provider surrogate as the complete header, using the helper | HTTP 400 |
| Complete-header dummy provider using the helper | HTTP 401 |

This settles the proposed request construction for this tested configuration:
adding the prefix locally to a raw-value surrogate did not reproduce the
complete-header route. It supports whole-value matching as an explanation,
but neither the HTTP statuses nor the source inspection prove the internal
substitution algorithm. A defect specific to the raw registration is a residual
alternative; stored values were not read back. No real authentication succeeded
or was attempted by this experiment.

Muse also reported rechecking its documented registration schema, connector
skill and helper: no custom authorization-scheme or prefix/template option was
found. URL-path substitution is documented, but does not construct an
authorization header. Extra fields accepted by a permissive frontend parser
are not evidence of a supported server capability.

**Practical result:** the tested existing route needs the complete authorization
value entered privately. To let users enter only the raw key, Muse would need
to expose a supported entry transform or custom authorization-scheme/template
mechanism, or another independently verified supported route would need to be
found. Merely hardcoding `ApiKey ` in workbench Python did not solve it.
