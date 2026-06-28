"""Tools the agent can call.

Each tool is a pure-function wrapper around some side effect (search,
memory, file write). The agent's `run_turn` decides which one to invoke
based on the user's question + the system prompt. Tools are JSON-
schema-described so the LLM can pick correctly.

For the stub backend, the tool dispatch + result generation are entirely
deterministic - rule-based on the question text. The same tool functions
are what the real Claude SDK would call when CLAUDE_AGENT_PROVIDER=claude.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    """Describes a tool the agent can invoke. The schema is what the LLM sees."""
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCall:
    """A request to invoke a tool, produced by the agent loop."""
    tool: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """The result of executing a tool call."""
    tool: str
    result: Any
    is_error: bool = False


# ----- Tool implementations ---------------------------------------------------

def search_corpus(query: str, corpus: dict[str, str], k: int = 3) -> list[dict]:
    """Naive substring search across a small corpus (replace with real retrieval).

    Tries the full query first; if no doc contains it as a substring, falls
    back to scoring each doc by how many query *words* it contains. Returns
    the top-k entries, each with a snippet around the best match. Shape
    matches what a real RAG tool would return so the agent can cite.
    """
    q = query.lower().strip()
    hits = []

    # Phase 1: exact substring match wins on score.
    for doc_id, text in corpus.items():
        if q and q in text.lower():
            score = text.lower().count(q) * 10  # weighted high
            hits.append({"doc": doc_id, "score": score,
                         "snippet": _snippet(text, q)})

    # Phase 2: word-overlap fallback for any doc that didn't phrase-match.
    matched_ids = {h["doc"] for h in hits}
    words = [w for w in q.split() if len(w) > 2]
    if words:
        for doc_id, text in corpus.items():
            if doc_id in matched_ids:
                continue
            text_lower = text.lower()
            overlap = sum(1 for w in words if w in text_lower)
            if overlap > 0:
                best_word = max(words, key=lambda w: text_lower.count(w))
                hits.append({"doc": doc_id, "score": overlap,
                             "snippet": _snippet(text, best_word)})

    hits.sort(key=lambda h: -h["score"])
    return hits[:k]


def remember(memory: dict[str, str], key: str, value: str) -> dict:
    """Write a key/value pair into the persistent memory store.

    In a real Claude Agent SDK deployment this would be the `/mnt/memory/`
    write that the harness persists across sessions.
    """
    memory[key] = value
    return {"key": key, "stored": True, "memory_size": len(memory)}


def recall(memory: dict[str, str], key: str) -> dict:
    """Read a key from the persistent memory store."""
    if key in memory:
        return {"key": key, "value": memory[key], "found": True}
    return {"key": key, "value": None, "found": False,
            "available_keys": sorted(memory.keys())}


def grade_response(response: str, rubric: list[str]) -> dict:
    """Score the agent's draft against a rubric. The "outcomes" pattern.

    Returns a per-criterion verdict + total. In a Claude harness deployment
    this is what the grader agent would do; here it's a deterministic rule.
    Each criterion checks whether the response mentions the keyword.
    """
    per = []
    passed = 0
    for criterion in rubric:
        keyword = criterion.lower()
        ok = keyword in response.lower()
        per.append({"criterion": criterion, "passed": ok})
        if ok:
            passed += 1
    return {
        "passed": passed,
        "total": len(rubric),
        "rate": round(passed / len(rubric), 2) if rubric else 0.0,
        "per_criterion": per,
    }


# ----- Helpers ----------------------------------------------------------------

def _snippet(text: str, query: str, context: int = 80) -> str:
    """Extract a context window around the first match of `query` in `text`."""
    lower = text.lower()
    idx = lower.find(query.lower())
    if idx < 0:
        return text[:context].strip()
    start = max(0, idx - context // 2)
    end = min(len(text), idx + len(query) + context // 2)
    return ("..." if start > 0 else "") + text[start:end].strip() + ("..." if end < len(text) else "")


# ----- Tool registry (what the agent sees) ------------------------------------

TOOL_SCHEMAS: dict[str, Tool] = {
    "search_corpus": Tool(
        name="search_corpus",
        description="Search the internal knowledge corpus for documents matching a query. Returns top-k matches with snippets.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for"},
                "k": {"type": "integer", "description": "Number of results to return", "default": 3},
            },
            "required": ["query"],
        },
    ),
    "remember": Tool(
        name="remember",
        description="Save a key/value pair to persistent memory. Use this to remember facts the user shared that should persist across sessions.",
        input_schema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Short identifier for what's being saved"},
                "value": {"type": "string", "description": "The content to save"},
            },
            "required": ["key", "value"],
        },
    ),
    "recall": Tool(
        name="recall",
        description="Read a previously-saved value from persistent memory by key. If the key doesn't exist, returns the available keys.",
        input_schema={
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    ),
    "grade_response": Tool(
        name="grade_response",
        description="Score a draft response against a rubric of criteria. Each criterion is a phrase the response should mention. Returns pass count + per-criterion breakdown.",
        input_schema={
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "rubric": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["response", "rubric"],
        },
    ),
}
