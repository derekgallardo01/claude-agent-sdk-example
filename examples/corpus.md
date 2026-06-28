# Sample corpus

The CLI demo uses an in-memory corpus shaped like an M365 consultant's
internal knowledge base. To run the agent against your own docs, pass a
different dict into `Agent(corpus=...)`.

The five built-in docs are:

| Doc | Topic |
|---|---|
| `tenant-baseline.md` | Conditional Access, MFA, DLP coverage, default sensitivity label |
| `copilot-rollout.md` | Phased rollout, adoption metrics, weekly active prompts |
| `data-residency.md` | EU geography commitments, Azure OpenAI service boundary |
| `sharepoint-hygiene.md` | Orphaned documents, archived sites, external sharing |
| `incident-response.md` | Credential compromise runbook |

The corpus is small on purpose - the point of the kit is the **shape of
the agent loop**, not the retrieval quality. For a serious retrieval
backend, pair this kit with [rag-over-docs-kit](https://github.com/derekgallardo01/rag-over-docs-kit),
which has chunking, TF-IDF, query-aware re-ranking, and a golden eval
harness.

## Swap in your own corpus

```python
from claude_agent_example.agent import Agent, Session

my_docs = {
    "policy-1.md": "Long body text here...",
    "policy-2.md": "More body text...",
}
agent = Agent(corpus=my_docs)
session = Session()
print(agent.run_turn(session, "What does policy 1 say?"))
```

That's it - no other code changes needed. The tools are corpus-agnostic.
