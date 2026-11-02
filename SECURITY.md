# Security and privacy

Keep keys, tokens, health records, original activity files and GPS routes out of Git, public reports and logs. Use synthetic reproductions.

## Report a vulnerability

Use private vulnerability reporting in the repository's GitHub Security tab, if available. Otherwise, open an issue requesting a private channel, without exploit details or sensitive data.

Privately provide the source revision, affected component, impact and a synthetic reproduction. Don't attach an archive or credentials. Fixes target current code unless a maintainer says otherwise; no response time or older-release support is promised.

Revoke or replace exposed credentials through Garmin. Removing a file or message doesn't revoke a key.

## Choose the host

Processes sharing your OS user can read owner-only files. Accept that access model before remote authentication or sync. Query results may reach the selected AI provider. The stdio server provides no authenticated remote connector. See [setup](docs/SETUP.md#1-choose-where-the-data-lives).
