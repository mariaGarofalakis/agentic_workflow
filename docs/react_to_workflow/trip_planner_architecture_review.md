# Vacation Planner Chatbot: Current Architecture Review and Multi-Agent Evolution Plan

## Goal

This document explains the **current backend architecture** based on the code you shared, identifies the main extension points, and proposes a **future multi-agent workflow** that can be attached with minimal disruption to your existing FastAPI + streaming frontend chatbot setup.

The target outcome is:

- keep the current frontend chat UX,
- keep the current `/api/chat/stream` SSE flow,
- keep conversation creation and persistence patterns,
- replace the current single-runner agent with a multi-agent workflow engine,
- make the new workflow easy to introduce incrementally.

---

## 1. Current architecture overview

From the code shared so far, the current system has these main layers.

### 1.1 Application startup

At FastAPI startup, the app:

1. builds a global tool registry,
2. creates a single `OpenAIResponsesClient`,
3. creates a single `AgentRunner`,
4. stores it on `app.state.agent`,
5. initializes a dev user if auth is disabled.

### 1.2 HTTP/API layer

The FastAPI app exposes:

- `POST /api/chat/stream`
- `POST /api/conversations`
- user routes
- `GET /health`

The frontend chatbot currently depends on the **chat streaming endpoint**, which uses `StreamingResponse` and server-sent events.

### 1.3 Chat flow

The current chat route:

- receives `conversation_id` and `message`,
- calls `ChatService.reply_stream(...)`,
- streams JSON events over SSE,
- catches failures and emits an `error` event.

This is important because it means the frontend is already built around an **event-streaming contract**, which is exactly what we should preserve.

### 1.4 Tool system

The tool system has:

- auto-discovery via `pkgutil.iter_modules(...)`,
- registration using `register_*` functions,
- a `ToolRegistry` that stores tool schema + async handler,
- tools registered globally at startup.

This is a strong foundation for agent specialization later.

### 1.5 LLM provider layer

`OpenAIResponsesClient` is already a useful abstraction over the Responses API. It supports:

- streaming responses,
- final non-user-facing response retrieval,
- tool definitions,
- previous response chaining,
- structured output formatting.

This provider abstraction is exactly the right place to keep model-vendor specifics out of your agent/workflow logic.

### 1.6 Agent layer today

The current app uses:

- one `AgentRunner` instance,
- initialized once during app lifespan,
- likely acting as the main coordinator for LLM + tools + streaming.

Even though you have not yet shared `AgentRunner`, the startup and route shape strongly suggest the current system is a **single-agent runtime** with tool access.

---

## 2. Current strengths

Your current architecture already has several good design decisions.

### 2.1 Clear startup composition

The app composition is easy to follow:

- tool registry created once,
- provider created once,
- agent runner created once,
- injected into app state.

That makes the eventual migration easier.

### 2.2 Streaming-first chat API

The frontend already consumes SSE. That is excellent for agent systems because it allows you to stream:

- assistant text,
- progress updates,
- tool activity,
- planning stages,
- structured workflow events.

### 2.3 Tool registry is extensible

Your registry is generic and async-friendly. That means it can support:

- a single-agent runtime,
- multi-agent specialized tool access,
- workflow-driven tool execution,
- tool permission scoping per agent.

### 2.4 Provider abstraction is separate

You did not hard-wire OpenAI calls directly inside routes or services. That is a major positive. It means the upcoming multi-agent workflow can depend on the same provider without affecting the HTTP layer.

### 2.5 Good fit for incremental migration

Because the API boundary is already stable, you do **not** need to redesign the frontend to support multi-agent behavior.

---

## 3. Current likely architecture diagram

Based on the shared code, the current data flow is approximately:

```text
Frontend Chat UI
    -> POST /api/chat/stream
        -> chat_router
            -> ChatService.reply_stream(...)
                -> app.state.agent (AgentRunner)
                    -> OpenAIResponsesClient
                    -> ToolRegistry
                    -> tool handlers
                -> yields SSE events
    <- StreamingResponse(text/event-stream)
```

Conversation creation is separate:

```text
Frontend
    -> POST /api/conversations
        -> conversation_router
            -> ConversationService.create_conversation(...)
                -> persistence layer / DB
```

