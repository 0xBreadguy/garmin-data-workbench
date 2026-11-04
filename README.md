```text
  G A R M I N   D A T A

  __      _____  ___ _  _____ ___ _  _  ___ _  _
  \ \    / / _ \| _ \ |/ / _ ) __| \| |/ __| || |
   \ \/\/ / (_) |   / ' <| _ \ _|| .` | (__| __ |
    \_/\_/ \___/|_|_\_|\_\___/___|_|\_|\___|_||_|
```

# Garmin Data Workbench

<img src="assets/logo.svg" alt="Two conversation bubbles joined by a data line" width="180">

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-4B6F92?style=flat-square)](https://www.python.org/)
[![SQLite archive](https://img.shields.io/badge/archive-SQLite-5C7D70?style=flat-square)](https://www.sqlite.org/)
[![MIT license](https://img.shields.io/badge/license-MIT-777777?style=flat-square)](LICENSE)

**Your Garmin data, ready for your agent or your own analysis.**

Sync health data and activities into a SQLite archive on your computer or a persistent remote workstation. Keep the source JSON and original activity files. Ask your agent questions through MCP or the CLI, or work directly with SQL, scripts, notebooks and CSV.

## Get started

**Working with an agent?** Give it this repository and ask:

> Read AGENTS.md, then help me follow docs/SETUP.md on the workstation I choose.

**Setting it up yourself?** Install Python 3.12+ and [uv](https://docs.astral.sh/uv/), then:

```sh
git clone https://github.com/0xBreadguy/garmin-data-workbench.git
cd garmin-data-workbench
uv tool install --from . garmin-data-workbench
```

Follow the [setup guide](docs/SETUP.md) to create your Garmin Personal API key and run a first sync. Guided setup supports Codex and Claude Code; other agents can use local MCP or shell commands. Built-in scheduling supports macOS; remote workstations can use an OS scheduler or provider routine.

Keep your key out of chat. On a remote workstation, processes sharing your OS user can read credentials and health data. Query results may reach your agent's AI provider. Choose the host before syncing.

## Use your archive

Ask your agent: “How did my sleep and resting heart rate change over the last week?” Or query it yourself:

```sh
garmin-archive status
garmin-archive day 2026-01-01
garmin-archive sleep --from 2026-01-01 --to 2026-01-07
garmin-archive trend sleep_duration --from 2026-01-01 --to 2026-01-07
```

Queries use stored data. Available history and fields depend on Garmin, your devices and what was recorded.

## Go deeper

- [Commands, SQL, exports and scheduling](docs/USAGE.md)
- [Assistant connections and handoffs](docs/ASSISTANTS.md)
- [Contribute](CONTRIBUTING.md) · [Agent instructions](AGENTS.md) · [Testing](docs/TESTING.md)
- [Architecture](ARCHITECTURE.md) · [Security](SECURITY.md)

Independent open-source project. Not affiliated with, endorsed by, or supported by Garmin.
