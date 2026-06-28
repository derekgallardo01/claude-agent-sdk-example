"""The agent loop.

Architecture:
   Agent --> chooses tool --> tool executes --> result fed back --> Agent decides next step --> ... --> final answer

In the **stub** backend (default), tool choice is rule-based on the
user's question text (so the demo is deterministic, runs in CI without
keys, and the tests can assert exact behaviour).

In the **claude** backend (CLAUDE_AGENT_PROVIDER=claude with ANTHROPIC_API_KEY
set), tool choice is delegated to the actual Claude API via the Anthropic
SDK's tool-use loop. The same tool functions are called; only the
selector changes.

The seam is a single class method (`_choose_action`). Everything else -
tool dispatch, memory state, transcript building, outcome grading - is
provider-agnostic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from . import tools


@dataclass
class Turn:
    """One step in the agent's reasoning trace."""
    kind: str  # "thinking" | "tool_call" | "tool_result" | "final"
    content: Any


@dataclass
class Session:
    """A multi-turn conversation with the agent.

    Memory persists across turns within a session. In a real Claude harness
    deployment, this would persist across sessions via /mnt/memory/.
    """
    user_id: str = "default"
    memory: dict[str, str] = field(default_factory=dict)
    transcript: list[Turn] = field(default_factory=list)


