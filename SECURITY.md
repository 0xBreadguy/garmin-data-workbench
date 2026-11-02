# Security and privacy

Garmin Data Workbench handles credentials, health data and activity files that can contain precise locations. Keep those materials out of issues, pull requests, logs and public test fixtures. Use synthetic data to reproduce a problem whenever possible.

## Report a vulnerability

Use GitHub's private vulnerability reporting option in this repository's Security tab if it is available. If no private reporting option is offered, open an issue asking for a private reporting channel without including exploit details or sensitive data. Do not attach a personal archive, API key, token cache, raw Garmin response or original activity file.

Describe the affected source revision, the component, impact and a synthetic reproduction through the private channel. This is an early project; there is no promised response time or maintained older-release support policy. Fixes target the current code unless a maintainer says otherwise.

If a credential has been exposed, revoke or replace it through Garmin and remove it from the affected environment. Removing a file or message alone doesn't revoke a key. Do not post the exposed value in a report.

## Deployment choices

The [setup guide](docs/SETUP.md) explains local and cloud host choices. Owner-only permissions do not isolate data from other agents running as the same operating-system user. Users choose whether that access model is acceptable before syncing. Tool results may pass to the chosen AI provider. The shipped stdio server is not a configured authenticated remote connector.
