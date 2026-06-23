# NerdBot — Project Context for Resume / LinkedIn Content Generation

> **Audience note (for the downstream LLM):** This document is a factual, calibrated brief
> about a real project. Everything below is grounded in the actual source code. Use it to
> generate recruiter-facing resume bullets, LinkedIn "Projects"/"About" copy, and skills
> tags. A **"Calibration & honesty guardrails"** section near the end tells you what NOT to
> overclaim — respect it so the generated content survives a technical interview.

---

## 1. One-paragraph summary

**NerdBot** (a.k.a. `vg-nerd-bot`) is a conversational AI agent that helps users discover,
research, and get recommendations about video games. The user chats in natural language
("what are the best chill co-op games on Switch?"), and a custom **tool-calling agent loop**
built on the **OpenAI API** decides when to query a live games database (the **RAWG Video
Games Database API**), with what filters, normalizes the results, and responds in a heavily
prompt-engineered "Level 99 video game enthusiast" persona. The app ships with a custom
**Gradio** chat UI (bespoke CSS/JS, animated welcome sequence, loading states) and is
**deployed to Hugging Face Spaces**. The core engineering achievement is a hand-built agent:
the multi-turn tool-calling loop, the function/tool schema design, a natural-language →
constrained-enum → API-ID translation layer, structured-output normalization, and the prompt
engineering that governs *when* and *how* tools are invoked.

---

## 2. What the system does (data flow)

```
User message (Gradio chat)
   │
   ▼
chat()  ── builds message list: [system prompt] + synthetic "hi" + history + user msg (+ persona reminder)
   │
   ▼
OpenAI Chat Completions  (model + tool schemas)  ◄─────────────┐
   │                                                           │
   ├─ finish_reason == "tool_calls"? ── yes ─► execute tool(s) ┘  (loop: append assistant msg + tool results, call again)
   │        │
   │        ▼
   │   tool fns (tools.py): get_current_date / find_game_by_name / find_multiple_games
   │        │
   │        ▼
   │   slug → RAWG numeric ID translation  (constants.py maps)
   │        │
   │        ▼
   │   Database (database.py): RAWG REST call w/ retry + backoff + connection pooling
   │        │
   │        ▼
   │   Pydantic models (classes.py): normalize verbose nested JSON → compact game objects
   │
   └─ finish_reason == "stop" ─► final natural-language answer back to Gradio UI
```

---

## 3. Tech stack (categorized, with *why it's relevant*)

### Language & runtime
| Tech | How it's used / why it matters |
|---|---|
| **Python 3.12** | Entire application. Uses modern typing syntax (`list[str] \| None`, union types). |

### LLM / AI (the core of the project)
| Tech | How it's used / why it matters |
|---|---|
| **OpenAI API** (`openai` Python SDK, v2.x) | Drives the agent. Uses the **Chat Completions** endpoint with **function/tool calling**. |
| **Function / Tool calling** | 3 tools defined as JSON-schema function specs; the model chooses tools and arguments. |
| **Custom agentic loop** | Hand-written multi-turn reasoning loop (call → tool exec → feed results → re-call until done). Demonstrates understanding of agent internals *without* a framework. |
| **Prompt engineering** | A ~90-line system prompt encoding persona, tool-use policy, few-shot examples, and disambiguation rules. |
| **Structured outputs** | Pydantic models constrain and normalize tool return payloads into compact, token-efficient JSON. |
| **Enum-constrained tool schemas** | Tool parameters are constrained to valid enums (platforms, genres, tags, stores, devs, publishers, sort orders) to prevent invalid model arguments. |

### Data validation & modeling
| Tech | How it's used / why it matters |
|---|---|
| **Pydantic** (`BaseModel`) | `GameDetailsResponse` and `GameDescriptionResponse` models with classmethod factories that parse messy nested RAWG JSON into clean, validated objects; `model_dump()` for JSON serialization back to the LLM. |

### External API integration / backend
| Tech | How it's used / why it matters |
|---|---|
| **RAWG Video Games Database API** | Third-party REST API for game metadata, search, and filtering (500k+ games). |
| **`requests`** + **`requests.Session`** | HTTP client with a **shared session for connection pooling** (TCP reuse across calls). |
| **Custom retry / resilience layer** | **Exponential backoff with jitter**, bounded retries, connect/read **timeouts**, structured success/error envelopes. |

