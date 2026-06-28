# Evaluation

The kit ships a golden eval harness that gates CI on agent behaviour,
not just on whether the code compiles.

## What gets checked

Per [evals/golden.json](../evals/golden.json), each case asserts:

1. **`expect_tool`** — did the agent pick the right tool for this question?
2. **`expect_citations`** — did the answer cite the right document(s)?
3. **`rubric`** — do the required phrases appear in the final answer?

A case passes when all three hold. CI fails on anything less than 100%.

## Running

```bash
python evals/run.py
```

Output:

```
Running 5 eval cases against provider=stub

  PASS  data-residency                  tool=True  cites=True  rubric=True
  PASS  tenant-baseline                 tool=True  cites=True  rubric=True
  PASS  sharepoint-hygiene              tool=True  cites=True  rubric=True
  PASS  incident-runbook                tool=True  cites=True  rubric=True
  PASS  remember-pilot-date             tool=True  cites=True  rubric=True

5/5 passed (100%)
```

Non-zero exit code if any case fails — so it works straight in CI.

## Adding a new eval case

Edit `evals/golden.json`:

```json
{
  "id": "your-new-case",
  "question": "the question text",
  "expect_tool": "search_corpus",
  "expect_citations": ["doc-id.md"],
  "rubric": ["phrase that must appear in the final answer"]
}
```

Re-run `python evals/run.py` to verify. If it fails, the agent's
behaviour drifted — that's the eval doing its job. Fix the agent or
update the expectation, whichever is correct.

## Why a separate eval suite (vs just tests)

Tests verify code shape — "did the function return the right type, with
the expected keys". Evals verify behaviour shape — "did the agent
actually pick the right tool for the right question, and produce a
citation-bearing answer".

These move on different cadences. Tests change when you refactor; evals
change when you change the agent's intended behaviour. Mixing them
makes both noisier. Keeping them separate lets you ship a refactor
without re-thinking the eval pass rate, and lets you change behaviour
deliberately by editing one JSON file.

## Running evals against the real Claude API

```bash
pip install -e ".[claude]"
export ANTHROPIC_API_KEY=sk-...
CLAUDE_AGENT_PROVIDER=claude python evals/run.py
```

The same cases run; the selector changes. Expect a few flips
(particularly on the search cases where the LLM might phrase the answer
differently than the stub) — the eval failure is the signal to either
tighten the rubric or accept the LLM's variance.

This is how you watch model upgrades: re-run the eval suite after
flipping to a new Claude version, see which cases changed, decide if
it's drift or improvement.

## The outcomes pattern

The fourth tool, `grade_response`, is the in-loop version of an eval.
The agent itself can grade a draft against a rubric before returning:

```python
draft = "Our tenant data stays in the EU and CA is enabled."
grade = tools.grade_response(draft, rubric=["EU", "Conditional Access", "MFA"])
# {'passed': 1, 'total': 3, 'rate': 0.33, 'per_criterion': [...]}
```

If the rate is low, the agent can search again before committing.
That's the **outcomes pattern** — orchestrator self-grades, retries if
the grade is below threshold, returns only when good enough.

Not enforced in the default stub flow (it would mask the simpler
search-and-cite path), but documented in
[customization.md](customization.md) under "Use a different selector
strategy in the stub" so you can switch it on for high-stakes answers.
