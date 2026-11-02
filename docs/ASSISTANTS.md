# Connect your assistant

Run [setup](SETUP.md) on the archive host first. Agents can query through a shell or local stdio MCP. An agent coordinating from elsewhere also needs a supported connection to that host.

## Shell access on the workstation

No MCP client or Codex registration required:

```sh
garmin-archive day 2026-01-01
garmin-archive trend sleep_duration --from 2026-01-01 --to 2026-01-07
```

Use absolute executable and archive paths in remote tasks. These commands need an existing archive, but no Garmin key or live request. See [metrics, units and dates](USAGE.md#summaries-units-and-dates).

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

Seven tools read data/status; `configure_sync` changes the local macOS schedule when requested. Data tools need no Garmin credentials and make no live requests.

They provide daily summaries, up to 90 days of five [trend metrics](USAGE.md#summaries-units-and-dates), coverage, activities, stored daily responses and paginated FIT records. Samples omit coordinates and raw fields. Daily responses over 64 KB are rejected; inspect those locally with `health`.

Results include dates, units, coverage and freshness. Missing values aren't zeros; failed refreshes don't present stale values as current. Activity names and daily responses may be sensitive, and returned data may reach the selected AI provider.

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

A local Codex conversation has used the MCP successfully. Claude Code registration has been checked in isolation. Muse has a reported offline VM check, but its live setup and provider routine remain unverified. Other handoffs need end-to-end tests. Test installation, discovery, live sync, a real query and recurring execution separately using [the setup checks](SETUP.md#4-connect-and-test-the-assistant).
