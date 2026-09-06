#!/usr/bin/env python3
"""
Verify current MCP wiring + report what's missing for the user's stated
integration goals (Gmail, Slack, GitHub, Docker, Ollama).

Prints a compact status table:
  - Which MCP servers are configured in .mcp.json today
  - Whether each configured server's binary/URL is reachable
  - What CONNECTOR (Gmail / Slack / GitHub / Docker / Ollama) each maps to
  - What's missing, with a concrete `claude mcp add ...` command per gap

DOES NOT MODIFY .mcp.json. Adding servers to a live config can break
in-flight Claude Code sessions — that's the user's call, not the script's.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
MCP_JSON = REPO / ".mcp.json"

# Maps a "connector goal" (what the user asked for) → the MCP server that
# delivers it + a one-line install command they can run to add it. All
# commands are `claude mcp add …` (or `claude mcp add-json …` for URL-based).
# None of these run automatically here — this is a shopping list, not an
# installer.
CONNECTORS = [
    {
        "goal": "GitHub",
        "package": "@modelcontextprotocol/server-github",
        "install": (
            "claude mcp add github "
            "'npx -y @modelcontextprotocol/server-github' "
            "-e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_TOKEN"
        ),
        "auth": "personal access token (already in ~/.config/devops-tokens.env as GITHUB_TOKEN)",
        "notes": "issues · PRs · file contents · code search · repos",
    },
    {
        "goal": "Docker",
        "package": "@quantgeekdev/docker-mcp",
        "install": "claude mcp add docker 'npx -y @quantgeekdev/docker-mcp'",
        "auth": "none — talks to the local Docker daemon socket",
        "notes": "list containers · logs · exec · compose · build",
    },
    {
        "goal": "Slack",
        "package": "@modelcontextprotocol/server-slack",
        "install": (
            "claude mcp add slack "
            "'npx -y @modelcontextprotocol/server-slack' "
            "-e SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN "
            "-e SLACK_TEAM_ID=$SLACK_TEAM_ID"
        ),
        "auth": "bot token (create at api.slack.com/apps → OAuth & Permissions)",
        "notes": "channels · messages · search · user info",
    },
    {
        "goal": "Gmail",
        "package": "@gongrzhe/server-gmail-autoauth-mcp",
        "install": (
            "npx @gongrzhe/server-gmail-autoauth-mcp auth "
            "# then: claude mcp add gmail 'npx -y @gongrzhe/server-gmail-autoauth-mcp'"
        ),
        "auth": "OAuth flow — first run auth walks you through Google consent",
        "notes": "search · send · draft · labels — auth is Google OAuth so interactive",
    },
    {
        "goal": "Ollama (local fallback)",
        "package": "@rawveg/ollama-mcp",
        "install": (
            "claude mcp add ollama "
            "'npx -y @rawveg/ollama-mcp' "
            "-e OLLAMA_HOST=http://localhost:11434"
        ),
        "auth": "none — talks to your local Ollama at localhost:11434",
        "notes": "list models · generate · chat — for cost-free local completion "
                 "(codellama, deepseek-coder, mixtral, llama3, mistral you already have)",
    },
]


def load_mcp() -> dict[str, Any]:
    """Parse .mcp.json structurally — extract server names + transports only.
    Never prints raw contents (which may include tokens in `env:`)."""
    if not MCP_JSON.is_file():
        return {}
    try:
        return json.loads(MCP_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def probe_binary(cmd: str) -> str:
    """Is the top-level command (e.g. 'npx', 'uvx', 'python') on PATH?"""
    if not cmd:
        return "?"
    head = cmd.split()[0]
    return "✓" if shutil.which(head) else "✗"


def probe_service(url: str, timeout: float = 1.5) -> str:
    """Local service reachability check — used for Ollama at localhost:11434
    and similar."""
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout):
            return "✓"
    except Exception:
        return "✗"


def main() -> int:
    doc = load_mcp()
    servers = doc.get("mcpServers", {})

    print("=" * 72)
    print(f"MCP servers configured in {MCP_JSON.relative_to(REPO.parent)}")
    print("=" * 72)
    if not servers:
        print("  (none)")
    else:
        print(f"  {'name':<24} {'transport':<10} {'binary':<8} {'command':<20}")
        print(f"  {'-'*24} {'-'*10} {'-'*8} {'-'*20}")
        for name, cfg in servers.items():
            cmd = cfg.get("command", "") or cfg.get("url", "")
            transport = "stdio" if "command" in cfg else "http" if "url" in cfg else "?"
            reach = probe_binary(cmd) if transport == "stdio" else probe_service(cmd)
            head = cmd.split()[0] if cmd else "?"
            print(f"  {name:<24} {transport:<10} {reach:<8} {head:<20}")

    print()
    print("=" * 72)
    print("Local services (relevant to fallback / observability)")
    print("=" * 72)
    ollama = probe_service("http://localhost:11434/api/tags")
    print(f"  Ollama at localhost:11434         {ollama}")

    print()
    print("=" * 72)
    print("Requested connectors — status + install command per gap")
    print("=" * 72)
    for c in CONNECTORS:
        wired = any(c["package"] in json.dumps(cfg) for cfg in servers.values())
        marker = "✓ wired" if wired else "○ not wired"
        print(f"\n  {c['goal']:<26} {marker}")
        print(f"    package: {c['package']}")
        print(f"    auth:    {c['auth']}")
        print(f"    what:    {c['notes']}")
        if not wired:
            print(f"    add:     {c['install']}")

    print()
    print("=" * 72)
    print("Summary")
    print("=" * 72)
    total = len(CONNECTORS)
    wired_count = sum(
        1 for c in CONNECTORS
        if any(c["package"] in json.dumps(cfg) for cfg in servers.values())
    )
    print(f"  {wired_count}/{total} requested connectors wired.")
    print("  Adding a server requires `claude mcp add …` (touches either ~/.claude.json")
    print("  or the project .mcp.json depending on scope) and a session restart to pick")
    print("  up. Nothing was modified by this script.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
