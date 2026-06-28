"""CLI entry point - runs a scripted demo conversation with the agent.

Default backend is the deterministic stub so the kit runs anywhere without
keys (perfect for CI, screenshots, and the Pages live demo). Set
CLAUDE_AGENT_PROVIDER=claude with ANTHROPIC_API_KEY to route to the real
Claude API.

Usage:
    claude-agent-example                # runs the scripted demo
    claude-agent-example --interactive  # repl mode
    claude-agent-example --json         # machine-readable transcript

This is intentionally tiny - the agent loop lives in agent.py and the
tools in tools.py. The CLI just wires them together for a demo run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .agent import Agent, Session


# A small sample corpus shaped like an M365 consultant's knowledge base.
# Each entry maps a doc id to its full text. Searches return snippets.
SAMPLE_CORPUS = {
    "tenant-baseline.md": (
        "Tenant baseline configuration for Microsoft 365. "
        "Conditional Access policies must be set to enabled, not report-only. "
        "MFA is enforced for all admin roles. "
        "Data Loss Prevention (DLP) policies cover Exchange, SharePoint, OneDrive, and Teams chats. "
        "The default sensitivity label for new documents is 'General'."
    ),
    "copilot-rollout.md": (
        "Copilot for M365 rollout playbook. "
        "Phase 1: pilot with 25 users for 30 days. "
        "Phase 2: department-by-department expansion, gated on adoption metrics. "
        "Phase 3: tenant-wide. "
        "Adoption is measured by weekly active prompts per licensed user; the floor is 5."
    ),
    "data-residency.md": (
        "Data residency commitments. "
        "Customer tenant data is stored in the EU geography. "
        "Azure OpenAI calls from Copilot stay within the Microsoft 365 service boundary. "
        "No tenant data leaves the EU for model training."
    ),
    "sharepoint-hygiene.md": (
        "SharePoint hygiene runbook. "
        "Orphaned documents (no owner OR not accessed in 365 days) are flagged for review. "
        "Sites with fewer than 2 active members in 90 days are archived. "
        "External sharing is restricted to specific allowed domains."
    ),
    "incident-response.md": (
        "Incident response procedure for credential compromise. "
        "Step 1: revoke session tokens via Entra ID admin centre. "
        "Step 2: rotate the user's password and require MFA re-registration. "
        "Step 3: audit sign-in logs for the previous 14 days. "
        "Step 4: file the post-mortem in the security log."
    ),
}


def build_agent(provider: str | None = None) -> Agent:
    return Agent(corpus=SAMPLE_CORPUS, provider=provider)


def run_scripted_demo(as_json: bool = False) -> int:
    """Run a few example turns to show the agent's behaviour."""
    agent = build_agent()
    session = Session(user_id="demo")

    questions = [
        "What's our data residency commitment for Copilot?",
        "Remember that the pilot kick-off is on 2026-07-15.",
        "Do you remember the pilot kick-off date?",
        "How do orphaned SharePoint documents get handled?",
    ]

    results = []
    for q in questions:
        out = agent.run_turn(session, q)
        results.append({"question": q, "answer": out["answer"],
                        "tool_calls": out["tool_calls"],
                        "citations": out["citations"],
                        "steps": out["steps"]})
        if not as_json:
            print(f"\n>>> {q}")
            print(f"    answer:    {out['answer']}")
            print(f"    tools:     {[tc['tool'] for tc in out['tool_calls']]}")
            print(f"    citations: {out['citations']}")
            print(f"    steps:     {out['steps']}")

    if as_json:
        print(json.dumps({"provider": agent.provider, "turns": results}, indent=2))
    else:
        print(f"\nProvider: {agent.provider}  (set CLAUDE_AGENT_PROVIDER=claude to swap)")
    return 0


def run_interactive() -> int:
    agent = build_agent()
    session = Session(user_id="interactive")
    print(f"Claude Agent SDK example (provider={agent.provider}). Ctrl-C to exit.")
    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not q:
            continue
        out = agent.run_turn(session, q)
        print(f"\n{out['answer']}")
        if out["tool_calls"]:
            print(f"  (tools: {[tc['tool'] for tc in out['tool_calls']]})")
        if out["citations"]:
            print(f"  (sources: {out['citations']})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Claude Agent SDK example demo.")
    parser.add_argument("--interactive", action="store_true",
                        help="Start a REPL instead of the scripted demo.")
    parser.add_argument("--json", action="store_true",
                        help="Emit the scripted demo as JSON (for CI / Pages).")
    args = parser.parse_args(argv)

    if args.interactive:
        return run_interactive()
    return run_scripted_demo(as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
