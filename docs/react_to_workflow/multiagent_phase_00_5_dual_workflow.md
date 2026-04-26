# Multi-Agent Migration Phase 0.5 — Dual-Workflow Compatibility

## Goal

Preserve **both** of these workflows during the migration:

1. the current **single-agent tool-calling workflow**
2. the future **multi-agent vacation-planning workflow**

without breaking:

- the FastAPI app startup
- the current SSE `/api/chat/stream` endpoint
- the frontend chatbot
- conversation persistence
- `last_response_id` handling
- the existing database services and repositories

---

## What we learned from the additional code

### `ConversationService`
`ConversationService` is independent of the agent implementation. It only creates conversations and validates the user. That means it does **not** need to change for the migration.

### `ChatService`
`ChatService` depends on one thing that matters for compatibility:

```python
async for event in self.agent.run_stream(
    user_input=message,
    previous_response_id=previous_response_id,
):
```

This is the key seam.

Because `ChatService` only expects an object with `run_stream(...)`, we can preserve compatibility by introducing a **common runner interface** and then plugging in either:

- `AgentRunner` (existing single-agent runtime)
- `MultiAgentWorkflowRunner` (new runtime)

---

## Decision

We will **not** replace the old workflow immediately.

We will support both workflows through one abstraction:

- `ChatService` remains unchanged
- routers remain unchanged
- frontend remains unchanged
- app lifespan chooses which runner to mount into `app.state.agent`

---

## Recommended design

## 1. Introduce a runner protocol / interface

Create a small shared interface that both runners satisfy.

Example:

```python
from collections.abc import AsyncIterator
from typing import Any, Protocol


class ChatAgentRunner(Protocol):
    async def run_stream(
        self,
        user_input: str,
        previous_response_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        ...
```

This gives us a stable contract for:

- `AgentRunner`
- `MultiAgentWorkflowRunner`

`ChatService` can then type against the protocol instead of the concrete old class.

---

## 2. Preserve event contract

Both runners must emit the same stream event format:

### chunk event
```json
{"type": "chunk", "content": "..."}
```

### completed event
```json
{"type": "completed", "final_response_id": "..."}
```

This keeps the current router and frontend working as-is.

Optional future internal events may exist, but the public SSE shape should remain unchanged for now.

---

## 3. Keep `previous_response_id` support in both modes

Your current architecture persists `conversation.last_response_id` and sends it into the next model turn.

We should preserve this behavior in both runners because it provides continuity for the Responses API conversation state.

That means the multi-agent workflow runner should still expose a top-level `final_response_id` for storage, even if internally it orchestrates multiple agent calls.

### Practical rule
The workflow runner should choose one of these strategies:

#### Strategy A — single top-level response chain
The orchestrator owns the conversation chain and worker calls are internal/stateless.  
This is the preferred approach for compatibility.

#### Strategy B — multiple internal chains
Workers maintain separate internal chains, but the runner still returns the orchestrator's final response id for the main chat thread.

For your system, **Strategy A** is the cleanest first implementation.

---

## 4. Add config-based workflow selection

Add a setting like:

```python
agent_workflow: str = "single"
```

Allowed values:
- `single`
- `multi`

Then in `lifespan(...)`, instantiate the correct runner.

Example:

```python
if settings.agent_workflow == "multi":
    agent = MultiAgentWorkflowRunner(...)
else:
    agent = AgentRunner(...)
```

This lets you:

- deploy safely
- test locally
- switch back instantly
- compare behaviors
- run A/B testing later if desired

---

## 5. Keep one shared global tool registry

Your existing auto-registration model is good and should remain the source of truth.

We should **not** create separate global registries for each workflow.

Instead:

- global `ToolRegistry` is built once
- old `AgentRunner` can continue using the full registry
- new multi-agent workflow can create filtered `ToolSet` views per worker

This allows both systems to coexist.

---

## Compatibility architecture

## Current
```text
Frontend Chatbot
  -> /api/chat/stream
  -> ChatService
  -> AgentRunner
  -> OpenAIResponsesClient + ToolRegistry
```

