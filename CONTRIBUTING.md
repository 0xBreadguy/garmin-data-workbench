# Contributing to Garmin Data Workbench

Thanks for helping make personal Garmin data more useful and accessible. This is an independent, community-built project for people who want to own and query their data locally.

## Ways to help

- Report a reproducible bug or improve setup and troubleshooting documentation.
- Add support for a Garmin Personal API dataset or improve FIT decoding and data coverage.
- Improve queries, exports, sync recovery or tests.
- Help design a local MCP interface or share an analysis workflow.

For larger changes, start with an issue describing the problem and proposed direction so contributors can coordinate before writing a lot of code.

## Develop locally

Install Python 3.12+ and [uv](https://docs.astral.sh/uv/), then from the repository:

```sh
uv sync
uv run python -m unittest discover -s tests -v
```

The tests use generated FIT data and fake Garmin responses, so they do not require a Garmin account or an API key. The [README](README.md) documents the optional live connection for your own use.

Keep changes focused, add meaningful offline tests for affected behavior, and document any new commands, datasets or limitations. The project stores user data outside the checkout by default; please preserve that behavior.

## Protect personal data

Do not include API keys, tokens, activity files, real Garmin exports, health measurements, GPS routes or unredacted API responses in issues, pull requests, fixtures or logs. Use synthetic examples and remove identifying details from reports. If a bug involves sensitive data, describe the behavior without uploading it.

The project is independent and is not affiliated with Garmin. Data access and features can differ by account and device; report the behavior you observed without assuming every device works the same way.