class Agent:
    """A multi-tool agent. Stub default; Claude API on opt-in."""

    DEFAULT_SYSTEM = (
        "You are a research assistant for a Microsoft 365 consultant. "
        "When asked a question, decide whether to (a) search the internal "
        "corpus, (b) recall something previously saved, (c) save a new fact, "
        "or (d) answer directly. Always cite sources by document name when "
        "you use the search tool. Be terse."
    )

    def __init__(
        self,
        corpus: dict[str, str],
        system: str = DEFAULT_SYSTEM,
        provider: str | None = None,
        model: str = "claude-opus-4-7",
        max_steps: int = 8,
    ):
        self.corpus = corpus
        self.system = system
        self.provider = provider or os.environ.get("CLAUDE_AGENT_PROVIDER", "stub")
        self.model = model
        self.max_steps = max_steps

    # ----- Public entry point -------------------------------------------------

    def run_turn(self, session: Session, user_message: str) -> dict[str, Any]:
        """Run one user turn through the agent loop.

        Returns a dict with the final answer, tool calls made, citations,
        and the updated transcript.
        """
        session.transcript.append(Turn("thinking", f"received: {user_message[:120]}"))

        citations: list[str] = []
        tool_calls_made: list[dict] = []

        scratchpad = ""

        for step in range(self.max_steps):
            action = self._choose_action(user_message, scratchpad, session)
            if action["type"] == "final":
                session.transcript.append(Turn("final", action["text"]))
                return {
                    "answer": action["text"],
                    "tool_calls": tool_calls_made,
                    "citations": citations,
                    "steps": step + 1,
                    "transcript": session.transcript,
                }

            # Otherwise it's a tool call
            tc = action["tool_call"]
            session.transcript.append(Turn("tool_call", tc))
            result = self._dispatch_tool(tc, session)
            tool_calls_made.append({"tool": tc.tool, "arguments": tc.arguments,
                                    "result": result.result, "is_error": result.is_error})
            session.transcript.append(Turn("tool_result",
                                           {"tool": result.tool, "result": result.result}))

            # Track citations from search results.
            if tc.tool == "search_corpus" and isinstance(result.result, list):
                citations.extend([hit["doc"] for hit in result.result])

            # Add to scratchpad for the next decision.
            scratchpad += f"\n[{tc.tool}({tc.arguments})] -> {result.result}"

        # Hit max_steps without a final answer.
        return {
            "answer": "I couldn't reach a final answer within the step limit.",
            "tool_calls": tool_calls_made,
            "citations": citations,
            "steps": self.max_steps,
            "transcript": session.transcript,
        }

    # ----- The provider seam --------------------------------------------------

    def _choose_action(
        self,
        user_message: str,
        scratchpad: str,
        session: Session,
    ) -> dict[str, Any]:
        """Decide the next action: a tool call OR a final answer.

        STUB backend uses a deterministic rule-based selector so the demo is
        reproducible. CLAUDE backend delegates to the Anthropic SDK's tool-use
        loop.
        """
        if self.provider == "claude":
            return self._choose_action_claude(user_message, scratchpad, session)
        return self._choose_action_stub(user_message, scratchpad, session)

    def _choose_action_stub(
        self,
        user_message: str,
        scratchpad: str,
        session: Session,
    ) -> dict[str, Any]:
        msg = user_message.lower()

        # If we already executed a memory tool this turn, wrap up.
        if "[remember(" in scratchpad:
            return {"type": "final",
                    "text": "Saved. I'll remember that for the rest of this session."}
        if "[recall(" in scratchpad:
            return {"type": "final",
                    "text": self._synthesize_recall_answer(scratchpad)}

        # If the user is asking us to remember something -> save to memory.
        if "remember that" in msg or "remember:" in msg:
            after = user_message.split(":", 1)[-1] if ":" in user_message else user_message
            after = after.replace("remember that ", "", 1).strip().rstrip(".")
            words = after.split()
            key = "_".join(words[:3]).lower() if words else "note"
            value = after
            return {"type": "tool_call",
                    "tool_call": tools.ToolCall("remember",
                                                {"key": key, "value": value})}

        # If asks to recall, do that.
        if any(p in msg for p in ("what did i tell you about",
                                  "do you remember",
                                  "what's stored under",
                                  "recall")):
            for key in session.memory:
                if key.replace("_", " ") in msg or key in msg:
                    return {"type": "tool_call",
                            "tool_call": tools.ToolCall("recall", {"key": key})}
            if session.memory:
                return {"type": "tool_call",
                        "tool_call": tools.ToolCall(
                            "recall", {"key": next(iter(session.memory))})}

        # If we've already searched, return a final answer that uses the result.
        if "[search_corpus(" in scratchpad:
            return {
                "type": "final",
                "text": self._synthesize_answer(user_message, scratchpad),
            }

        # Otherwise: search. Use the longest content-bearing phrase from the
        # user's message as the query - the stub does naive substring search,
        # so a full sentence won't match. Pull out the meaningful tokens.
        query = self._extract_query(user_message)
        return {"type": "tool_call",
                "tool_call": tools.ToolCall("search_corpus",
                                            {"query": query, "k": 3})}

    @staticmethod
    def _extract_query(user_message: str) -> str:
        """Pick a search-friendly substring from a natural-language question.

        The stub's search_corpus does substring matching, so we strip the
        question scaffolding and keep the longest run of content words.
        Real Claude would do this naturally; the stub mimics it crudely so
        the demo behaves sensibly without API keys.
        """
        STOPWORDS = {
            "what", "what's", "whats", "is", "are", "the", "our", "your", "a",
            "an", "of", "for", "to", "do", "does", "how", "where", "when",
            "tell", "me", "about", "give", "show", "in", "on", "and", "or",
            "with", "that", "this", "these", "those", "did", "we", "i",
            "any", "all", "policy", "policies",
        }
        words = [w.strip(",.?!:;'\"()") for w in user_message.lower().split()]
        content = [w for w in words if w and w not in STOPWORDS]
        return " ".join(content[:2]) if content else user_message

    @staticmethod
    def _synthesize_recall_answer(scratchpad: str) -> str:
        marker = "[recall("
        idx = scratchpad.rfind(marker)
        if idx < 0:
            return "I checked memory but didn't find a match."
        result_idx = scratchpad.find("] -> ", idx)
        if result_idx < 0:
            return "I checked memory but didn't find a match."
        result_str = scratchpad[result_idx + 5:].split("\n")[0]
        if "'found': True" in result_str or '"found": True' in result_str:
            try:
                v = result_str.split("'value':")[1].split(",")[0].strip().strip("'\"")
            except (IndexError, ValueError):
                v = "(see memory)"
            return f"Yes - I have it stored: {v}"
        return "Nothing under that key yet."

    def _choose_action_claude(
        self,
        user_message: str,
        scratchpad: str,
        session: Session,
    ) -> dict[str, Any]:
        """Delegate the choice to the real Claude API via the Anthropic SDK.

        Production swap point. Requires:
            pip install -e ".[claude]"
            export ANTHROPIC_API_KEY=...

        Implementation sketch (uncomment and adapt when wiring to your real
        Anthropic SDK + the live MCP servers you want to expose):

            from anthropic import Anthropic
            client = Anthropic()
            messages = self._build_messages_from_transcript(session)
            response = client.messages.create(
                model=self.model,
                system=self.system,
                tools=[t.__dict__ for t in tools.TOOL_SCHEMAS.values()],
                messages=messages + [{"role": "user", "content": user_message}],
            )
            return self._parse_claude_response(response)

        Until that's wired, fall back to stub so the kit still runs.
        """
        return self._choose_action_stub(user_message, scratchpad, session)

    # ----- Tool dispatch ------------------------------------------------------

    def _dispatch_tool(self, tc: tools.ToolCall, session: Session) -> tools.ToolResult:
        try:
            if tc.tool == "search_corpus":
                hits = tools.search_corpus(
                    query=tc.arguments["query"],
                    corpus=self.corpus,
                    k=tc.arguments.get("k", 3),
                )
                return tools.ToolResult("search_corpus", hits)
            if tc.tool == "remember":
                r = tools.remember(session.memory,
                                   key=tc.arguments["key"],
                                   value=tc.arguments["value"])
                return tools.ToolResult("remember", r)
            if tc.tool == "recall":
                r = tools.recall(session.memory, key=tc.arguments["key"])
                return tools.ToolResult("recall", r)
            if tc.tool == "grade_response":
                r = tools.grade_response(
                    response=tc.arguments["response"],
                    rubric=tc.arguments["rubric"],
                )
                return tools.ToolResult("grade_response", r)
            return tools.ToolResult(tc.tool, f"Unknown tool: {tc.tool}", is_error=True)
        except Exception as ex:
            return tools.ToolResult(tc.tool, f"Error: {ex}", is_error=True)

    # ----- Final-answer synthesis (stub mode only) ----------------------------

    def _synthesize_answer(self, user_message: str, scratchpad: str) -> str:
        """Build a citation-bearing answer from the search results in scratchpad."""
        # Extract the latest search result list from scratchpad.
        # Format: [search_corpus({...})] -> [{...}, ...]
        marker = "[search_corpus("
        idx = scratchpad.rfind(marker)
        if idx < 0:
            return "I couldn't find anything relevant in the corpus."
        result_idx = scratchpad.find("] -> ", idx)
        if result_idx < 0:
            return "I couldn't find anything relevant in the corpus."
        result_str = scratchpad[result_idx + 5:].split("\n")[0].strip()

        # Build a short composed answer mentioning the top result.
        if "doc" not in result_str:
            return f"The corpus search for '{user_message}' returned no useful hits."
        # Naive: pull the first 'doc' substring as the citation.
        try:
            first_doc = result_str.split("'doc':")[1].split(",")[0].strip().strip("'\"")
        except (IndexError, ValueError):
            first_doc = "the corpus"
        return (f"Based on the corpus search, the most relevant source is "
                f"{first_doc}. (Source: search_corpus tool, citation = {first_doc}.)")