## Target
```text
Frontend Chatbot
  -> /api/chat/stream
  -> ChatService
  -> ChatAgentRunner (interface)
       -> AgentRunner                 # old mode
       -> MultiAgentWorkflowRunner    # new mode
  -> OpenAIResponsesClient + ToolRegistry/ToolSets
```

---

## What stays unchanged

These parts should remain unchanged in the early phases:

- `chat_router`
- `conversation_router`
- `ConversationService`
- `ChatService` business flow
- frontend SSE handling
- DB persistence model
- `last_response_id` storage
- tool auto-discovery bootstrap

---

## What changes first

### Phase 1
- introduce `ChatAgentRunner` protocol
- refactor `ChatService` typing to depend on the protocol instead of concrete `AgentRunner`
- add `ToolSet`
- add `ToolExecutor`
- keep old `AgentRunner` fully working

### Phase 2
- add `MultiAgentWorkflowRunner`
- keep its public `run_stream(...)` contract identical
- begin using agent-specific tool subsets internally

### Phase 3
- add orchestrator + worker agents + shared state
- preserve the same chat endpoint and persistence flow

---

## Recommended code changes

## A. New shared protocol

Suggested file:

```text
app/agent/interfaces.py
```

Suggested contents:

```python
from collections.abc import AsyncIterator
from typing import Any, Protocol


class ChatAgentRunner(Protocol):
    async def run_stream(
        self,
        user_input: str,
        previous_response_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        ...
```

---

## B. Update `ChatService` type hints only

Current:

```python
from backend.app.agent.react_streamer import AgentRunner
```

Recommended:

```python
from app.agent.interfaces import ChatAgentRunner
```

Then:

```python
class ChatService:
    def __init__(
        self,
        agent: ChatAgentRunner,
        session: AsyncSession,
    ) -> None:
        ...
```

This is a low-risk change because the runtime behavior stays the same.

---

## C. Lifespan runner selection

Update app startup to choose the runner based on config.

Pseudo-code:

```python
registry = build_registry()
llm = OpenAIResponsesClient(...)

if settings.agent_workflow == "multi":
    agent = MultiAgentWorkflowRunner(
        llm=llm,
        registry=registry,
        max_tool_iterations=settings.max_tool_iterations,
    )
else:
    agent = AgentRunner(
        llm=llm,
        registry=registry,
        max_tool_iterations=settings.max_tool_iterations,
    )

app.state.agent = agent
```

---

## D. Keep `AgentRunner` as a compatibility adapter

Do not delete or heavily rewrite it yet.

Treat it as:

- the stable legacy workflow
- a fallback path
- a behavioral baseline for testing the new workflow

---

## Why this is the right migration strategy

A hard cutover would couple too many risks:

- new orchestration logic
- new tool selection logic
- new prompts
- new state management
- production chat flow

By preserving both runners, you can migrate safely:

- compare outputs
- rollback easily
- test streaming behavior separately
- keep the frontend stable

---

## Notes on conversation continuity

Because your DB stores:
- user messages
- assistant messages
- `last_response_id`

the safest approach is:

- let both workflows remain compatible with the same persistence model
- do not change repositories yet
- do not introduce workflow-specific DB schema changes in early phases

If later you want richer internal workflow memory, that should be stored separately from the main chat persistence.

---

## Success criteria for this phase

This phase is successful when:

1. `ChatService` works with either runner
2. frontend sees no API or SSE contract changes
3. old single-agent mode still works exactly as before
4. new multi-agent mode can be turned on by configuration
5. both modes can share the same tool registration/discovery system

---

## Next implementation phase

After this document, the next code phase should implement:

1. `ChatAgentRunner` protocol
2. `ToolSet` support on top of `ToolRegistry`
3. `ToolExecutor`
4. a no-op `MultiAgentWorkflowRunner` skeleton that still satisfies `run_stream(...)`
5. config-based runner selection in `lifespan`

That gives you dual-mode support before we add real orchestration.
