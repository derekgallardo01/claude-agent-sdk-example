# Architecture

This kit is built around a single design pattern: **one swappable
selector, everything else provider-agnostic**.

## The agent loop

```
run_turn(session, user_message)
    repeat up to max_steps:
        action = _choose_action(user_message, scratchpad, session)
        if action.type == "final":  -> return final answer
        else:
            result = _dispatch_tool(action.tool_call, session)
            scratchpad += [tool_call] -> result
    return "couldn't reach a final answer"
```

The loop is in [src/claude_agent_example/agent.py](../src/claude_agent_example/agent.py)
and is about 50 lines.

## The provider seam

```python
def _choose_action(self, user_message, scratchpad, session):
    if self.provider == "claude":
        return self._choose_action_claude(user_message, scratchpad, session)
    return self._choose_action_stub(user_message, scratchpad, session)
```

That's the whole seam. Everything downstream — tool dispatch, memory,
transcript, citation tracking, step-limit safety — is the same code
path regardless of provider.

### Why a stub at all?

Three reasons:

1. **CI without keys.** The default backend runs in GitHub Actions free
   minutes with no secrets configured. Tests + evals pass deterministically.
2. **Reproducible demos.** The Pages live demo, the screenshots, and the
   portfolio card all need to render the same way every push.
3. **Onboarding speed.** A new contributor clones, runs, sees the agent
   work. No `ANTHROPIC_API_KEY` blocker. They wire the real provider
   after they understand the surface.

### The Claude path

`_choose_action_claude` ships as a documented sketch. Wire it up like this:

```python
from anthropic import Anthropic

client = Anthropic()
messages = self._build_messages_from_transcript(session)
response = client.messages.create(
    model=self.model,
    system=self.system,
    tools=[tool.__dict__ for tool in tools.TOOL_SCHEMAS.values()],
    messages=messages + [{"role": "user", "content": user_message}],
)
# Parse response.content for either a tool_use block or a text block
return self._parse_claude_response(response)
```

The `tools` list passed to the API is the same `TOOL_SCHEMAS` dict the
stub references — same JSON schemas, same arguments, same dispatcher.

## Tools

Four pure functions in [src/claude_agent_example/tools.py](../src/claude_agent_example/tools.py):

| Tool | Why it's the shape it is |
|---|---|
| `search_corpus` | Returns `{doc, score, snippet}` — the shape any real retrieval tool returns. The substring-then-word-overlap matcher is intentionally crude so the demo is deterministic; swap in `rag-over-docs-kit` for real retrieval. |
| `remember` / `recall` | Session-scoped memory dict. In a real Claude harness deployment, this would persist across sessions via `/mnt/memory/`. |
| `grade_response` | The **outcomes pattern** — the agent self-checks against a rubric before returning. Mirrors what a grader agent would do in a Claude Workforce setup. |

Tools are tested directly, without the agent loop:
[tests/test_tools.py](../tests/test_tools.py). That's the same separation
the Claude Agent SDK recommends — keep tools dumb and testable, push
orchestration into the loop.

## Memory model

`Session.memory` is a `dict[str, str]`. Within a session, every
`remember` writes are visible to every subsequent `recall`. Across
sessions, the dict is fresh — production would persist it.

The seam to persistent storage is one line:

```python
# At session boot:
session.memory = json.load(open("/mnt/memory/session-state.json"))

# At session shutdown:
json.dump(session.memory, open("/mnt/memory/session-state.json", "w"))
```

Skipped in the kit because the point of the kit is the agent surface,
not file IO.

## Transcript

Every step appends a `Turn(kind, content)` to `session.transcript`:

- `thinking` — internal note about what was received
- `tool_call` — the `ToolCall` object the selector chose
- `tool_result` — the `ToolResult` returned
- `final` — the answer text

For Claude integration, the transcript is what you'd feed back to the
API as message history. The structure is intentionally aligned with
the Anthropic SDK's `messages` shape.

## Citation tracking

The agent watches every tool call. When it sees `search_corpus`, it
extracts the `doc` field from each hit and appends to `citations`. That
list comes back in the final response so the caller can render footnotes
or sign-off doc references without re-parsing the answer.

## Step-limit safety

`max_steps` (default 8) is a hard cap. If the agent keeps tool-calling
without reaching a `final` action, it returns a graceful "couldn't reach
a final answer" instead of looping forever. This is the same
runaway-guard the SDK harness ships with — it just lives at the kit
level here so the same code works inside and outside the SDK.
