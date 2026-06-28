# Customization

How to shape this kit for a real engagement.

## Swap the corpus

The CLI loads a built-in M365 consultant corpus from
[src/claude_agent_example/cli.py](../src/claude_agent_example/cli.py)
(`SAMPLE_CORPUS`). To use your own:

```python
from claude_agent_example.agent import Agent, Session

my_corpus = {
    "policy-1.md": "Long body text...",
    "playbook.md":  "Another long body...",
}

agent = Agent(corpus=my_corpus)
session = Session()
result = agent.run_turn(session, "your question")
```

For a serious retrieval backend (chunking, TF-IDF, re-ranking, golden
eval gating), drop in [rag-over-docs-kit](https://github.com/derekgallardo01/rag-over-docs-kit)
and replace the `search_corpus` body with a call into its `ragkit.search()`.
The shape returned (`[{doc, score, snippet}, ...]`) is the same.

## Add a tool

Three steps:

1. **Write the pure function** in `tools.py`:

```python
def lookup_user(user_id: str, directory: dict) -> dict:
    return directory.get(user_id, {"error": "not found"})
```

2. **Add its schema to `TOOL_SCHEMAS`** so the LLM knows it exists:

```python
"lookup_user": Tool(
    name="lookup_user",
    description="Look up a user by their ID in the directory.",
    input_schema={
        "type": "object",
        "properties": {"user_id": {"type": "string"}},
        "required": ["user_id"],
    },
),
```

3. **Wire dispatch** in `agent.py::_dispatch_tool`:

```python
if tc.tool == "lookup_user":
    return tools.ToolResult("lookup_user",
                            tools.lookup_user(tc.arguments["user_id"], self.directory))
```

That's it. The Claude provider path automatically picks up the new tool
because it iterates `TOOL_SCHEMAS`. Add a test in `tests/test_tools.py`
and an eval case in `evals/golden.json` and you're done.

## Change the system prompt

Pass `system="..."` to `Agent()`:

```python
agent = Agent(
    corpus=my_corpus,
    system="You are a financial-services compliance assistant. Always cite policy IDs.",
)
```

The stub provider ignores the system prompt (it's rule-based), but the
Claude provider uses it directly. Production swap behaves accordingly.

## Tighten the step limit

```python
agent = Agent(corpus=my_corpus, max_steps=3)
```

Useful when you want to fail fast on complex questions and route them
to a human, instead of letting the agent grind through tool calls.

## Persist memory across sessions

Add to your session lifecycle:

```python
import json
from pathlib import Path

MEM_FILE = Path("/mnt/memory/session.json")

def load_session(user_id: str) -> Session:
    s = Session(user_id=user_id)
    if MEM_FILE.exists():
        s.memory = json.loads(MEM_FILE.read_text())
    return s

def save_session(s: Session) -> None:
    MEM_FILE.write_text(json.dumps(s.memory))
```

The kit doesn't ship this because every deployment has different
persistence (Redis, Postgres, the SDK harness's mounted volume, etc.) —
but the seam is one read and one write at session boundaries.

## Pin a specific Claude model

```python
agent = Agent(corpus=my_corpus, provider="claude", model="claude-opus-4-7")
```

The kit's default is `claude-opus-4-7` (latest as of writing). Pin
explicitly when you need reproducibility across SDK updates.

## Use a different selector strategy in the stub

`_choose_action_stub` is rule-based today. If you want to test a
different orchestration shape (e.g. "always grade before final"), edit
that method — the rest of the loop doesn't care:

```python
# Force a grading pass before any final answer
if "[search_corpus(" in scratchpad and "[grade_response(" not in scratchpad:
    return {"type": "tool_call",
            "tool_call": tools.ToolCall("grade_response", {
                "response": self._synthesize_answer(user_message, scratchpad),
                "rubric": ["citation", "specific", "actionable"],
            })}
```

This is how the **outcomes pattern** gets enforced — the orchestrator
self-checks before returning.
