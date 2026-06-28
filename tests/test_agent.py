"""Tests for the Agent loop.

Covers the stub provider end-to-end: search-then-answer, remember, recall,
multi-turn memory persistence within a session, citation tracking, and
the step-limit safety.

The Claude provider is not exercised here (it requires a key + the
network); the seam is documented in agent.py and verified by inspection.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_agent_example.agent import Agent, Session  # noqa: E402


CORPUS = {
    "tenant.md": "tenant data residency: tenant data stays within the EU geography.",
    "copilot.md": "copilot rollout playbook: rollout is gated on adoption metrics.",
    "sharepoint.md": "orphaned sharepoint documents are flagged for review.",
}


def make_agent() -> Agent:
    return Agent(corpus=CORPUS, provider="stub")


def test_search_question_produces_tool_call_and_citation():
    agent = make_agent()
    session = Session()
    out = agent.run_turn(session, "tenant data residency")

    assert out["steps"] >= 2  # one search, one final
    tools_used = [tc["tool"] for tc in out["tool_calls"]]
    assert "search_corpus" in tools_used
    assert "tenant.md" in out["citations"]
    assert "tenant.md" in out["answer"]


def test_remember_then_recall_within_session():
    agent = make_agent()
    session = Session()

    agent.run_turn(session, "Remember that pilot kick-off is 2026-07-15")
    assert any("pilot" in k for k in session.memory)

    out = agent.run_turn(session, "Do you remember pilot kick-off?")
    tools_used = [tc["tool"] for tc in out["tool_calls"]]
    assert "recall" in tools_used


def test_session_memory_persists_across_multiple_turns():
    agent = make_agent()
    session = Session()
    agent.run_turn(session, "Remember that owner is alice")
    agent.run_turn(session, "Remember that deadline is friday")
    assert len(session.memory) == 2


def test_unmatched_question_still_returns_final_answer():
    agent = make_agent()
    session = Session()
    out = agent.run_turn(session, "What about kubernetes scheduling internals?")
    # No corpus match, but agent should still terminate with a final answer.
    assert out["answer"]
    assert out["steps"] >= 1


def test_transcript_records_thinking_tool_and_final_turns():
    agent = make_agent()
    session = Session()
    agent.run_turn(session, "copilot rollout playbook")
    kinds = [t.kind for t in session.transcript]
    assert "thinking" in kinds
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert "final" in kinds


def test_max_steps_safety_returns_graceful_message():
    agent = Agent(corpus=CORPUS, provider="stub", max_steps=0)
    session = Session()
    out = agent.run_turn(session, "Anything")
    assert "couldn't reach" in out["answer"].lower()
    assert out["steps"] == 0


def test_provider_defaults_to_stub_when_env_unset():
    # Ensure no leakage from the test runner's environment.
    saved = os.environ.pop("CLAUDE_AGENT_PROVIDER", None)
    try:
        agent = Agent(corpus=CORPUS)
        assert agent.provider == "stub"
    finally:
        if saved is not None:
            os.environ["CLAUDE_AGENT_PROVIDER"] = saved
