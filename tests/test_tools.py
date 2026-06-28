"""Tests for the four tool functions in tools.py.

Tools are pure functions, so the tests don't need to instantiate the Agent
- they exercise the tool surface directly. That's the same separation the
real Claude Agent SDK encourages: tools are tested in isolation; the
orchestrator is tested separately.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_agent_example import tools  # noqa: E402


CORPUS = {
    "doc-a.md": "Conditional Access policies must be enabled, not report-only.",
    "doc-b.md": "Copilot tenant data stays within the EU geography.",
    "doc-c.md": "Orphaned SharePoint documents are flagged for review.",
}


def test_search_corpus_returns_matching_docs():
    hits = tools.search_corpus("conditional access", CORPUS)
    assert len(hits) == 1
    assert hits[0]["doc"] == "doc-a.md"
    assert "conditional" in hits[0]["snippet"].lower()


def test_search_corpus_returns_empty_on_no_match():
    hits = tools.search_corpus("kubernetes", CORPUS)
    assert hits == []


def test_search_corpus_respects_k():
    hits = tools.search_corpus("the", CORPUS, k=2)
    assert len(hits) <= 2


def test_remember_writes_to_memory_dict():
    mem = {}
    r = tools.remember(mem, key="pilot_date", value="2026-07-15")
    assert r["stored"] is True
    assert r["memory_size"] == 1
    assert mem["pilot_date"] == "2026-07-15"


def test_recall_returns_value_when_present():
    mem = {"pilot_date": "2026-07-15"}
    r = tools.recall(mem, key="pilot_date")
    assert r["found"] is True
    assert r["value"] == "2026-07-15"


def test_recall_lists_available_keys_when_missing():
    mem = {"pilot_date": "2026-07-15", "owner": "alice"}
    r = tools.recall(mem, key="does_not_exist")
    assert r["found"] is False
    assert r["value"] is None
    assert sorted(r["available_keys"]) == ["owner", "pilot_date"]


def test_grade_response_scores_against_rubric():
    response = "Our tenant data stays in the EU and Conditional Access is enabled."
    r = tools.grade_response(response, rubric=["EU", "Conditional Access", "MFA"])
    assert r["passed"] == 2
    assert r["total"] == 3
    assert r["rate"] == round(2 / 3, 2)
    crit_by_name = {c["criterion"]: c["passed"] for c in r["per_criterion"]}
    assert crit_by_name["EU"] is True
    assert crit_by_name["MFA"] is False


def test_grade_response_handles_empty_rubric():
    r = tools.grade_response("anything", rubric=[])
    assert r["total"] == 0
    assert r["passed"] == 0
    assert r["rate"] == 0.0


def test_tool_schemas_registry_has_all_tools():
    expected = {"search_corpus", "remember", "recall", "grade_response"}
    assert set(tools.TOOL_SCHEMAS) == expected
    for name, tool in tools.TOOL_SCHEMAS.items():
        assert tool.name == name
        assert "type" in tool.input_schema
        assert "properties" in tool.input_schema
