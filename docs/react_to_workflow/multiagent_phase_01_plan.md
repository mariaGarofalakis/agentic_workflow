# Multi-Agent Migration Plan — Phase 1

## Goal
Introduce a new multi-agent runtime **without breaking the existing FastAPI + SSE chat flow**.

The key compatibility constraint is that the current frontend and `ChatService` expect an object with this method:

```python
async def run_stream(
    user_input: str,
    previous_response_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]
```

As long as the replacement runtime preserves that contract and emits the same event shapes (`chunk`, `completed`), the frontend chatbot can continue working unchanged.

---

## Current integration seam

### Current call chain

- `POST /api/chat/stream`
- `chat_router.chat_stream()`
- `ChatService.reply_stream()`
- `agent.run_stream(user_input=..., previous_response_id=...)`
- streamed SSE events back to frontend

### Important observation
`ChatService` is already decoupled from the internals of `AgentRunner`.
It only requires:

1. a streaming async iterator,
2. `chunk` events during generation,
3. a final `completed` event with `final_response_id`.

This is the main reason the migration can be incremental.

---

## Current architecture strengths

### Good parts already in place

- FastAPI lifespan bootstraps shared app dependencies once.
- The model client is abstracted behind `OpenAIResponsesClient`.
- Tool registration is centralized through `ToolRegistry`.
- Conversation persistence and response IDs are already tracked.
- SSE streaming is already integrated in the router and frontend flow.
- The current `AgentRunner` already implements a basic tool loop over the Responses API.

### Why this matters
You are **not** starting from scratch. You already have a production-friendly shell. The migration should therefore replace only the **agent runtime layer**, not the whole application.

---

## Main architectural issue today

`AgentRunner` is currently:

- a single-agent runtime,
- using one global tool list,
- with no concept of specialized worker roles,
- no shared planning state,
- no orchestrator decisions,
- no per-agent tool access control.

This makes it good for a general tool-using assistant, but not yet a reliable multi-agent trip planner.

---

## Phase 1 objective

Build the **runtime foundation** for multi-agent execution while preserving the external interface.

### We are **not** doing yet

- full trip planning workflow,
- destination selection logic,
- itinerary state machine,
- database schema changes,
- frontend changes.

### We **are** doing now

1. introduce agent-specific tool filtering,
2. introduce a reusable tool executor,
3. introduce a reusable base runner for tool-calling workers,
4. add a new top-level runner that still exposes `run_stream(...)`,
5. keep `ChatService` unchanged.

---

## Target design after Phase 1

### New layers

#### 1. Global registry
Keep your existing registry auto-discovery pattern.

Responsibility:
- discover all available tools,
- register them once,
- act as the source of truth.

#### 2. ToolSet / filtered tool view
A lightweight wrapper over the global registry that exposes only the tools allowed for one agent.

Examples:
- destination agent: `web_search`, `wiki_search`, `get_weather_forecast`
- budget agent: `calculator`
- itinerary agent: maybe no external tools initially

#### 3. ToolExecutor
A small runtime object that:
- parses tool arguments,
- executes handlers,
- catches exceptions,
- serializes outputs safely.

#### 4. Worker base runtime
A reusable class for tool-enabled specialist agents.

Responsibility:
- send prompt + tools to model,
- execute function calls,
- continue until final response,
- support both text and structured outputs.

#### 5. MultiAgentWorkflowRunner
This is the new drop-in replacement for `AgentRunner`.

Important:
- it will still expose `run_stream(...)`,
- it will still yield `chunk` and `completed` events,
- internally it can evolve from “single orchestrated worker” to “true multi-agent workflow” over time.

---

## Why preserve `run_stream(...)`

Because that is the seam that protects the rest of the app.

If we preserve:

```python
async def run_stream(
    user_input: str,
    previous_response_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]
```

then these pieces do not need to change in Phase 1:

- `chat_router`
- `ChatService`
- SSE event generator
- frontend streaming consumption
- conversation/message persistence logic

That is the safest migration path.

---

## Concrete Phase 1 file changes

### New files to add

```text
app/tools/core/executor.py
app/tools/core/selection.py
app/agents/base.py
app/agents/worker.py
app/agents/multiagent_runner.py
```

### Existing files to update

```text
app/tools/core/registry.py
app/main.py (or wherever lifespan bootstrapping lives)
```

### Files intentionally unchanged in Phase 1

```text
app/api/chat_router.py
app/services/chat_service.py
app/repositories/*
frontend chatbot streaming logic
```

---

## Proposed Phase 1 bootstrapping change

### Today

```python
agent = AgentRunner(
    llm=llm,
    registry=registry,
    max_tool_iterations=settings.max_tool_iterations,
)
```

### After Phase 1

```python
agent = MultiAgentWorkflowRunner(
    llm=llm,
    registry=registry,
    max_tool_iterations=settings.max_tool_iterations,
)
```

That should be the only required change at app startup for the first migration step.

---

## Event compatibility requirements

The new runner must emit the same event shape currently expected by `ChatService`.

### Streaming chunk event

```python
{"type": "chunk", "content": "..."}
```

### Final completion event

```python
{"type": "completed", "final_response_id": "..."}
```

This compatibility requirement is strict.

---

## Internal design direction for the new runner

In Phase 1, `MultiAgentWorkflowRunner` should be intentionally simple.

### Recommended internal flow

1. Build an orchestrator-like worker.
2. Give it a filtered toolset.
3. Run a Responses API tool loop.
4. Stream chunks back exactly like the current runner.
5. Keep room to later call specialist workers internally.

At this stage, the new runner may still behave similarly to a single advanced agent, but the code structure must be ready for multi-agent composition.

---

## Risks to avoid in Phase 1

### 1. Do not change the router contract
No API contract changes yet.

### 2. Do not change DB persistence flow
`ChatService` already has a safe transaction pattern.
Keep it.

### 3. Do not add agent-to-agent free-form chat yet
That would add complexity too early.

### 4. Do not let every worker see every tool
Per-agent tool scoping should be added now, even if only lightly used at first.

### 5. Do not move tool orchestration into the provider
The provider should remain a low-level OpenAI wrapper.

---

## Success criteria for Phase 1

Phase 1 is successful when:

- the frontend chat still streams normally,
- `ChatService` does not need to change,
- `AgentRunner` can be replaced by `MultiAgentWorkflowRunner`,
- tools can be scoped per agent,
- the runtime can support specialist agents in the next phase.

---

## What comes after Phase 1

### Phase 2
Shared planning state and orchestrator decisions.

Expected additions:
- `TripRequest`
- `TripPlanState`
- `OrchestratorAction`
- explicit worker delegation

### Phase 3
Specialist agents for:
- destination research,
- weather analysis,
- budget estimation,
- itinerary drafting.

### Phase 4
Validation, replanning, and evaluation.

---

## Implementation note

The best migration strategy is:

- preserve the outside interface,
- improve the inside architecture,
- switch one layer at a time.

That fits your current backend very well.
