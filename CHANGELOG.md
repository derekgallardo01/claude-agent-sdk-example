# Changelog

Notable changes to the Claude Agent SDK example. Dates are when the
change landed on `main`.

## 2026-06-28 — Initial public release (v1.0.0)
- `Agent` loop with provider seam (`_choose_action`) — stub-by-default,
  one method swap to wire the real Claude Agent SDK
- 4 tools: `search_corpus`, `remember`, `recall`, `grade_response`
- Session-scoped memory; transcript with `thinking`/`tool_call`/
  `tool_result`/`final` turn kinds; citation tracking;
  step-limit safety
- `claude-agent-example` CLI: scripted demo + `--interactive` REPL +
  `--json` output
- 16 unit tests (9 across the tool surface, 7 across the agent loop)
- Golden eval harness (`evals/run.py` + `evals/golden.json`) with 5
  cases — CI gates on 100% pass
- CI on Python 3.10/3.11/3.12 (tests + evals + scripted demo smoke)
- `pyproject.toml` with `[claude]` optional extra for the Anthropic SDK
- Docs trio: `getting-started`, `architecture`, `customization`,
  `evaluation`, `diagrams`, `faq`
- OSS niceties: `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`,
  `CITATION.cff`, `.editorconfig`, `.devcontainer/devcontainer.json`,
  `.github/ISSUE_TEMPLATE/*`, `.github/PULL_REQUEST_TEMPLATE.md`,
  `.github/dependabot.yml`
- `Dockerfile` for container demo runs
- README badges: CI + License (MIT) + Python (3.10+) + Open in Codespaces
