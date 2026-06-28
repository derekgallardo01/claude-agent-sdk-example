# Getting started

Five minutes to a working agent loop on your machine, zero API keys required.

## Install

```bash
git clone https://github.com/derekgallardo01/claude-agent-sdk-example.git
cd claude-agent-sdk-example
pip install -e .
```

That's it for the default path. The kit is stdlib-only on the stub provider.

## Run the demo

```bash
claude-agent-example
```

You should see four scripted turns: a search, a remember, a recall, and
another search — each printing the answer, the tools the agent picked,
and any citations.

## Run the tests

```bash
python -m pytest -q
```

16 tests across the tool surface and the agent loop. They run in under
a second because the stub provider is deterministic — no network.

## Run the evals

```bash
python evals/run.py
```

5 golden cases that assert which tool the agent picks, which document
it cites, and whether the rubric phrases appear in the answer. CI gates
on a 100% pass rate.

## Interactive REPL

```bash
claude-agent-example --interactive
```

Talk to the agent against the built-in M365 consultant corpus. Try:

```
> data residency
> remember that the pilot kick-off is 2026-07-15
> do you recall the pilot date?
> conditional access
```

## Wire to the real Claude API

1. Install the optional Claude extra:
   ```bash
   pip install -e ".[claude]"
   ```

2. Set your key + flip the provider env var:
   ```bash
   export ANTHROPIC_API_KEY=sk-...
   export CLAUDE_AGENT_PROVIDER=claude
   ```

3. Implement `_choose_action_claude` in [src/claude_agent_example/agent.py](../src/claude_agent_example/agent.py)
   per the docstring sketch — about 30 lines of glue against the
   Anthropic SDK's tool-use loop. The tools are already declared in
   `TOOL_SCHEMAS`; you're just wiring the LLM's tool picks back to the
   same dispatcher.

4. Re-run `claude-agent-example` — it'll now route through the real API.

The tests stay green either way because they pin the provider to `stub`
explicitly.

## Next steps

- Read [Architecture](architecture.md) for the agent loop walkthrough.
- Read [Customization](customization.md) to swap the corpus or add tools.
- Read [Evaluation](evaluation.md) to gate CI on agent behaviour.