---

## 4. Main architectural seam to preserve

The most important seam in your system is this one:

```text
ChatService.reply_stream(...) -> agent-like runtime -> SSE events
```

That seam is where the migration should happen.

You do **not** want the frontend to know whether the backend is powered by:

- one agent,
- an orchestrator with many workers,
- a graph workflow,
- or a deterministic pipeline.

The frontend should continue to see a stream of chat events.

So the replacement should be:

```text
ChatService.reply_stream(...) -> MultiAgentWorkflowRunner -> SSE events
```

not:

```text
Frontend -> new special endpoint -> new protocol -> new UX
```

That would be unnecessary churn.

---

## 5. What the future architecture should look like

The future system should keep your HTTP/API layer almost unchanged and introduce a new internal workflow layer.

### 5.1 Recommended target architecture

```text
Frontend Chat UI
    -> POST /api/chat/stream
        -> chat_router
            -> ChatService.reply_stream(...)
                -> ConversationService / history loading
                -> MultiAgentChatWorkflow.stream(...)
                    -> Orchestrator
                    -> Specialist agents
                    -> Tool executor
                    -> shared planning state
                -> emits SSE events
    <- StreamingResponse(text/event-stream)
```

### 5.2 Key idea

Replace the current `AgentRunner` with a new **workflow facade** that still exposes a streaming interface.

That facade should be the only thing the chat service needs to know about.

Example shape:

```python
class ChatWorkflowRunner:
    async def stream_reply(
        self,
        conversation_id: str,
        user_message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        ...
```

As long as the chat service can iterate over events, the frontend remains unchanged.

---

## 6. Migration strategy: do not jump directly to “many autonomous agents”

The safest path is:

### Phase 1

Introduce a **workflow runtime** that looks like your current runner from the outside.

### Phase 2

Add a typed shared state for trip planning.

### Phase 3

Add a small number of specialist worker agents.

### Phase 4

Add optional richer event streaming such as:

- `planner_started`
- `agent_selected`
- `tool_called`
- `tool_result`
- `state_updated`
- `assistant_delta`
- `final_answer`

This keeps the frontend working from day one while allowing the backend intelligence to evolve.

---

## 7. Proposed future backend layers

### 7.1 API layer

Keep as-is:

- `chat_router`
- `conversation_router`
- user router

Minimal or no changes required.

### 7.2 Service layer

Your `ChatService` should remain the boundary used by the route.

It should continue to own:

- conversation lookup,
- history loading,
- persistence of new messages,
- passing requests to a runner/workflow,
- streaming output events back to the route.

### 7.3 Workflow layer

Introduce a new package, for example:

```text
app/workflows/
  chat/
    runner.py
    events.py
    state.py
    orchestrator.py
    policies.py
```

This workflow layer becomes the core replacement for `AgentRunner`.

### 7.4 Agent layer

Introduce specialist agents under:

```text
app/agents/
  base.py
  worker.py
  requirement_extractor.py
  destination_research.py
  weather_agent.py
  budget_agent.py
  itinerary_agent.py
  checker_agent.py
```

These should **not** be exposed directly to the HTTP layer.

### 7.5 Tool layer

Keep your registry approach, but add agent-specific filtered access later.

Suggested addition:

- global `ToolRegistry`
- per-agent `ToolSet`
- reusable `ToolExecutor`

---

## 8. Recommended future trip-planning workflow

For vacation planning, the future workflow should probably follow this sequence.

### Step 1: requirement extraction

Extract or normalize:

- origin
- dates
- budget
- number of travelers
- preferences
- hard constraints
- soft preferences

### Step 2: destination research

If destination is missing or vague:

- suggest candidate destinations
- justify ranking
- identify assumptions

### Step 3: weather and seasonality check

Use weather tools and later possibly historical climate tools.

### Step 4: transport and logistics

Plan transport options and travel friction.

### Step 5: lodging evaluation

Estimate lodging options or constraints.

### Step 6: budget validation

Check whether the overall plan fits user constraints.

### Step 7: itinerary generation

Produce a day-by-day or block-by-block plan.

### Step 8: final consistency check

Check for:

- budget overflow
- missing dates
- impossible logistics
- weak assumptions
- unsafe or misleading recommendations