### Frontend / UX
| Tech | How it's used / why it matters |
|---|---|
| **Gradio** (v5.x) | Chat UI via `gr.ChatInterface` + custom `gr.Chatbot(type="messages")`. Uses the **Blocks** event system, event chaining (`.then()`), and lifecycle events (`load`, `clear`). |
| **Custom CSS** | Animated typing/loading "bubble" (`@keyframes`), disabled-state styling. |
| **Custom JavaScript (vanilla)** | Injected JS that intercepts Enter-key/click submits during the welcome animation (**capture-phase event listeners**), manages a global loading flag, and syncs UI state. |
| **Custom HTML** | Loading indicator markup with ARIA roles (`role="status"`, `aria-label`) for accessibility. |

### Deployment, tooling & config
| Tech | How it's used / why it matters |
|---|---|
| **Hugging Face Spaces** | Production deployment target (Gradio SDK Space; configured via README YAML front-matter). |
| **`gradio deploy` CLI** | One-command deployment workflow — the developer ships updates to the Hugging Face Space by running `gradio deploy` (Gradio's built-in CLI that packages the app and pushes it to HF Spaces). |
| **`uv`** | Python package/dependency manager (`uv.lock` lockfile, `pyproject.toml`). |
| **`python-dotenv`** | Loads API keys/secrets from environment (`RAWG_API_KEY`, OpenAI credentials) — keeps secrets out of code. |
| **`ruff`** | Linter present in the dev environment. |
| **Git** | Version control. |
| *(transitively, via Gradio)* **FastAPI / Starlette / Uvicorn / WebSockets** | Gradio's server stack — relevant context, though not directly hand-coded. |

---

## 4. The LLM / Agent layer — DEEP DIVE (the headline of this project)

This is where the most resume-worthy engineering lives. The user effectively **built a custom
agent from primitives** rather than reaching for LangChain/LlamaIndex/an agent framework.

### 4.1 The custom agentic tool-calling loop
Implemented in `app.py::chat()`. The canonical agent control loop:

1. Assemble the message list (system prompt + conversation history + new user turn).
2. Call the model **with the tool schemas attached**.
3. Inspect `finish_reason`. If it equals `"tool_calls"`:
   - Iterate over **all** requested tool calls (supports **parallel/multiple tool calls in a
     single turn**),
   - Execute each, JSON-serialize the result,
   - Append the assistant tool-call message **and** the tool-result messages back into history,
   - **Loop again** so the model can reason over the fresh data (and possibly call more tools).
4. When the model stops requesting tools, return the final natural-language answer.

**Why it's impressive:** This demonstrates a ground-up understanding of how agents actually
work (the ReAct-style observe→act→observe cycle, message-history threading, tool-result
plumbing, `tool_call_id` correlation) — knowledge that's often hidden behind a framework.

### 4.2 Dynamic tool dispatch
Tools are resolved by name at runtime via `globals().get(tool_name)` and invoked with
`**arguments` unpacked from the model's JSON. This is a lightweight, registry-free dispatch
pattern that keeps tool wiring minimal.

### 4.3 Tool / function schema design (3 tools)
Defined in `tools.py::VIDEO_GAME_TOOLS` as OpenAI function-calling specs:

- **`get_current_date`** — gives the model a way to resolve **relative** time queries ("games
  from last year," "released in the past 6 months") into absolute date ranges. A clean example
  of giving an LLM a deterministic capability it otherwise lacks/hallucinates.
- **`find_game_by_name`** — single-game lookup by title (returns top matches).
- **`find_multiple_games`** — the complex one: a **14-parameter** filtered search with
  **enum-constrained** arrays for platforms, parent platforms, stores, developers, publishers,
  genres, tags; plus numeric Metacritic bounds, ISO date bounds, result count (1–25), and a
  sort `ordering`. Each parameter carries a precise natural-language description that doubles as
  inline guidance to the model.

**Single source of truth for enums:** The schema's `enum` lists are generated directly from
the canonical mapping dictionaries/lists in `constants.py` (e.g., `sorted(PLATFORM_SLUG_TO_ID.keys())`,
`GENRE_SLUGS`, `TAG_SLUGS`). The valid vocabulary the model can emit and the translation tables
used to build API calls **cannot drift apart** — a thoughtful design decision.

### 4.4 The natural-language → slug → API-ID translation layer
A three-stage mapping that is a genuinely smart agent-design pattern:

1. **User NL** ("PlayStation 5", "chill", "open world") →
2. **Constrained human-readable slug** the LLM emits (`"playstation5"`, `genres:["indie","casual"]`,
   `tags:["relaxing"]`) — constrained by the schema enums so the model stays on-vocabulary →
3. **RAWG numeric ID** produced by deterministic Python helpers (`_get_platform_ids`,
   `_get_store_ids`, etc.) that translate slugs to the integer IDs RAWG actually requires.

This keeps the LLM's job **semantic** (reason about *meaning*) and offloads the **brittle,
arbitrary ID bookkeeping** to deterministic code — reducing hallucination surface and making
the model's outputs validatable.

### 4.5 Structured outputs & token efficiency
RAWG returns large, deeply nested JSON. The Pydantic models in `classes.py` flatten and
**normalize** this into compact objects (name, id, playtime, platforms, stores, genres,
release date, Metacritic, ESRB) before the data is serialized back into the model's context.
This **cuts token cost** and **shrinks the surface for hallucination/distraction** — a real
LLM-engineering instinct.

### 4.6 Robust tool-result contract & graceful degradation
Every tool returns a structured `{"success": bool, "results"/"failure_reason": ...}` envelope.
The system prompt instructs the model that when tools return nothing useful, it should **fall
back to training knowledge while warning the user the info may be less current** — an explicit
graceful-degradation policy.

### 4.7 Prompt engineering (the system prompt is a whole artifact)
`prompts.py::SYSTEM_PROMPT` is a structured, multi-section prompt that encodes:

- **Persona definition** (voice, tone, response style).
- **Tool-usage *priority policy*** — explicit rules + **few-shot examples** for *when to call a
  tool vs. not* (greetings/chit-chat → no tool; specific game/recommendation requests → tool;
  reuse already-fetched data instead of re-calling). This directly addresses cost control and
  latency, and prevents needless API spam.
- **Parameter-maximization guidance with good/bad few-shot pairs** — teaches the model to turn
  vague requests into high-quality filtered queries ("best" → sort by `-metacritic`; "chill" →
  infer genres/tags), improving result relevance.
- **A disambiguation rule** for a real edge case: *platform* vs *parent_platform* (e.g., "PS5"
  must map to the specific console, not the entire PlayStation family) — a subtle correctness
  trap the developer identified and prompted around.

### 4.8 Persona / instruction-drift mitigation
A **persona reminder string is appended to every user turn** (not just the system prompt).
This is a deliberate countermeasure to **instruction/persona decay over long conversations** —
a known LLM failure mode where early system instructions lose influence as context grows.

### 4.9 Conversation well-formedness handling
To keep the message history valid for the model, the code prepends a synthetic `"hi"` user turn
so the page-load welcome (an assistant message) always has a user antecedent — small but shows
care about the strict user/assistant alternation LLM APIs expect.

---

## 5. Backend / external-integration engineering

- **Resilient HTTP layer** (`database.py::_make_request_with_retry`): bounded retries (default 3),
  **exponential backoff** (`base_delay * 2**attempt`) with **random jitter** to avoid the
  thundering-herd problem, explicit **connect/read timeouts** `(3s, 10s)`, and `raise_for_status`
  error handling — all wrapped in a uniform success/error return contract.
- **Connection pooling** via a single shared `requests.Session` (reuses TCP connections across calls).
- **Singleton database client** (`DATABASE`) for shared config/auth/query helpers.
- **Clean separation of concerns:** `database.py` (raw API/transport), `tools.py` (agent-facing
  tool functions + ID translation + schema), `classes.py` (data models), `constants.py`
  (reference data), `prompts.py` (prompt artifacts), `app.py` (agent loop + UI).

---

## 6. Frontend / UX engineering (Gradio + custom web)

The UI is more than a default Gradio chatbot — there's real custom front-end work:

- **Custom Gradio Blocks composition:** a hand-built `gr.Chatbot` wired into `gr.ChatInterface`,
  with custom CSS/JS injection (`css_paths`, `js=`).
- **Animated welcome sequence:** on page load (and on chat-clear), a loading "typing" bubble
  shows, then the welcome message is revealed with a delay, then synced into `ChatInterface`'s
  history state so the agent still receives it as context.
- **Event orchestration:** uses Gradio lifecycle events (`demo.load`, `chatbot.clear`) and event
  chaining (`.then(...)`) to sequence multi-step UI transitions and toggle the send button.
- **Vanilla-JS input guard:** injected JavaScript installs **capture-phase** `keydown`/`keypress`/
  `click` listeners that block message submission while the welcome animation is in flight,
  coordinating UI state through a global flag and CSS body class.
- **Accessibility:** the loading indicator uses ARIA `role="status"` / `aria-label`.

> This welcome/loading/state-sync orchestration was clearly one of the fiddly parts of the
> project (multiple JS files + CSS + Python event wiring just to make page-load feel polished).

---

## 7. Key challenges & complexities overcome (use these for "impact" bullets)

1. **Built a tool-calling agent from scratch** — the multi-turn loop, message threading, parallel
   tool-call handling, and tool-result plumbing — instead of leaning on an agent framework.
2. **Designed a 3-stage NL → enum-slug → API-ID translation** that keeps the LLM reasoning
   semantically while deterministic code handles brittle ID mapping (reduces hallucination,
   keeps outputs validatable).
3. **Prompt-engineered tool-use economics** — explicit policy + few-shot examples controlling
   *when* tools fire (avoiding needless API calls on greetings/known data) and *how richly*
   queries are parameterized (turning vague asks into high-quality filtered searches).
4. **Mitigated persona/instruction drift** across long conversations via per-turn reminder
   injection.
5. **Token-efficient structured outputs** — normalized verbose nested third-party JSON into
   compact Pydantic models before returning to the model's context.
6. **Resilient external API integration** — retries with exponential backoff + jitter, timeouts,
   connection pooling, and a uniform success/error contract enabling graceful degradation.
7. **Single-source-of-truth schema generation** — tool-schema enums generated from the same
   constant maps used for ID translation, eliminating drift between what the model can say and
   what the API accepts.
8. **Polished, custom chat UX** — animated welcome/loading states with cross-layer (Python +
   JS + CSS) state synchronization and input gating.
9. **Shipped it** — packaged with `uv`, secrets via env, and **deployed to Hugging Face Spaces** via
   the **`gradio deploy`** CLI (single-command publish workflow).

---

## 8. LinkedIn / resume keyword bank (group + sprinkle naturally)

> Use these as skills tags and weave the *bolded* ones into bullet copy. Don't keyword-stuff;
> pick the strongest per bullet.

**AI / LLM (lead with these):**
`LLM application development` · `OpenAI API` · `AI agents` · `Agentic workflows` ·
`Tool calling / Function calling` · `Prompt engineering` · `System prompt design` ·
`Few-shot prompting` · `Structured outputs` · `Retrieval / live data augmentation` ·
`Conversational AI` · `Chatbot development` · `Context management` · `Token optimization` ·
`Graceful degradation / fallback strategies`

**Languages & core:**
`Python` · `Python 3.12` · `Type hints` · `Asynchronous-friendly request handling`

**Frameworks & libraries:**
`Gradio` · `Pydantic` · `OpenAI Python SDK` · `Requests` · `python-dotenv`

**APIs & data:**
`REST API integration` · `Third-party API integration (RAWG)` · `JSON parsing & normalization` ·
`Data modeling / validation` · `API resilience (retries, backoff, jitter, timeouts)` ·
`Connection pooling`

**Frontend / UX:**
`Custom UI` · `JavaScript` · `CSS animations` · `Event-driven UI` · `Accessibility (ARIA)`

**DevOps / tooling / deployment:**
`Hugging Face Spaces` · `gradio deploy (CLI deployment)` · `Model deployment` ·
`uv (Python packaging)` · `Git` · `Ruff` · `Secrets / environment configuration`

**Transitive / "familiar with" (only if asked — Gradio's server stack):**
`FastAPI` · `Starlette` · `Uvicorn` · `WebSockets`

**Concept keywords (good for "About" prose):**
`Separation of concerns` · `Single source of truth` · `Schema-driven design` ·
`Software architecture` · `Human-in-the-loop conversational systems`

---

## 9. Ready-to-adapt resume bullet seeds (rewrite to fit voice/length)

- *Designed and built a custom LLM agent (OpenAI function calling) with a multi-turn
  tool-calling loop that autonomously decides when to query a live games API and synthesizes
  results into conversational answers.*
- *Engineered a natural-language → constrained-enum → API-ID translation layer and Pydantic-based
  output normalization, reducing hallucination and token cost while keeping model outputs
  validatable.*
- *Authored a structured system prompt (tool-use policy, few-shot examples, disambiguation rules)
  that controls when tools fire and how richly queries are parameterized — cutting unnecessary
  API calls and improving recommendation relevance.*
- *Implemented a resilient third-party API integration layer with exponential backoff + jitter,
  timeouts, and connection pooling behind a uniform success/error contract.*
- *Built and deployed a polished custom Gradio chat interface (animated welcome/loading states,
  capture-phase JS input gating, ARIA accessibility) to Hugging Face Spaces via the `gradio deploy` CLI.*

---

## 10. Calibration & honesty guardrails (READ BEFORE WRITING COPY)

To keep generated claims defensible in a technical interview, observe these limits:

- **Scope:** This is a **solo, personal portfolio project** (~3 commits, no automated test suite,
  no CI/CD pipeline, no auth/multi-user infra). **Do not** describe it as a team effort, a
  large-scale production system, or claim metrics (users, latency, uptime, cost savings) — there
  are no measured numbers. Avoid invented quantitative impact ("reduced costs by X%").
- **The agent is real, the framework is not.** It's a genuinely hand-built tool-calling loop —
  that's the honest strength. Don't claim use of LangChain/LlamaIndex/CrewAI/etc. (none are used).
- **Model:** the configured model is a small/"nano"-tier OpenAI chat model. It's fine to say
  "OpenAI API / GPT" generically; don't overstate model sophistication or imply fine-tuning,
  RAG over a vector DB, or embeddings — **none of those are present** (data comes from a live
  REST API, not a vector store; calling it "RAG" is a stretch — prefer "live data augmentation"
  or "tool-augmented retrieval from a REST API").
- **No streaming / no async:** responses are returned whole; calls are synchronous. Don't claim
  streaming token output or async concurrency.
- **Statelessness:** conversation history is supplied by the Gradio client each turn; there's no
  server-side persistence/database of conversations. "Database" in the code refers to the RAWG
  API wrapper, not a datastore the developer manages.
- **FastAPI/Uvicorn/WebSockets** come *transitively* via Gradio — list them as "familiar with /
  underlying stack," not as things hand-implemented.
- **Best, fully-honest framing:** lead with *LLM/agent engineering, prompt engineering, API
  integration, and shipping a deployed full-stack AI app solo.* Those are all 100% supported by
  the code.

---

## 11. Quick file map (for reference)

| File | Role |
|---|---|
| `app.py` | Agent loop (`chat`), tool dispatch (`handle_tool_calls`), Gradio UI build & welcome sequence. |
| `tools.py` | Agent-facing tool functions, slug→ID translation, OpenAI tool/function schemas. |
| `prompts.py` | The engineered system prompt (persona + tool-use policy + few-shot examples). |
| `classes.py` | Pydantic models normalizing RAWG JSON into compact game objects. |
| `database.py` | RAWG REST client: requests Session, retry/backoff/jitter, timeouts. |
| `constants.py` | Canonical slug↔ID maps and enum vocabularies (platforms, genres, tags, etc.). |
| `assets/*.js`, `assets/*.css` | Custom front-end: loading bubble, welcome animation, input gating. |
| `README.md` | Hugging Face Spaces config (YAML front-matter). |
| `pyproject.toml` / `uv.lock` | Dependencies, managed with `uv`. |
