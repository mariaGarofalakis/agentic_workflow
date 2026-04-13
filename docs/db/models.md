# Database Model & Transaction Design

## Overview

This application uses PostgreSQL with SQLAlchemy to manage:

* Users
* Conversations (chat sessions)
* Messages (chat history)

The system is designed to support **stateful AI conversations** using OpenAI’s `previous_response_id`, while ensuring **correctness under concurrency**.

---

## Data Model

### 1. User

Represents an application user.

| Column       | Type        | Description             |
| ------------ | ----------- | ----------------------- |
| `id`         | string (PK) | Unique user identifier  |
| `email`      | string      | Optional, unique email  |
| `created_at` | datetime    | User creation timestamp |

**Relationships**

* One user → many conversations

---

### 2. Conversation

Represents a chat thread and holds the **AI memory pointer**.

| Column             | Type          | Description                   |
| ------------------ | ------------- | ----------------------------- |
| `id`               | string (PK)   | Unique conversation ID        |
| `user_id`          | FK → users.id | Owner of the conversation     |
| `title`            | string        | Optional name                 |
| `last_response_id` | string        | OpenAI response chain pointer |
| `is_processing`    | boolean       | Concurrency guard             |
| `created_at`       | datetime      | Creation time                 |
| `updated_at`       | datetime      | Last update                   |

**Purpose**

* Stores **conversation state**
* Enables continuation via:

  ```
  previous_response_id = conversation.last_response_id
  ```

---

### 3. Message

Represents each message in a conversation.

| Column               | Type                  | Description               |
| -------------------- | --------------------- | ------------------------- |
| `id`                 | string (PK)           | Message ID                |
| `conversation_id`    | FK → conversations.id | Parent conversation       |
| `role`               | string                | "user", "assistant", etc. |
| `content`            | text                  | Message content           |
| `openai_response_id` | string                | Source OpenAI response    |
| `created_at`         | datetime              | Timestamp                 |

**Purpose**

* Stores chat history
* Enables debugging and auditing

---

## Core Concept: Conversation Memory

The system does **not replay full chat history** to the model.

Instead, it uses:

```
conversation.last_response_id
```

This is passed to OpenAI:

```
previous_response_id = last_response_id
```

This allows OpenAI to maintain context internally.

---

## Transaction Design

### Goals

* Prevent concurrent writes to the same conversation
* Avoid long database locks
* Ensure consistency of `last_response_id`
* Keep transactions short and predictable

---

## Transaction Pattern (Per Request)

Each chat request follows **three phases**:

---

### 1. Claim Phase (short transaction)

```python
async with session.begin():
    conversation = SELECT ... FOR UPDATE

    if conversation.is_processing:
        raise error

    conversation.is_processing = True

    insert user message
```

**What happens**

* Row is locked
* Conversation is marked as busy
* User message is saved
* Transaction commits quickly

---

### 2. Execution Phase (no transaction)

```python
run agent (LLM + tools)
stream response
```

**What happens**

* No DB locks held
* Model + tools execute
* Response is streamed to client

---

### 3. Finalize Phase (short transaction)

```python
async with session.begin():
    SELECT ... FOR UPDATE

    insert assistant message

    conversation.last_response_id = new_id
    conversation.is_processing = False
```

**What happens**

* Conversation is updated safely
* Memory pointer is advanced
* Lock is released

---

### 4. Failure Handling

If an error occurs:

```python
async with session.begin():
    conversation.is_processing = False
```

Prevents the conversation from being permanently locked.

---

## Concurrency Strategy

### Problem

Without protection:

* Two requests read same `last_response_id`
* Both generate responses
* State becomes inconsistent

---

### Solution

We enforce:

```
one active request per conversation
```

Using:

* `is_processing` flag
* `SELECT ... FOR UPDATE` row locking

---

## Why This Approach

### Advantages

* Short DB transactions
* No long locks during model execution
* Safe concurrency per conversation
* Scales across multiple backend instances
* Simple mental model

---

### Tradeoffs

* A conversation cannot process two messages at once
* Requires cleanup if a process crashes mid-request

---

## Future Improvements

For more robust systems, consider:

* Lease-based locking:

  * `processing_owner`
  * `processing_started_at`
* Agent run tracking table
* Tool execution logging
* Message metadata (tokens, model, etc.)
* Redis caching layer

---

## Summary

| Layer                         | Responsibility            |
| ----------------------------- | ------------------------- |
| PostgreSQL                    | Source of truth           |
| Conversation.last_response_id | AI memory pointer         |
| is_processing                 | Concurrency guard         |
| SQLAlchemy Session            | Unit of work              |
| ChatService                   | Transaction orchestration |

---

## Key Principle

> The database owns conversation state.
> The agent consumes and advances it safely.

---