### Step 9: stream final answer

Return the assistant answer in chat-friendly form while preserving structured internal state.

---

## 9. Shared typed state is the key enabling change

The future workflow should not pass only raw text between agents.

Instead, introduce a shared structured state such as:

```python
class TripPlanState(BaseModel):
    request: TripRequest
    destination_candidates: list[DestinationOption]
    chosen_destination: DestinationOption | None
    transport_options: list[TransportOption]
    stay_options: list[StayOption]
    itinerary: list[DayPlan]
    assumptions: list[str]
    risks: list[str]
```

This state should live in the workflow layer, not the HTTP layer.

### Why this matters

It gives you:

- deterministic orchestration,
- easy debugging,
- easier testing,
- better persistence,
- ability to resume or continue a conversation cleanly.

---

## 10. Streaming compatibility plan

Your frontend chatbot should continue to work if the new workflow emits the same basic event shape that the route already streams.

### Minimum compatibility mode

At first, the new workflow can emit only:

- text deltas
- final completion event
- error event

That means the frontend may need no change at all.

### Better future event protocol

Later, you can enrich events while keeping backward compatibility.

Suggested event types:

```json
{ "type": "message_start" }
{ "type": "assistant_delta", "delta": "Let me plan that..." }
{ "type": "workflow_step", "step": "extract_requirements" }
{ "type": "agent_step", "agent": "destination_research", "status": "started" }
{ "type": "tool_call", "tool": "get_weather_forecast", "input": {...} }
{ "type": "tool_result", "tool": "get_weather_forecast", "ok": true }
{ "type": "message_end" }
{ "type": "done" }
```

The frontend can ignore what it does not yet render.

---

## 11. Suggested replacement for current startup wiring

Today you have roughly:

```python
agent = AgentRunner(...)
app.state.agent = agent
```

The future should become something like:

```python
workflow = ChatWorkflowRunner(
    llm=llm,
    registry=registry,
    max_tool_iterations=settings.max_tool_iterations,
)
app.state.agent = workflow
```

Or, even better for naming clarity:

```python
app.state.chat_runner = workflow
```

Then `ChatService` depends on an interface, not the old class name.

### Recommended design

Define a protocol-like runtime contract:

```python
class ChatRunner(Protocol):
    async def stream_reply(
        self,
        conversation_id: str,
        message: str,
        history: list[dict[str, Any]],
    ) -> AsyncIterator[dict[str, Any]]:
        ...
```

This lets you swap:

- `AgentRunner`
- `SingleAgentRunner`
- `MultiAgentWorkflowRunner`

without changing the route contract.

---

## 12. Suggested compatibility architecture

### Current

```text
chat_router -> ChatService -> AgentRunner
```

### Transitional

```text
chat_router -> ChatService -> ChatRunner interface
                             -> SingleAgentRunner OR MultiAgentWorkflowRunner
```

### Final

```text
chat_router -> ChatService -> MultiAgentWorkflowRunner
                                -> Orchestrator
                                -> Worker agents
                                -> Tool executor
                                -> shared typed state
```

This is the cleanest migration path.

---

## 13. Future improvements by layer

### 13.1 FastAPI app layer

Recommended improvements:

- rename `app.state.agent` to something more generic like `app.state.chat_runner`
- create a typed app-state access helper
- optionally move bootstrap wiring into a dedicated composition module

### 13.2 Router layer

Recommended improvements:

- keep `/chat/stream` stable
- optionally add non-stream `/chat/reply` for testing or evals
- standardize SSE event shapes in one place

### 13.3 Service layer

Recommended improvements:

- make `ChatService` depend on a runner interface, not a concrete runner
- centralize message persistence and history loading here
- let it remain orchestration-light and transport-focused

### 13.4 Provider layer

Recommended improvements:

- keep provider low-level
- do not mix workflow logic into provider
- add metadata capture later: response ids, latency, token usage, tool count

### 13.5 Tool layer

Recommended improvements:

- introduce `ToolSet` for agent-specific tools
- add `ToolExecutor` abstraction
- normalize tool errors to one schema
- add tool observability

### 13.6 Agent layer

Recommended improvements:

