# Muse vault authentication probe — November 7, 2026

**Outcome:** an isolated dummy credential entered through Muse's native private
card produced a reported HTTP 401 through its documented shell credential
helper, matching a direct dummy control. A malformed control returned 400.
This supports a local authentication adapter using the existing vault; it is
not a working workbench integration or a real-key authentication result.

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
- The **Garmin Test Dummy** registration remains as disposable test state.
  A final review/cleanup message could not be sent after the native app stopped
  exposing a window (`noWindowsAvailable` / `cgWindowNotFound`). Do not confuse
  that registration's connected status with a live Garmin connection.
- Next step: implement and test the narrow local auth adapter, then separately
  validate real-key authentication with the user's authorization. The dummy
  probe alone does not justify advertising live Muse setup as supported.
