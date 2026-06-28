"""Eval harness for the Claude Agent SDK example.

Runs every case in golden.json against the agent and reports per-case
pass/fail plus an aggregate score. Default uses the stub provider so the
result is deterministic and CI can gate on it.

Usage:
    python evals/run.py                 # uses stub provider
    CLAUDE_AGENT_PROVIDER=claude python evals/run.py   # uses real API

Pass rate is printed at the end. Non-zero exit code if any case fails.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from claude_agent_example.agent import Agent, Session  # noqa: E402
from claude_agent_example.cli import SAMPLE_CORPUS  # noqa: E402


def load_cases() -> list[dict]:
    with open(Path(__file__).parent / "golden.json") as f:
        return json.load(f)["cases"]


def run_case(agent: Agent, case: dict) -> dict:
    session = Session()
    out = agent.run_turn(session, case["question"])
    tools_used = [tc["tool"] for tc in out["tool_calls"]]

    tool_ok = case["expect_tool"] in tools_used
    citation_ok = all(c in out["citations"] for c in case["expect_citations"])
    rubric_ok = all(r.lower() in out["answer"].lower() for r in case["rubric"])

    return {
        "id": case["id"],
        "passed": tool_ok and citation_ok and rubric_ok,
        "tool_ok": tool_ok,
        "citation_ok": citation_ok,
        "rubric_ok": rubric_ok,
        "tools_used": tools_used,
        "citations": out["citations"],
    }


def main() -> int:
    cases = load_cases()
    agent = Agent(corpus=SAMPLE_CORPUS)
    print(f"Running {len(cases)} eval cases against provider={agent.provider}\n")

    results = [run_case(agent, c) for c in cases]
    passed = sum(1 for r in results if r["passed"])

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  {status}  {r['id']:30s}  tool={r['tool_ok']}  cites={r['citation_ok']}  rubric={r['rubric_ok']}")

    rate = passed / len(cases) if cases else 0.0
    print(f"\n{passed}/{len(cases)} passed ({rate:.0%})")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