- small workers with strict roles
- each worker returns structured outputs
- each worker gets only the tools it needs
- avoid agent-to-agent free-form chat as the first version

### 13.7 Workflow layer

Recommended improvements:

- deterministic orchestrator loop
- typed shared state
- explicit action selection
- final consistency checker
- workflow event emission for SSE

### 13.8 Persistence layer

Potential future improvement:

Persist not just chat messages, but also planning state snapshots if you want conversation continuity with less prompt bloat.

---

## 14. Risks to avoid during migration

### Risk 1: putting workflow logic in routers

Avoid it. Keep routers thin.

### Risk 2: making the frontend aware of internal agents

Avoid it. Frontend should consume chat events, not backend implementation details.

### Risk 3: letting every agent call every tool

Avoid it. Use limited tool access per worker.

### Risk 4: using only raw natural-language state

Avoid it. Use typed shared state.

### Risk 5: replacing everything at once

Avoid it. Introduce a compatible runner interface and swap the implementation behind it.

---

## 15. Concrete recommended next changes

These are the best next steps before full implementation.

### Change 1: introduce a runner interface

Create a shared contract for the chat runtime.

Example:

```python
class ChatRunner(Protocol):
    async def stream_reply(
        self,
        conversation_id: str,
        message: str,
        history: list[dict[str, Any]],
    ) -> AsyncIterator[dict[str, Any]]:
        ...
```

### Change 2: rename app state from `agent` to `chat_runner`

This avoids coupling the whole app to a specific implementation style.

### Change 3: keep `ChatService` as the stable boundary

Do not let routes talk directly to the workflow.

### Change 4: build a multi-agent workflow runner behind the same streaming interface

This is the main replacement target.

### Change 5: add structured workflow events

Even if the frontend initially ignores them.

---

## 16. Suggested future package layout

```text
app/
  api/
    chat_router.py
    conversation_router.py
    user_router.py

  services/
    chat_service.py
    conversation_service.py
    user_service.py

  providers/
    openai_responses.py

  tools/
    core/
      registry.py
      discovery.py
      executor.py
      selection.py
    weather.py
    web_search.py
    wiki_search.py
    calculator.py

  agents/
    base.py
    worker.py
    requirement_extractor.py
    destination_research.py
    weather_agent.py
    budget_agent.py
    itinerary_agent.py
    checker_agent.py

  workflows/
    chat/
      runner.py
      events.py
      state.py
      orchestrator.py
      contracts.py

  core/
    config.py
    logging.py

  db/
    session.py
```

---

## 17. Answer to your main architectural question

Yes — your future multi-agent workflow can be attached **seamlessly** to the current app **without breaking the frontend chatbot**, provided that you preserve this contract:

- `chat_router` still streams SSE,
- `ChatService` still returns an async event stream,
- the new workflow runner still yields frontend-safe chat events.

That is the central compatibility requirement.

You do **not** need to redesign the frontend first.

---

## 18. What I understand well enough already

Based on the code shared so far, I already understand enough to design the next backend step safely:

- FastAPI startup composition
- current tool loading and registration model
- streaming chat route
- conversation creation route
- provider abstraction
- the intended migration from single-agent to multi-agent

The most important missing implementation detail for code generation is the current shape of:

- `ChatService`
- `AgentRunner`
- any conversation/message persistence interfaces used by chat streaming

Those files are not needed for this review document, but they **will** be needed for the next step if the goal is to generate drop-in implementation code.

---

## 19. Recommended next implementation step

The next code step should be:

1. define a `ChatRunner` interface,
2. keep `ChatService` unchanged externally,
3. introduce a `MultiAgentWorkflowRunner` skeleton,
4. wire it in place of `AgentRunner` behind the same stream contract,
5. only then add the specialist worker agents.

That will preserve the current frontend chat UX while making the backend ready for multi-agent trip planning.

---

## 20. Summary

Your current system is already structured well enough for an incremental migration.

The safest design path is:

- keep the current FastAPI + SSE chat contract,
- replace the internal runner behind `ChatService`,
- add a workflow layer,
- use typed shared planning state,
- add specialist agents gradually,
- keep one global tool registry with filtered per-agent toolsets.

This gives you a multi-agent vacation planner that still behaves like the same chatbot from the frontend’s point of view.
