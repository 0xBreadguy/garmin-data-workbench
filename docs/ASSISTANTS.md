# Connect your assistant

Run [setup](SETUP.md) on the archive host first. Agents can query through a shell or local stdio MCP. An agent coordinating from elsewhere also needs a supported connection to that host.

Before setup, say where commands and the archive will run: a desktop chat app may execute in a separate VM, and a fresh conversation may share prior installations. For mock requests, use the [isolated mock-only route](SETUP.md#mock-only-setup-stop-before-credentials), preserving existing tools and state. Finish with the [compact host/query handoff](SETUP.md#hand-off), distinguishing expected persistence from an actual new-session test.

## Shell access on the workstation

No MCP client or Codex registration required:

```sh
garmin-archive day 2026-01-01
garmin-archive trend sleep_duration --from 2026-01-01 --to 2026-01-07
garmin-archive sleep --from 2026-01-01 --to 2026-01-07
```

Run `garmin-archive agent-guide` for installed query, branded chart and interpretation guidance. `assistant-guide --client other` prints a generic same-host shell handoff with absolute paths and that guidance; it does not assume an MCP connection. `connect --client shell` prints the handoff without registration, syncing or scheduling.

Use absolute executable and archive paths in remote tasks. These commands need an existing archive, but no Garmin key or live request. See [metrics, units and dates](USAGE.md#summaries-units-and-dates).

For a synthetic archive, pass its explicit `--data-dir` to `assistant-guide --client other` or `--client muse`, using the executable in the new environment. The printed paths are usable only on that host; report synthetic/manual status alongside them. Shell query success and an installed MCP executable do not establish MCP registration, discovery or a real client query.

## Local MCP clients

Connect Codex or Claude Code without resyncing or changing a schedule:

```sh
garmin-archive connect --client codex
garmin-archive connect --client claude
```

Each client has its own configuration. Existing `garmin-workbench` registrations are preserved; inspect the target with `codex mcp get garmin-workbench` or `claude mcp get garmin-workbench`. Codex discovery is checked in a fresh runtime. For Claude Code, start a new session and check `/mcp`. Test a real query in either client.

For clients accepting `mcpServers` JSON:

```json
{
  "mcpServers": {
    "garmin-workbench": {
      "command": "/absolute/path/to/garmin-archive-mcp",
      "args": []
    }
  }
}
```

Replace the executable path. For a custom archive, use `args: ["--data-dir", "/absolute/private/archive"]`.

### Tool contract

Sixteen tools read data/status/guidance; `configure_sync` changes the local macOS schedule when requested. Data tools need no Garmin credentials and make no live requests.

They provide daily summaries, up to 90 days of [trend metrics](USAGE.md#summaries-units-and-dates), detailed [sleep summaries](SLEEP.md), [Body Battery summaries](BODY_BATTERY.md), coverage, activities, stored daily responses and paginated FIT records. `agent_guide` returns installed guidance; `setup_receipt` separates setup evidence from outstanding verification. Samples omit coordinates and raw fields. `api_catalog` discovers all documented Personal API sources and native field definitions. `source_data` pages their complete stored responses; `source_series` reads native scalar values across dates. Default output omits coordinates; native coordinate access requires an explicit opt-in. See [Personal API coverage](API_COVERAGE.md). `daily_health` responses over 64 KB are rejected; use `source_data` to page them. Failed refreshes mask retained response data.

`chart` returns a bounded PNG image and structured caption/coverage/provenance metadata; `brand` returns settings and retrievable PNG/SVG resource URIs. Neither needs a shell or writes chart files. Charts require the optional charts extra; see the [delivery contract](VISUALIZATION.md#mcp-chart-delivery). Actual image display must be tested in each host.

Results include archive provenance, dates, units, coverage and freshness. Missing values aren't zeros; failed refreshes don't present stale values as current. Activity names and daily responses may be sensitive, and returned data may reach the selected AI provider.

## Assistants coordinating from elsewhere

On the archive host, print a handoff:

```sh
garmin-archive assistant-guide --client dot
```

Give it to your dot and confirm the computer name. It directs the dot to a local Codex task using Garmin MCP; the computer must be online, connected and already configured for Codex. See [OpenAI's connected-computer guide](https://learn.chatgpt.com/docs/dots/computers-and-apps). This Garmin handoff still needs an end-to-end test.

`--client codex`, `claude` and `other` print shorter handoffs. `--client muse` prints a same-host shell handoff with absolute paths. A local Codex/Claude registration doesn't connect Dot, Duet or Muse automatically. Direct Duet and Muse MCP integrations aren't implemented.

### Direct ChatGPT MCP

A regular ChatGPT conversation needs a separate connection. One documented route is [OpenAI's Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels): create a workspace tunnel, run its client on the archive host pointing at `garmin-archive-mcp`, then add the server in ChatGPT. The tunnel client must keep running; account/workspace permissions apply. The workbench doesn't configure or verify it.

The shipped server uses stdio and provides no authenticated remote HTTP connector. Don't expose it publicly as a shortcut.

## Verification status

A local Codex conversation has used the MCP successfully. Claude Code registration has been checked in isolation. Synthetic CLI answers and visible images were verified in the Muse and Grok apps at the [recorded baseline](COMPATIBILITY.md#assistant-acceptance-snapshot); Grok reused an existing installation, and Dot was blocked before its first prompt. Those checks did not exercise MCP, controlled persistence, live setup or provider routines. Use the [acceptance reporting stages](TESTING.md#assistant-acceptance-reports) and [setup checks](SETUP.md#4-connect-and-test-the-assistant) to record each result separately.
