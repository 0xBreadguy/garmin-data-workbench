"""Installed guidance for shell and MCP agents; no archive or credentials needed."""
from pathlib import Path


def agent_guide() -> str:
    return Path(__file__).with_name("agent_guide.md").read_text(encoding="utf-8")
