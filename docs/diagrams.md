# Diagrams

GitHub renders Mermaid natively. These render on the README and in this file.

## End-to-end flow

```mermaid
flowchart LR
    U[User question] --> A["Agent.run_turn()"]
    A -->|"_choose_action()"| P{Provider?}
    P -- "stub (default)" --> S["_choose_action_stub()<br/>rule-based"]
    P -- "claude" --> C["_choose_action_claude()<br/>Anthropic SDK tool-use loop"]
    S --> T{Tool call or final?}
    C --> T
    T -- "tool_call" --> D["_dispatch_tool()<br/>search / remember / recall / grade"]
    D --> M[(Session memory)]
    D --> R[Tool result]
    R --> A
    T -- "final" --> F[Final answer + citations]
```

## The loop, step by step

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant T as Tool
    participant M as Memory

    U->>A: question
    A->>A: thinking (record)
    loop max_steps
        A->>A: _choose_action()
        alt picked a tool
            A->>T: tool_call(args)
            T->>M: read/write (if memory tool)
            T-->>A: tool_result
            A->>A: record in transcript + scratchpad
        else picked final
            A-->>U: answer + citations + transcript
        end
    end
```

## Stub vs Claude

```mermaid
flowchart TB
    subgraph Stub["stub provider (default)"]
        direction TB
        S1[Match keywords in user_message]
        S2["'remember' / 'recall' / 'search' / fallback"]
        S3[Hand-coded action dict]
        S1 --> S2 --> S3
    end

    subgraph Claude["claude provider"]
        direction TB
        C1[Build messages from transcript]
        C2["Anthropic.messages.create()<br/>with TOOL_SCHEMAS"]
        C3[Parse tool_use or text block]
        C4[Action dict — same shape as stub]
        C1 --> C2 --> C3 --> C4
    end

    Stub -. "same action shape" .- Claude
```

The action dict is identical — `{"type": "tool_call", "tool_call": ToolCall(...)}`
or `{"type": "final", "text": str}`. Downstream code doesn't know
which path produced it.

## Session lifecycle

```mermaid
stateDiagram-v2
    [*] --> Idle: Session()
    Idle --> Running: run_turn(msg)
    Running --> ToolDispatch: choose=tool
    ToolDispatch --> Running: result added
    Running --> Final: choose=final
    Running --> StepLimitHit: max_steps reached
    Final --> Idle: response returned
    StepLimitHit --> Idle: graceful failure
    Idle --> [*]: session ends<br/>(memory could persist)
```

## Repo shape

```mermaid
flowchart TB
    R[claude-agent-sdk-example]
    R --> SRC[src/claude_agent_example/]
    SRC --> A[agent.py — loop + seam]
    SRC --> T[tools.py — 4 pure tools + schemas]
    SRC --> C[cli.py — demo + REPL]
    R --> TESTS[tests/]
    TESTS --> TT[test_tools.py]
    TESTS --> TA[test_agent.py]
    R --> EV[evals/]
    EV --> GJ[golden.json]
    EV --> ER[run.py]
    R --> DOCS[docs/]
    R --> CI[.github/workflows/ci.yml]
    R --> DK[Dockerfile]
```
