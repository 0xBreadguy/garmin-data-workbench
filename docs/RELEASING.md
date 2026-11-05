# Release a workbench version

Use a reviewed PR and the protected default branch. This checklist covers a source release; there is no automatic PyPI upload, deployment or release-publishing workflow.

## Prepare the candidate

1. Reconcile the intended changes and preserve concurrent work. Check the diff for credentials, real health data, routes, archives and unrelated/generated files.
2. Update `project.version` in `pyproject.toml` when cutting a new version, run `uv lock` and review both files. Keep README version wording aligned. For the first `v0.1.0` release, confirm the existing version matches the tag.
3. Review dependency advisories and the resolved lockfile. Upgrade vulnerable direct/transitive dependencies deliberately; don't equate a clean advisory scan with a security audit. See the [dependency audit commands](TESTING.md#dependency-advisories).
4. Check setup, CLI/MCP guidance, compatibility claims and example output against the candidate. Use only generated data for public screenshots. Keep dates, coverage and synthetic labels visible.
5. Write release notes describing capabilities, breaking behavior, upgrade instructions and known limits. For 0.1.0, call out macOS-only built-in scheduling, incomplete Windows live privacy validation and separately tested assistant connections.

## Verify before merging

From the candidate checkout:

```sh
uv sync --locked --extra charts
uv run --locked --extra charts python -m unittest discover -s tests -v
uv build
uv run --locked --extra charts python scripts/smoke_installed.py
uv run --locked --extra charts python scripts/smoke_installed.py --charts
git diff --check
```

The smoke script expects exactly one wheel in `dist/`; preserve or move older artifacts out of that directory before building a different version. Inspect wheel/sdist contents and package provenance. A build from uncommitted changes records a dirty source; build final release artifacts from the clean release revision.

The final PR head must pass all three required GitHub Actions checks: `tests (ubuntu-latest)`, `tests (macos-latest)` and `tests (windows-latest)`, with the branch up to date. Local macOS results do not replace that matrix. Don't bypass the ruleset or treat pending/skipped checks as passed. Require the post-merge package smoke to pass for the merged revision before tagging it.

## Publish and check

Publication requires the maintainer's authorization. Tag the verified commit with the matching `vX.Y.Z`, create a GitHub release with the reviewed notes, and rebuild any attached artifacts from that clean tagged checkout. Check the tag, source revision, installation instructions and attached files after publication. A PyPI release, if introduced later, needs its own packaging and publishing verification.

Enable GitHub secret scanning/push protection, dependency alerts and private vulnerability reporting when available. Confirm [SECURITY.md](../SECURITY.md) leads to a usable private report route. Keep the public bug/setup templates easy to find without requesting private data.

For a rollout, lead with one useful question and a clearly labeled synthetic result, then link to the README's demo and setup routes. Keep an early release's boundaries explicit. A video or agent conversation doesn't establish support for every host, live Garmin setup or recurring execution.
