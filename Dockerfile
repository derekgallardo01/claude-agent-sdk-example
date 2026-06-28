FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/
COPY tests/ ./tests/
COPY evals/ ./evals/
COPY examples/ ./examples/
COPY README.md LICENSE ./

RUN pip install --no-cache-dir -e ".[claude]" pytest

# Default: run the scripted demo. Override with `docker run ... pytest` or
# `docker run ... claude-agent-example --interactive`.
CMD ["claude-agent-example"]
