"""End-to-end research assistant - all 4 tools used in one workflow.

This shows what a complete "agent does a small research task" looks like
end-to-end:

  1. User asks a question
  2. Agent searches the corpus (search_corpus tool)
  3. Agent commits a finding to memory (remember tool)
  4. Later in the same session, agent recalls the saved finding (recall tool)
  5. Agent grades its draft response against a rubric (grade_response tool)
  6. Agent returns the final answer with citations

The script runs a scripted multi-turn session demonstrating each tool in
sequence, then prints the full transcript so the user can see exactly which
tool the agent picked for each step and why.

Default uses the stub backend - deterministic, no API key needed. Set
CLAUDE_AGENT_PROVIDER=claude to run against the real Anthropic API once
you've wired _choose_action_claude.

Usage:
    python examples/research_assistant.py
    python examples/research_assistant.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from claude_agent_example.agent import Agent, Session  # noqa: E402
from claude_agent_example.cli import SAMPLE_CORPUS  # noqa: E402
from claude_agent_example import tools  # noqa: E402


SCRIPT = [
    # (label, user message, what the agent should demonstrate)
    ("research-question",
     "What's our data residency commitment for Copilot?",
     "search_corpus + cite source"),
    ("save-finding",
     "Remember that the EU data residency commitment is enforced for Copilot via the Microsoft 365 service boundary.",
     "remember tool with key/value"),
    ("recall-finding",
     "What did I tell you about EU data residency?",
     "recall the saved fact"),
    ("compose-followup",
     "Based on what we have, what are the open compliance questions for the EU rollout?",
     "search_corpus follow-up using context"),
    ("grade-draft",
     "The EU data residency commitment is documented in tenant policy. Grade my answer against the rubric: 'EU', 'data residency', 'Microsoft 365', 'service boundary'.",
     "grade_response (note: stub doesn't pick grade_response automatically; "
     "shown via direct tool call below)"),
]


def run_demo(as_json: bool = False) -> int:
    agent = Agent(corpus=SAMPLE_CORPUS)
    session = Session(user_id="research_demo")

    results = []
    for label, message, what in SCRIPT[:4]:  # First 4 turns through the loop
        if not as_json:
            print(f"\n{'=' * 70}\n[{label}] {what}\n{'=' * 70}")
            print(f"USER:  {message}\n")
        out = agent.run_turn(session, message)
        results.append({
            "label": label, "what": what, "user_message": message,
            "answer": out["answer"],
            "tools_used": [tc["tool"] for tc in out["tool_calls"]],
            "citations": out["citations"],
            "steps": out["steps"],
        })
        if not as_json:
            print(f"AGENT:    {out['answer']}")
            print(f"  tools:  {[tc['tool'] for tc in out['tool_calls']]}")
            print(f"  cites:  {out['citations']}")
            print(f"  steps:  {out['steps']}")

    # Explicit grade_response demonstration (the stub's selector doesn't pick
    # this automatically; production wiring with the Claude API would).
    if not as_json:
        print(f"\n{'=' * 70}\n[grade-draft] grade_response (direct tool call)\n{'=' * 70}")
    grade_result = tools.grade_response(
        response="The EU data residency commitment is documented and enforced via the Microsoft 365 service boundary.",
        rubric=["EU", "data residency", "Microsoft 365", "service boundary"],
    )
    results.append({
        "label": "grade-draft",
        "what": "grade_response (direct tool call)",
        "tool_result": grade_result,
    })
    if not as_json:
        print(f"Grade: {grade_result['passed']}/{grade_result['total']} criteria passed "
              f"({grade_result['rate'] * 100:.0f}%)")
        for c in grade_result["per_criterion"]:
            mark = "OK" if c["passed"] else "MISS"
            print(f"  [{mark}] {c['criterion']}")

    if not as_json:
        print(f"\n{'=' * 70}\nSession transcript: {len(session.transcript)} turns recorded")
        print(f"Memory state: {dict(session.memory)}")
    else:
        print(json.dumps({
            "provider": agent.provider,
            "results": results,
            "memory_state": dict(session.memory),
            "transcript_turn_count": len(session.transcript),
        }, indent=2, default=str))

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="End-to-end research-assistant demo.")
    parser.add_argument("--json", action="store_true",
                        help="Emit a machine-readable JSON transcript.")
    args = parser.parse_args(argv)
    return run_demo(as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
