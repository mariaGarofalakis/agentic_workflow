# 🧠 Agentic Chatbot (Streaming + Tool Calling)

A minimal but **production-grade chatbot system** built with:

* ⚡ FastAPI (backend)
* ⚛️ React + Vite (frontend)
* 🤖 Agentic reasoning loop
* 🌊 Real-time streaming (SSE)
* 🧩 Modular architecture

---

# 📦 Project Structure

```
.
├── app
│   ├── agent/              # Agent orchestration logic
│   ├── api/                # FastAPI routes
│   ├── core/               # Config + logging
│   ├── providers/          # LLM provider abstraction
│   ├── services/           # Business logic layer
│   ├── tools/              # Tool registry + implementations
│   ├── schemas/            # Pydantic models
│   ├── dependencies.py     # Dependency injection
│   └── main.py             # FastAPI entrypoint
├── pyproject.toml
└── uv.lock
```

---

# 🚀 Overview

This project implements an **agentic chatbot system** where:

* the LLM can call tools
* responses are streamed in real-time
* the backend is cleanly layered
* the frontend renders streaming tokens live

---

# 🧩 Architecture Overview

```mermaid
flowchart TB
    User[User]
    Frontend[React Frontend]
    API[FastAPI API]
    Service[ChatService]
    Agent[AgentRunner]
    Provider[OpenAIResponsesClient]
    LLM[LLM Endpoint]
    Registry[ToolRegistry]
    Tools[Tool Implementations]

    User --> Frontend
    Frontend --> API
    API --> Service
    Service --> Agent
    Agent --> Provider
    Provider --> LLM

    Agent --> Registry
    Registry --> Tools
    Tools --> Registry
    Registry --> Agent
```

---

# 🔁 End-to-End Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as React
    participant API as FastAPI
    participant Service
    participant Agent
    participant Provider
    participant LLM
    participant Tools

    User->>UI: Send message
    UI->>API: POST /chat/stream
    API->>Service: reply_stream()
    Service->>Agent: run_stream()
    Agent->>Provider: stream_response()
    Provider->>LLM: request

    loop streaming
        LLM-->>Provider: token
        Provider-->>Agent: chunk
        Agent-->>Service: chunk
        Service-->>API: chunk
        API-->>UI: SSE chunk
    end

    LLM-->>Provider: final response

    alt tool calls
        Agent->>Tools: execute tool
        Tools-->>Agent: result
        Agent->>Provider: follow-up call
    end
```

---

# 🌊 Streaming Architecture

```mermaid
flowchart LR
    LLM --> Provider
    Provider --> Agent
    Agent --> Service
    Service --> API
    API --> Browser
    Browser --> UI
```

Streaming is implemented via:

* FastAPI `StreamingResponse`
* SSE (Server-Sent Events)
* Browser `ReadableStream`

---

# 🧠 Core Components

## 1. `main.py` — App Composition

Responsible for wiring everything:

```python
registry = build_registry()
llm = OpenAIResponsesClient(...)
agent = AgentRunner(...)
chat_service = ChatService(agent)
set_chat_service(chat_service)
```

This is your **dependency composition root**.

---

## 2. `AgentRunner` — The Brain

Handles:

* multi-step reasoning
* tool execution loop
* streaming tokens
* iteration control

```mermaid
flowchart TD
    Start --> CallLLM
    CallLLM --> CheckTools
    CheckTools -->|No| Return
    CheckTools -->|Yes| RunTool
    RunTool --> CallLLM
```

---

## 3. `OpenAIResponsesClient`

Handles:

* LLM API calls
* streaming tokens
* returning final responses

---

## 4. `ChatService`

Thin abstraction layer:

```python
reply()         # non-streaming
reply_stream()  # streaming
```

---

## 5. FastAPI Router

Provides endpoints:

```
POST /api/chat
POST /api/chat/stream
```

Streaming uses SSE:

```
data: {"type": "chunk", "content": "..."}
```

---

## 6. Tool System

```mermaid
flowchart LR
    LLM --> Agent
    Agent --> Registry
    Registry --> Tool
    Tool --> Registry
    Registry --> Agent
```

---

# 🔧 Startup Flow

```mermaid
sequenceDiagram
    participant Uvicorn
    participant App
    participant Lifespan

    Uvicorn->>App: import
    App->>Lifespan: startup
    Lifespan->>App: init services
```

---

# ⚛️ Frontend Flow

```mermaid
flowchart TD
    Input --> SendRequest
    SendRequest --> Stream
    Stream --> Parse
    Parse --> UpdateUI
```

---

# 🖥️ Frontend Streaming Logic

```mermaid
flowchart TD
    Submit --> AddUserMessage
    AddUserMessage --> AddEmptyAssistant
    AddEmptyAssistant --> StreamRequest
    StreamRequest --> ReceiveChunk
    ReceiveChunk --> AppendText
    AppendText --> ReceiveChunk
```

---

# 🔄 Streaming vs Non-Streaming

| Mode   | Behavior                |
| ------ | ----------------------- |
| Chat   | waits for full response |
| Stream | updates UI live         |

---

# 🛠️ Running the Project

## Backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Server:

```
http://127.0.0.1:8000
```

---

## Frontend

```bash
cd frontend
npm install
npm run dev
```

App:

```
http://localhost:5173
```

---

# 🔍 Debugging Tips

## Import errors

Make sure every folder has:

```
__init__.py
```

---

## Router errors

Correct import:

```python
from app.api.chat_router import router
```

---

## Streaming issues

Check:

* SSE headers
* frontend parsing
* buffering proxies

---

# 🚀 Future Improvements

* chat history (memory)
* WebSocket streaming
* persistent sessions
* retry + rate limits
* observability (logs + traces)

---

# 🧠 Design Philosophy

This project follows:

* separation of concerns
* dependency injection
* streaming-first UX
* agent + tools pattern

---

# 🏁 Summary

You now have:

* real-time streaming chatbot
* tool-calling agent
* clean backend architecture
* modular frontend

This is already close to **production-grade design**.

---

## Want next steps?

I can help you add:

* memory (chat history)
* WebSockets instead of SSE
* structured tool validation
* logging + tracing

Just ask 🚀
