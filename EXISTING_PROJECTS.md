# Related projects

Research snapshot: November 1, 2026. Public docs and selected source were reviewed; these projects weren't run with credentials or security-audited. Claims below describe those snapshots and may change.

## Where this workbench fits

Build around the official Personal API, a durable archive and useful access for workstation agents and power users. Original FIT samples, inspectable coverage and dependable setup are priorities. Local storage and MCP already exist elsewhere; novelty isn't the goal.

## Comparisons

| Project | Useful overlap | Main difference in the reviewed snapshot |
| --- | --- | --- |
| [Garmin Personal API client](https://github.com/garmin/connect-personal-api-python) | Official authentication, endpoints, original downloads | Dependency, not a maintained archive or agent workflow |
| [garmin-connect-personal-mcp](https://github.com/braydenabo/garmin-mcp) | Official API, SQLite, resumable/scheduled sync, coverage, MCP, charts | Closest overall; saves FIT ZIPs, but reviewed activity tools use summary JSON without decoded sample queries |
| [garmin-personal-mcp](https://github.com/Mason-Levyy/garmin-personal-mcp) | Official API, broad endpoints, date-window splitting, original downloads | Live queries rather than a durable archive/FIT analysis layer |
| [garmin-health-data](https://github.com/diegoscarabelli/garmin-health-data) | SQLite, source retention, detailed FIT records/laps/events | Own Connect client; no built-in MCP. FIT schema and Apache-2.0 code are useful references |
| [GarminDB](https://github.com/tcgoetz/GarminDB) | SQLite, device/Connect imports, notebooks | Different collection and analysis workflow |
| [garmin-local-mcp](https://github.com/anup-shesh/garmin-local-mcp) | Warehouse, trends, correlations, gaps, wellness-FIT import | Unofficial Connect access; docs exclude activity-FIT parsing |
| [garmin-mcp-local](https://github.com/the-mace/garmin-mcp-local) | Cache, backfill, gap repair, persistent cooldowns, launchd/watchdog examples | Unofficial access; reliability ideas to evaluate, not current workbench guarantees |
| [fitness-data-sync](https://github.com/chrisa84/fitness-data-sync) | SQLite mirror, read-only MCP, scheduler examples | Unofficial access; another existing archive/MCP approach |
| [garmin-health-mcp-gateway](https://github.com/cara-labs/garmin-health-mcp-gateway) | Separate collector/query roles, queued sync, FIT retention | PostgreSQL, containers and remote tunnels add operational work |
| [garmin-grafana](https://github.com/arpanghosh8453/garmin-grafana) | Long-term dashboards | Docker/InfluxDB/Grafana; an option for users prioritizing dashboards |
| [Garth](https://github.com/matin/garth) / [Garth MCP](https://garth.readthedocs.io/en/latest/mcp/) | Shared client/authentication and structured health tools | Unofficial access and live API dependence; endpoint breadth doesn't prove Personal API coverage |

Source references: [health-data schema](https://github.com/diegoscarabelli/garmin-health-data/blob/main/garmin_health_data/tables.ddl), [archive sync](https://github.com/braydenabo/garmin-mcp/blob/main/src/garmin_connect_personal_mcp/sync.py), [activity queries](https://github.com/braydenabo/garmin-mcp/blob/main/src/garmin_connect_personal_mcp/activities.py), [MCP tool reference](https://github.com/braydenabo/garmin-mcp/blob/main/docs/tools.md).

## What to learn from them

- **Reliability:** persistent rate-limit cooldowns, per-run diagnostics, gap repair and honest queued/running/failed states.
- **Analysis:** recorded samples, units, timestamps and gaps; comparisons without treating missing data as zero or correlation as cause.
- **Recovery:** export/import fallback, explicit source precedence and activity-edit/deletion history.
- **Setup:** diagnostics and tested paths for different clients and persistent hosts.

The workbench already has daily trends and macOS scheduling. Sampling-completeness analysis, persistent cooldowns and historical reconciliation remain opportunities. See [current priorities](PRODUCT_BRIEF.md#next-priorities).

Review licenses before reusing code and preserve notices. Test compatible schemas/file lifecycles with synthetic fixtures first. A real-account comparison needs separate authorization; don't move keys into another project to explore it. Verify history depth and endpoint coverage against Garmin rather than adopting another project's claims as universal limits.
