# FAQ

## Is this the real Claude Agent SDK?

No. This is a **kit shaped like** what you'd build on top of the SDK,
designed so the entire orchestration runs without needing the SDK or an
API key. The Claude provider seam (`_choose_action_claude`) is a
documented stub with an implementation sketch — you wire the real SDK
in 30 lines when you're ready.

The point is to show the **shape** of an agent build (coordinator +
tools + memory + outcomes) without the tooling burden of getting the
SDK set up before you can read the code.

## Why not just use the SDK examples?

The SDK examples assume you have a key, you're online, and you're
willing to burn tokens to run them. This kit:

- Runs in CI on every push with no secrets configured.
- Has deterministic outputs so the Pages live demo + screenshots can
  regenerate on every push.
- Has a golden eval harness that gates merges on behavior, not just
  on `python -c "import"` succeeding.
- Is stdlib-only on the default path (no `requirements.txt` debt).

You should still read the official SDK examples for production wiring
patterns. This kit is the on-ramp.

## When would I use this in a real engagement?

Three patterns:

1. **Starter template.** Fork it, swap the corpus + tools to match the
   client's domain, point `_choose_action_claude` at the real SDK,
   ship.
2. **Eval harness for a real build.** Use `evals/run.py`'s shape as the
   template for the client's own behavior gates. The CI gating pattern
   is the part most teams skip and most regret.
3. **Tutorial.** When you're explaining the agent-loop shape to a
   non-engineer stakeholder, this kit gives you a runnable thing to
   demo without "we need to provision an API key first" friction.

## How is this different from `m365-audit-mcp`?

That repo is the **server side** — it exposes tools an agent consumes.
This repo is the **agent side** — it consumes tools (with the same
shape an MCP server would expose). Pair them:

```
[claude-agent-sdk-example agent] --calls--> [m365-audit-mcp server]
```

The agent's `search_corpus` tool in this kit is a stand-in for what an
MCP-connected tool would look like. To wire the actual MCP server,
replace `search_corpus`'s body with an MCP client call.

## How is this different from `rag-over-docs-kit`?

`rag-over-docs-kit` is a **retrieval system** — chunking, TF-IDF,
re-ranking, golden eval harness for retrieval quality.

This kit is an **agent loop** — picks which tool to call, dispatches,
tracks memory + citations.

They compose: drop `rag-over-docs-kit` in as the body of `search_corpus`
in this kit. You get a real retriever wired into a real agent loop.

## How is this different from `copilot-studio-support-agent`?

`copilot-studio-support-agent` is the same loop pattern running
**inside Microsoft's hosted Copilot Studio runtime** — yaml-defined
topics, knowledge connectors, the Copilot grounding layer doing
retrieval.

This kit is **the SDK build** — Python, your own loop, your own tools,
your own memory. Same architectural pattern, different deployment
substrate. M365 consultants need to be fluent in both.

## Does it really need 16 tests for this much code?

The agent loop has more states than the line count suggests:
provider-routing, tool-call vs final, citation tracking, multi-turn
memory persistence, step-limit safety. Each of those breaks
independently when you refactor, and each break is hard to debug from
the outside ("the agent answered weird again").

The tests are the regression net. 16 isn't a lot if you've ever
debugged "the LLM stopped citing sources after we changed the system
prompt three sprints ago".

## How long until the Claude provider sketch is fully implemented?

Deliberately left as an exercise — about 30 lines of Anthropic SDK glue.
Implementing it for you would tie the kit to a specific SDK version and
make it look "done" in a way that hides the seam. The point is that the
seam is one method; you wire it once for your stack.

If you want a worked example, the Anthropic SDK docs at
[docs.anthropic.com](https://docs.anthropic.com) have the tool-use loop
spelled out — the only translation needed is parsing the response into
the kit's action dict shape.

## Can I use this with a different model provider (OpenAI, Gemini, etc)?

Yes — add a third branch in `_choose_action`:

```python
if self.provider == "openai":
    return self._choose_action_openai(user_message, scratchpad, session)
```

The tool dispatcher, memory, transcript, and citation tracking are all
provider-agnostic. You're only writing the selector adapter per
provider.
