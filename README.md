# SRU Assist — Agentic Student Handbook Chatbot

**SRU Assist** is an *agentic RAG (Retrieval-Augmented Generation) chatbot* built for the
SR University student portal (SRAAP). Students ask questions in natural language about
credits, grading, CGPA, pass marks, attendance, examinations, promotion rules, hostels,
fees, scholarships, dress code and other university policies — and the bot answers
**exclusively and faithfully from the official Student Handbook PDFs**, always with
**document + page citations**, falling back to a controlled web search only when the
handbook has no answer.

This repository is a **fully self-contained project**: it ships the retrieval engine, the
LLM agent loop, the Flask API, an embeddable vanilla-JS chat widget, a mock portal for
demos, an evaluation harness, and one-click deploy configuration. Zip the folder, set one
API key, and it runs anywhere.

```
 Student question (portal widget / API)
        │
        ▼
 ┌─────────────────────────────────────────────┐
 │  Flask  POST /api/chat  →  agent/core.py    │  (app.py)
 └─────────────────────────────────────────────┘
        │
        ├─ 1► AUTO-RETRIEVE  top-K handbook chunks  (pure-Python BM25, no vector DB)
        │      • two-stage retrieval: BM25 recall → exact query-phrase promotion
        │      • intent-based multi-document routing (Handbook 2026-27 vs R23)
        │      • compound/contact normalization: "Wi-Fi"↔"wifi", "sru.edu.i\n"→".in"
        │      • query-side synonym expansion ("internet not working" → wifi rows)
        │
        ├─ 2► FAST MODE (default, 1 LLM call): answer grounded directly on context
        │      AGENT MODE (AGENT_MODE=agent): LLM tool loop up to AGENT_MAX_STEPS:
        │      • search_handbook(query)  more retrieval on demand
        │      • calculator(expr)       safe CGPA / percentage arithmetic
        │      • search_web(query)      Tavily fallback ONLY if handbook lacks it
        │
        └─ 3► Grounded answer in chat-safe markdown  +  document & page citations
              e.g.  "(Handbook 2026-27 p. 34)"  or  "(R23 Handbook p. 57)"
```

---

## Table of contents

1. [What has been built (feature timeline)](#what-has-been-built)
2. [Quick start](#quick-start)
3. [Architecture & request flow](#architecture--request-flow)
4. [Model & rate limits (OpenRouter)](#model--rate-limits-openrouter)
5. [Retrieval engine (how answers are found)](#retrieval-engine)
6. [Agentic loop & tools](#agentic-loop--tools)
7. [Multi-document support (2026-27 + R23)](#multi-document-support)
8. [Personalization, clarifying questions & suggestions](#personalization--conversation-features)
9. [API contract](#api-contract)
10. [Embeddable widget](#embeddable-widget)
11. [Evaluation & quality](#evaluation--quality)
12. [Reducing latency](#reducing-latency)
13. [Deployment (live)](#deployment--live-url)
14. [Real portal integration notes (sraap.in)](#real-portal-integration)
15. [Configuration (.env)](#configuration)
16. [Project layout](#project-layout)
17. [Design decisions (why it was built this way)](#design-decisions)
18. [Known limitations & roadmap](#known-limitations--roadmap)
19. [Team workflow & rules](#team-workflow--rules)

---

## What has been built

Built by the SRU student project team (2026). Each bullet maps to a commit in `git log`:

| # | Milestone | What it delivered |
|---|---|---|
| 1 | **SRU Assist v1** | Working agentic handbook chatbot: Flask API (`POST /api/chat`, `GET /api/health`), page-based chunking + pure-Python BM25 retrieval over the 86-page Student Handbook, LLM tool-calling loop via OpenRouter, embeddable vanilla-JS widget + mock demo portal. |
| 2 | **Chat-friendly formatting** | LaTeX/math markup banned in prompts; the widget ships a **mini-markdown renderer** (paragraphs, dash bullets, numbered lists, tables, bold, inline code, subscripts) with LaTeX cleanup (`\frac`, `\times`, `\[...\]`…) as a second safety net. Fixes the "raw `\frac` in the chat bubble" failure class seen in testing. |
| 3 | **Personalization & clarify-then-answer** | Student profile (⚙️ in widget: programme/branch/year/semester) injected into the system prompt, persisted in `localStorage`. When a rule depends on programme/year and it is unknown, the agent asks **exactly ONE** clarifying question instead of guessing. Topic-bandit suggestion chips (`agent/stats.py` → `data/query_stats.json`) surface recent asks as short labels. |
| 4 | **Branding & portal prep** | Widget + demo rebranded to the SRAAP/SRU palette (primary **#23468A**, accents #97B9E2 / #dbe7f7), matching the live portal's stylesheet. Real-portal integration notes written up (see below). |
| 5 | **Production readiness** | `gunicorn` startup, `$PORT`/`FLASK_PORT` support, `render.yaml` Blueprint for one-click Render deploy. Deployed live at **https://sru-assist.onrender.com**. |
| 6 | **Documented live deployment** | Deploy URL recorded; README deploy guide verified. |
| 7 | **Eval harness + contract** | `tests/golden_set.json`, `docs/API.md` (API contract), `ARCHITECTURE.md` (decision record), `PRODUCTIONIZATION.md` (path to university infra). CI-friendly exit code (fails under 80% hit-rate). |
| 8 | **Multi-document + intent routing** | Second regulation added — **R23 B.Tech Handbook** (238 pages) — with per-document indexes, intent-based routing (name a regulation → search only that doc; comparison → split; else default to current handbook), `(R23 Handbook p. N)` citations. Eval expanded to **27 golden cases @ 93% → 100% hit-rate**. |
| 9 | **100% retrieval hit-rate** | Two-stage retrieval: BM25 recall + **exact query-phrase promotion** and **compound-word normalization** — e.g. "non-credit" matches the PDF's "noncredit", across *any* hyphenated pair, not just known ones. Final baseline: **100% hit-rate @ top-6, MRR 0.76** across all 27 cases. |
| 10 | **Contact/wifi fixes + clean data** | Three coordinated fixes for the "is it even in the handbook?" failure class: **generic hyphen/compound tokenization** (any `word-word` emits both split + joined forms, so "Wi-Fi"↔"wifi"), **contact-directory chunking** (email+mobile paragraphs split into ≤400-char row groups so "Who do I contact for Wi-Fi?" hits the Wi-Fi row instead of a 1500-char contact dump), **query-side synonym expansion** ("not working"/"internet" widen to the handbook's exact wording), plus a **PDF text repair** that rejoins emails the PDF split across lines (`g.rajeshwarreddy@sru.edu.i\n` → `@sru.edu.in`). Golden set now **29 cases; baseline 100% hit-rate @ top-6, MRR 0.79**. |

**Current baseline:** `100% hit-rate @ top-6 · MRR 0.79` on **29 golden questions**
spanning BOTH regulations (measured: 29/29, retrieval-only eval, one BM25 pass takes
~10 ms; full index = 690 chunks). Remaining headroom is semantic paraphrase — the
motivation for hybrid embedding retrieval (roadmap).

---

## Quick start

```bash
cd sru-chatbot
pip install -r requirements.txt

# one-time: copy .env.example -> .env and add your OPENROUTER_API_KEY
python app.py
```

Open **http://localhost:5000** → the mock student portal loads → click the **💬** bubble
(bottom-right). The API runs on the same port.

`requirements.txt` is intentionally tiny (5 packages): `flask`, `openai`, `requests`,
`pypdf`, `gunicorn`. No numpy / torch / langchain / vector DB — by design.

---

## Architecture & request flow

```
 Flask  POST /api/chat ──►  agent/core.run_agent()
   │
   ├─0► clarify pre-pass (agent/clarify.py, ZERO LLM cost): ambiguous Boys/Girls
   │     hostel or programme/branch questions get a one-tap question first
   │
   ├─1► auto-retrieve: BM25 over handbook chunks (always; grounds the model)
   │     retriever.search() → _phrase_rerank → format_hits(top_k=4 in fast mode)
   │
   ├─2► LLM (OpenRouter, OpenAI-compatible client in agent/llm.py):
   │     fast  (default): exactly ONE call, tool-free prompt, grounded by context
   │     agent (opt-in):  tool loop up to AGENT_MAX_STEPS=4 rounds
   │              search_handbook(query)   more retrieval on demand
   │              calculator(expr)         safe CGPA / percentage arithmetic
   │              search_web(query)        Tavily fallback ONLY if handbook lacks it
   │
   └─3► answer + page citations (+ mode / tool_calls / latency_ms metadata)
```

**Module map** — each request flows through exactly these pieces:

| Layer | File | Responsibility |
|---|---|---|
| HTTP | `app.py` | Routes (`/api/chat`, `/api/health`, `/api/suggestions`, `/api/sync`), CORS, static + demo, request validation (message 1–1000 chars), `latency_ms` measurement |
| Agent | `agent/core.py` | `run_agent()` → clarify pre-pass, then fast or agentic path; auto-RAG context injection; trash-history trimming; tool-call-echo defence; citation harvesting; the grounded-answer safety net |
| Clarify | `agent/clarify.py` | Deterministic, zero-LLM ambiguity check (Boys/Girls hostel, programme/branch) → `mode:"clarify"` + `options` chips |
| Retrieval | `agent/retriever.py` | PDF/URL/manifest ingestion, page-marked text files, chunking (incl. contact tables), tokenizer+stemmer, BM25 indexes, doc routing, query expansion, phrase rerank |
| Tools | `agent/tools.py` | Tool JSON schemas + safe implementations (search / calculator / search_web) |
| Prompts | `agent/prompts.py` | `SYSTEM_PROMPT` (agent), `FAST_SYSTEM_PROMPT` (tool-free), `FALLBACK_PROMPT` (safety net); all forbid claiming absence from missing context |
| LLM | `agent/llm.py` | Thin OpenAI-compatible wrapper around OpenRouter (one client, timeout from `LLM_TIMEOUT`) |
| Config | `agent/config.py` | Tiny `.env` loader (no `python-dotenv` dependency) |
| Suggestion ranker | `agent/stats.py` | Recency-decayed topic bandit → `data/query_stats.json` → widget chips |

**Key guarantee — never crashes the widget:** if the provider rejects tool-calling or any
LLM call errors mid-loop, `core.py` degrades to a *grounded no-tool answer*
(`_grounded_answer`, mode `rag-fallback` / `rag-fallback-midloop`) instead of failing.
The HTTP layer returns HTTP 200 with `mode:"error"` and a safe message on any unexpected
exception. Full mode ladder in [Agentic loop & tools](#agentic-loop--tools).

---

## Model & rate limits (OpenRouter)

The only external dependency is one LLM call. Everything below is configured via
environment variables (`.env`), never hard-coded.

### Default model

| Property | Value |
|---|---|
| Model ID | `nvidia/nemotron-3-ultra-550b-a55b:free` (`.env` key `MODEL_NAME`) |
| Why | Free ($0/token), strong reasoning, **tool-calling supported** (unusual for free tiers), top free model on OpenRouter by traffic |
| Architecture | NVIDIA **Nemotron 3 Ultra** — open MoE, hybrid Transformer-Mamba, **55B active / 550B total** |
| Context window | up to **1M tokens** |
| Max completion | up to **65,536 tokens** (we cap it at `MAX_TOKENS=700` ourselves) |
| Release | Jun 4, 2026 |
| Endpoint | `https://openrouter.ai/api/v1` (OpenAI-compatible) |

### Free-tier rate limits (the RPM / RPD the README warns about)

OpenRouter's `docs/api/reference/limits` governs *all* `:free`-suffixed models with a
two-tier daily quota. Limits are **per account and shared across every key and every
`:free` model** — new keys or new accounts *(incorrectly)* do **not** raise them.

| Lifetime credits bought | Requests per minute (RPM) | Requests per day (RPD) |
|---|---|---|
| < **$10** | **20** | **50** |
| **≥ $10** (bought once, never expires) | **20** | **1,000** |

- **RPM is fixed at 20** for free variants — buying credits does **not** raise it.
  That is ~1 request every 3 s; bursts past it return **HTTP 429**.
- **RPD is the lever** — a one-time **$10 credit purchase bumps 50 → 1,000 requests/day
  permanently**, even later when your balance drops to zero. The classic free-tier unlock.
- **Practical budget:** at 50 RPD, a single class of ~100 students asking
  `AGENT_MODE=fast` (1 LLM call each) consumes the whole day twice. For any real portal
  launch, plan on the $10 top-up (→ 1,000/day) or a paid model + per-student rate limits.
- **429 handling:** treat it as "slow down" — add exponential backoff/retry (the widget
  shows a graceful "can't reach the server" message). Query your exact quota live with
  `GET https://openrouter.ai/api/v1/key` (returns `limit_remaining`, `limit_reset`).
- **Provider-layer limits also exist** (token-per-minute, peak-hour throttling), and
  free endpoints are served at **lower priority** than paid traffic.

### Current latency/uptime profile (OpenRouter model page, snapshot Sept 2026)

These numbers move constantly; treat them as order-of-magnitude.

| Metric | Value (snapshot) |
|---|---|
| Throughput (generation) | **~3 tokens/s** |
| Median latency (P50) | **~75 s** round-trip |
| Uptime (3-day) | **~98%** |
| 24h availability | ~77–78% (volatile; OpenRouter has raised 429/error rates recently) |

**Implication:** the default model is a huge, slow MoE. A 100-word answer alone costs
15–40 s of generation. This is the *single biggest latency factor* — see
[Reducing latency](#reducing-latency). The intended production step is swapping
`MODEL_NAME` for a fast model with credits (see `PRODUCTIONIZATION.md` for a provider
table).

### Data & privacy note

`:free` endpoints have no SLA and some providers **log prompts** for improvement
(NVIDIA's free endpoint states sessions are logged and may be used to improve their
products; logs are not linked to your identity). OpenRouter itself adds connection logs.
Rule of thumb for this project: **nothing personal or confidential goes to a free
endpoint** — student PII stays out of prompts (we already only send programme/branch/
year/semester in the profile block).

---

## Retrieval engine

Files: `agent/retriever.py` (all logic), built on text extracted by `pypdf` (lazy,
on first load, per document). One BM25 search pass over the full 690-chunk index takes
**~10 ms** — no model downloads, no GPU, deterministic.

**Pipeline (per document in `data/`):**

1. **Extract** — `extract_pdf()` opens the PDF with `pypdf`, runs `_repair_email_breaks()`
   over each page's raw text (rejoins addresses the PDF text layer split across lines,
   e.g. `g.rajeshwarreddy@sru.edu.i\n` → `@sru.edu.in`, only when the combined tail is a
   known TLD such as `.in`/`.com`), then writes `data/<slug>.txt` with
   `===== PAGE <n> =====` markers. Plain text / JSON re-export can skip the PDF entirely —
   see [Portal integration](#real-portal-integration).
2. **Chunk** — `split_page()` joins paragraphs (split on blank lines) into chunks of
   ≤ `MAX_CHUNK_CHARS = 1400` chars; paragraphs longer than `1.5 ×` are hard-split at the
   last space ≥ 400 chars in. **Contact-directory paragraphs** (an email address *and* a
   10-digit mobile number in the same paragraph) are instead broken into small row groups
   of ≤ `CONTACT_TARGET_CHARS = 400`, so one "service → person → phone → email" entry is
   never drowned by a ~1500-char dump of every contact on the page. Total: **690 chunks**
   (Handbook 2026-27 = 344, R23 = 346).
3. **Tokenize + stem** — `tokenize()` lowers the text, extracts `[a-z0-9]+(-[a-z0-9]+)*`
   units, and emits **both halves *and* the hyphenless whole** of every two-part compound
   (`Wi-Fi`→`wifi,wi,fi`, `re-evaluation`→`re,evaluation,reevaluation`,
   `non-credit`→`non,credit,noncredit`). This generalizes to *any* hyphen/compound pair,
   not a hardcoded list. A cheap suffix stripper collapses `pass↔passing`, `mark↔marks`,
   `es`/`s` plurals. ~40 common stopwords are dropped.
4. **Index** — a pure-Python **BM25** scorer per document (sub-indexes) plus one
   compound index. Parameters: **k1 = 1.4, b = 0.72**, standard IDF
   `log(1 + (N − n + 0.5)/(n + 0.5))`. Each sub-index gives the smaller regulation a fair
   share of results instead of being drowned by the bigger one.

**A single `retriever.search(query, top_k=6)` call does:**

- **Doc routing** (`_doc_hints`) — the query is scanned for a regulation id
  (`r23`, `R23`, `2023`, `2024`, `B.Tech 2023`…): one named regulation → search that
  document's sub-index only; several (a comparison) → round-robin slots evenly across
  them; none → default to the current handbook (the proven single-doc baseline). A query
  saying `old/previous/earlier/last year` routes to the older regulation.
- **Query expansion** (`expand_query`) — before tokenization, noted synonyms are appended
  *to the query string only* (the index is untouched, so baselines can't drift). Examples:
  `wifi → wifi wi-fi wireless network`, `internet → internet wifi broadband network`,
  `not working → not working issue problem down disconnected`,
  `contact → contact reach report help desk helpline number`. BM25 + phrase rerank still
  favor exact matches; expansion only widens recall.
- **Two-stage reranking** (`_phrase_rerank`) — BM25 supplies recall; a second pass scans
  the candidate pool (up to `max(top_k*6, 30)` per doc) for the query's *adjacent term
  pairs* as an exact phrase and promotes those chunks to the front (BM25 order preserved
  inside each group). Phrase matching uses a **squashed comparison string** so
  `non-credit` matches `noncredit` and `Wi-Fi` matches `wifi`. "Promote, don't replace"
  keeps recall safe — non-matches backfill instead of being discarded.
- **Merge** — labels are walked round-robin in doc order until `top_k` chunks are filled
  (deduped), then packaged with `format_hits()` into blocks headed
  `[<label> · page <n>]` plus a matching citation list.

**Why BM25 and not a vector DB?** BM25 over ~690 chunks is instantaneous (~10 ms),
deterministic, needs no model downloads or GPU, and has zero heavy dependencies. The
retriever exposes one stable interface — `get_retriever().search(query, top_k)` and
`format_hits(query, top_k)` — so a future embedding/FAISS/Chroma upgrade touches one
file. `rebuild()` drops the cached index and is called by `/api/sync` when the portal
pushes refreshed content.

---

## Agentic loop & tools

`agent/core.py` orchestrates, in **two modes** switcheable via `AGENT_MODE`:

### Fast mode (default, `AGENT_MODE=fast`)
- **Exactly ONE LLM call** per question — no tools are offered, and the tool-free
  `FAST_SYSTEM_PROMPT` (which names no tools) makes tool-call echoing far less likely.
- The **auto-retrieved context** (top-4 chunks, `AUTO_CONTEXT_TOP_K=4`) is appended to
  the user message as `[system note]`, so answers are grounded *by construction*.
- History is trimmed to the last **6** messages (`FAST_HISTORY`) to keep prompts small.
- Response `mode: "fast"`. If the call errors, `mode: "fast-fallback"` with a grounded
  direct answer.

### Agent mode (opt-in, `AGENT_MODE=agent`)
- Auto-RAG runs the same, then the model is offered tools and may loop up to
  `AGENT_MAX_STEPS=4` rounds; history keeps 10 messages (`MAX_HISTORY`).
- **Citation harvesting** — every `search_handbook` result is scanned with a regex and
  merged (with auto-context pages) into the final `citations` array returned to the UI.

### Tools

| Tool | Purpose | Notes |
|---|---|---|
| `search_handbook(query, top_k)` | Keyword retrieval on demand | Same engine as auto-RAG; result blocks carry doc+page headers |
| `calculator(expression)` | CGPA / percentage math | Safe AST evaluator — only numbers, `+ - * / ( ) . %`; no `eval()` |
| `search_web(query)` | Tavily web fallback | Only offered when `ENABLE_WEB_SEARCH=true`; prompt forbids using it before `search_handbook` |

### Mode ladder (what `mode` can report)

| `mode` | Meaning |
|---|---|
| `fast` | single LLM call, grounded by auto-context (default `AGENT_MODE=fast`) |
| `fast-fallback` | single-call path failed → grounded direct answer |
| `clarify` | deterministic clarify pre-pass (zero LLM cost): asked a one-tap disambiguating question first, `options` holds the chips |
| `agent` | model used tools in the loop (`AGENT_MODE=agent`) |
| `rag-fallback` | provider rejected tools → grounded direct answer |
| `rag-fallback-midloop` | errored mid-loop → grounded direct answer |
| `error` | unexpected exception → safe generic message (still HTTP 200) |

Responses that ask a clarifying question (mode `clarify`) also carry an `options`
array the widget renders as one-tap chips, e.g. `["Boys Hostel", "Girls Hostel"]`.

### Tool-call echo defence
Free models sometimes echo a tool-call payload (`{"query": "…", "topk": 5}`) as plain
text instead of answering. Four layers stop it: (1) fast mode uses a tool-free prompt,
(2) `_normalize_question` unwraps any pasted tool-call JSON into the real question,
(3) `_cleanup_answer`/`_looks_like_tool_call` strip stray JSON or regenerate, and
(4) `_grounded_answer` is the final net: it re-queries the last 6 chunks with an explicit
instruction and returns a helpful non-answer as the last resort.

---

## Multi-document support

More than one regulation can live side by side:

| Document | Pages | Applies to |
|---|---|---|
| `data/student_handbook.pdf` → "Handbook 2026-27" | 86 | students admitted 2026-27 onward |
| `data/R23_BTECH_20240322.pdf` → "R23 Handbook" | 238 | older regulation (2023-24 admits) |

Adding another document is one line in `DOC_SOURCES` (register file + citation label);

```python
DOC_SOURCES = [
    {"file": "student_handbook.pdf",   "label": "Handbook 2026-27"},
    {"file": "R23_BTECH_20240322.pdf", "label": "R23 Handbook"},
    {"file": "<new>.pdf",              "label": "<Label>"},
]
```

Text extraction is automatic on next start. The system prompt tells the model the
differences between regulations must be surfaced explicitly ("give each document's rule
with its own citation"). Citations always name the document: `(R23 Handbook p. 57)`.

---

## Personalization & conversation features

- **Student profile** — the widget's ⚙️ lets students set *programme / branch / year /
  semester* (persisted in `localStorage`, sent with every request). `agent/core.py` builds
  a `STUDENT PROFILE: programme=…; branch=…` block appended to the system prompt, so
  answers target the student's actual programme.
- **Clarify-then-answer** — if a rule depends on programme/year and it's unknown, the
  prompt instructs the model to ask **exactly one** clarifying question (never guess).
  The widget auto-detects such questions and offers one-tap answer chips
  (`maybeClarifyChips`: B.Tech/BBA/BCA/B.Sc., CSE/ECE/EEE/…, Year 1–4).
- **Topic-based suggestion chips** — every typed question is folded onto a fixed set
  of handbook topics ("Promotion rules", "Attendance criteria", "CGPA / grading", …).
  Scores use **recency + frequency decay** (a bandit-style ranker:
  `score = count × 2^(−age_days/7)`, half-life 7 d), so recent, repeated asks surface as
  short topic labels. `GET /api/suggestions?limit=3` (default 3) returns clean labels →
  rendered as tap-able chips under the input. Stateless, JSON-persisted
  (`data/query_stats.json`), swappable for a model-based recommender behind the same
  interface.
- **Deterministic clarify pre-pass (zero LLM cost)** — before any LLM call,
  `agent/clarify.py` checks whether the question is ambiguous on a dimension the
  handbook genuinely splits and asks **one question first**:
  - *Boys/Girls hostel* — any hostel/dining/mess/fee/room question asks
    "Boys or Girls hostel?" (rules, facilities and contacts differ per side)
    when the student hasn't already said, whether in the query, recent chat
    history, or a future `profile.hostel` field.
  - *Programme/branch* — when the retrieved chunks for the question actually mix
    ≥2 programmes (e.g. "How many total credits do I need to graduate?") and the
    profile/branch is unknown, it asks "Which programme or branch are you in?".
  - neither fires when a regulation (e.g. "in R23") is named — doc routing
    already disambiguates that axis — and both are suppressed once the student
    declared the value. The reply is `mode:"clarify"` with an `options` array
    the widget renders as one-tap chips. Same rule is echoed in the prompts for
    the LLM-generated path, so the model never mixes the two sides' details.
- **History** — the widget keeps the conversation in memory and sends messages with each
  request (stateless server, no user accounts); the server keeps the last 6 (fast) or 10
  (agent) rounds.
- **Honesty rule** — all prompts now state that content you did *not* retrieve is **not
  proof of absence**: the bot must never claim a policy "is not in the handbook". Instead
  it says it couldn't find it in the pages it has, suggests rephrasings/keywords (e.g.
  `wifi`, `Wi-Fi`, `internet`, `help desk`), and points to the Student Help Desk.

---

## API contract

Base URL: `http://localhost:5000` (dev) · `https://sru-assist.onrender.com` (live).

**`POST /api/chat`**
```json
{
  "message": "What is the minimum pass percentage?",
  "history": [ { "role": "user", "content": "…" }, { "role": "assistant", "content": "…" } ],
  "profile": { "programme": "B.Tech", "branch": "CSE (AI & ML)", "year": "2", "semester": "4" }
}
```
`message` required (1–1000 chars); `profile` keys each ≤40 chars. Response:
```json
{
  "answer": "…markdown text with (Handbook 2026-27 p. 34) citations…",
  "citations": ["Handbook 2026-27 p.34"],
  "tool_calls": [ { "tool": "search_handbook", "args": { "query": "pass marks", "top_k": 5 } } ],
  "mode": "fast",
  "latency_ms": 4123
}
```
`mode` is one of the [ladder](#mode-ladder-what-mode-can-report). `latency_ms` measures the
full server round-trip including the LLM call.

**`GET /api/suggestions`** → `{ "suggestions": ["Promotion rules", "…"] }`,
takes `?limit=` (default 3) → top topic labels by recency-decayed popularity.

**`GET /api/health`** → `{ "status": "ok", "model": "<id>" }`.

**`POST /api/sync`** — portal-push content ingestion (no PDFs shipped). Body is a JSON
manifest (`{"label": …, "sections": [{"page": 5, "text": "…"}]}`) or a `{"url": …}`
pointer; when `SYNC_TOKEN` is set it requires `Authorization: Bearer <token>` (or
`X-Sync-Token`). On success the backend writes a page-marked text file,
registers it in `data/documents.json` (survives restarts), and rebuilds the index
immediately. Returns `{"ok": true, "label": …, "chunks": …, "source": …}`.

Errors: `400 {"error": "message is required"}` / `"message too long (max 1000 chars)"`.
Out-of-scope questions are politely refused. Full contract in `docs/API.md`.

Any stack (PHP, Node, Java…) can integrate — it's stateless HTTP + JSON.

---

## Embeddable widget

`static/widget.js` — **dependency-free vanilla JS** (~400 lines). Drop two tags into any
page:

```html
<script>
  window.SRU_CHAT = {
    apiUrl: "https://sru-assist.onrender.com",  // optional; defaults to its own origin
    botName: "SRU Assist",
    welcome: "Hi! I'm SRU Assist 🤖 …",
  };
</script>
<script src="https://sru-assist.onrender.com/static/widget.js"></script>
```

Features: floating 💬 bubble + panel (460px, brand gradient), mini-markdown renderer with
LaTeX cleanup, citation chips (`📖 Handbook 2026-27 p.34`), typing indicator, profile
⚙️ drawer, dynamic suggestion chips, one-tap clarify chips, safe escaping
(escape-first before any markup), Enter-to-send, busy/disabled handling, and a graceful
"can't reach server" message. All CSS is injected as a namespaced stylesheet; the widget
is safe against sandboxed content because it escapes before rendering.

---

## Evaluation & quality

`tests/golden_set.json` holds **29 real student questions** across both regulations
(`top_k=6` default), each annotated with `expect_pages` — the handbook pages that *must*
be retrieved. Score it any time:

```bash
python scripts/run_eval.py            # retrieval-only, fast, no API cost
python scripts/run_eval.py --k 8      # widen retrieval window
python scripts/run_eval.py --full     # also runs the live agent and checks citations
```

**Baseline (current): 100% hit-rate @ top-6 · MRR 0.79** (29/29). Coverage spans pass
marks, grade scales, SGPA/CGPA, F-grade & I-grade handling, promotion rules, attendance /
condonation, graduation credits, malpractice (CPAM), summer semester, re-evaluation,
dress code, hostel, scholarships, anti-ragging, library, exam fees, ID cards, mentoring,
plus the **wifi-contact** case ("Who do I contact for Wi-Fi problems?" → page 6, added
with the contact-directory fix) — and R23-specific cases (professional/open electives,
honors & minor, non-credit courses, grading scale).

Three cases sit on the top-6 edge (`total-credits` rank 5, `revaluation` rank 5,
`scholarship` rank 6) — treat them as the fragile frontier; any retrieval change must
re-measure them.

The harness is **CI-friendly**: exit code fails under 80% hit-rate. Eval is a **training
dojo before deployment** — any retrieval/prompt change must be measured against it.

---

## Reducing latency

Answers already arrive in a few seconds; to hit a consistent **2–3 s**, fix these in
order.

### 1. The model is the single biggest factor
The default `nvidia/nemotron-3-ultra-550b-a55b:free` is a huge MoE and **writes ~3 tok/s**
(OpenRouter snapshot: P50 latency ~75 s, ~98% uptime — and free-tier availability has
been volatile, ~77–78% over 24 h). At that speed a 100-word answer alone takes 15–40 s of
generation. **Nothing in code fixes that — swap `MODEL_NAME`:**

```env
MODEL_NAME=<a faster model id from https://openrouter.ai/models>
```

Prefer a small/fast model (e.g. an OpenAI/Azure/Gemini/Cerebras or small MoE id) **with
credits**, then verify answer quality holds:
`python scripts/run_eval.py --full`. Real numbers decide the model, not marketing.

### 2. Fewer LLM round-trips (done in code)
One question used to cause up to **5 LLM calls** (auto-RAG + up to 4 tool rounds). There
is now a **`fast` mode — the default**:

- `AGENT_MODE=fast` → **exactly one LLM call**, grounded by auto-retrieved context;
  cited pages still come from the auto-context. Response `mode:"fast"`.
- `AGENT_MODE=agent` → the original multi-step tool loop (`AGENT_MAX_STEPS` rounds,
  `mode:"agent"`), for models where tool-calling is reliable. Two knobs: max 4 rounds,
  `search_web` gated by `ENABLE_WEB_SEARCH`.

### 3. Smaller prompts (done in code)
- `AUTO_CONTEXT_TOP_K=4` (was 6) chunks in the prompt → less time-to-first-token.
- History trimmed to the last **6** messages in fast mode (10 in agent mode).
- `MAX_TOKENS=700` caps each generation → answers stop sooner.
- `LLM_TIMEOUT=90` — a stuck/slow provider call is treated as failed and falls back
  instead of hanging the bubble.

### 4. Deploy-level latency
- Render **free tier sleeps after ~15 min idle** → first request after idle takes ~40 s.
  Use a paid/persistent plan, a cron keep-alive ping, or university hosting to remove
  that spike.
- Optional: SSE streaming is on the roadmap (first token appears while the rest streams),
  already deploy-geared via gunicorn + nginx.

**Check what you're actually hitting:** responses now include `latency_ms` in the
`/api/chat` JSON — benchmark before/after each change.

Quick wins table:

| Change | Effect |
|---|---|
| `MODEL_NAME` → fast model | 5–10× on generation (the essential fix) |
| `AGENT_MODE=fast` (default) | up to 5 calls → 1 call per question |
| `AUTO_CONTEXT_TOP_K=4` | smaller prompt, faster TTFT |
| `MAX_TOKENS=700` | shorter session bound per answer |
| paid hosting / keep-alive | kills the ~40 s cold-start spike |

And remember the **rate-limit ceiling** (see [Model & rate limits](#model--rate-limits-openrouter)):
at 20 RPM and 50 RPD (before the $10 unlock) even a healthy demo can 429; plan quota
before hammering the free model in front of an audience.

---

## Deployment & live URL

**Live:** https://sru-assist.onrender.com (Render free tier, Blueprint `render.yaml`,
`gunicorn app:app --workers 2 --threads 4`).

1. Push to GitHub: `git remote add origin https://github.com/<you>/sru-assist.git && git push -u origin master`.
2. Render → Sign in with GitHub → **New + → Blueprint** → select the repo (reads `render.yaml`).
3. Fill secrets: `OPENROUTER_API_KEY`, `MODEL_NAME`, `TAVILY_API_KEY`.
4. Deploy → HTTPS URL → point any page's widget at it.

Free-tier notes: sleeps after ~15 min idle (first request ~40 s warm-up);
`data/query_stats.json` resets on redeploys (ephemeral disk); OpenRouter's 50 RPD free
quota is shared by every student using the deploy. `$PORT` is respected, so
it also runs on Railway/Fly.io unchanged.

---

## Real portal integration

The live portal **sraap.in** is server-rendered **PHP + Bootstrap 5 + jQuery**. The
widget is paste-in: the two tags in the next section, just before `</body>` (e.g. in
`student/dash_board.php` or a shared footer include). The brand palette was matched to
`assets/css/style.css` (primary **#23468A**, accents **#97B9E2 / #dbe7f7**). Public pages
disable right-click/devtools via inline JS — this does not affect the widget. In
production, restrict CORS in `app.py` (`add_cors`) to `https://sraap.in`.

**There are two halves to the integration** (full guide in `docs/PORTAL_INTEGRATION.md`):

**A · Widget embed** — put the bubble on portal pages:
```html
<script>
  window.SRU_CHAT = { apiUrl: "https://sru-assist.onrender.com", botName: "SRU Assist" };
</script>
<script src="https://sru-assist.onrender.com/static/widget.js"></script>
```

**B · Handbook from the portal, no PDFs in the backend** — two mechanisms:
- *Fetch (recommended)*: register a URL in `DOC_SOURCES`
  (e.g. `{"url": "https://sraap.in/api/handbook", "label": "Handbook 2026-27"}`). The
  portal serves a JSON manifest (`{ "sections": [{"page": 34, "text": "…"}] }`), a PDF,
  or plain text; the bot downloads + indexes it at startup.
- *Push*: the portal admin script calls `POST /api/sync`
  (`Authorization: Bearer <SYNC_TOKEN>`) with the same manifest; the backend writes the
  text, registers it in `data/documents.json`, and rebuilds the index immediately —
  no restart, no committed PDF. A PHP sample and curl examples are in the guide.

Production checklist (details in `PRODUCTIONIZATION.md`):
- [ ] Host behind HTTPS (gunicorn + nginx, or Render/Railway).
- [ ] Restrict CORS to the real portal domain.
- [ ] Add rate limiting / auth if exposed publicly.
- [ ] Swap the free model for a production-grade model in `.env` (and consider the
      one-time $10 top-up to lift the 50/day free-model cap → 1,000/day).
- [ ] Optional: log Q&A pairs to improve the FAQ.

---

## Configuration

| Env var | Required | Default | Meaning |
|---|---|---|---|
| `OPENROUTER_API_KEY` | yes | — | OpenRouter key (never commit) |
| `MODEL_NAME` | no | `nvidia/nemotron-3-ultra-550b-a55b:free` | Any OpenRouter / OpenAI-compatible model id — **swap for a fast model to hit 2–3 s latency** (see rate limits above for the `:free` caps) |
| `AGENT_MODE` | no | `fast` | `fast` = 1 LLM call per question; `agent` = multi-step tool loop |
| `AGENT_MAX_STEPS` | no | `4` | Tool rounds when `AGENT_MODE=agent` |
| `AUTO_CONTEXT_TOP_K` | no | `4` | Handbook chunks injected into the prompt (lower = faster) |
| `MAX_TOKENS` | no | `700` | Answer generation cap (lower = faster) |
| `LLM_TIMEOUT` | no | `90` | Seconds before a hung LLM call falls back |
| `TAVILY_API_KEY` | no | — | Enables `search_web` fallback (agent mode) |
| `ENABLE_WEB_SEARCH` | no | `true` | `false` → handbook-only answers |
| `SYNC_TOKEN` | no | — | Requires `Bearer` header on `POST /api/sync` |
| `OPENROUTER_BASE_URL` | no | `https://openrouter.ai/api/v1` | Point at OpenAI/Azure/Ollama to switch providers |
| `PORT` / `FLASK_PORT` | no | `5000` | Bind port |

`.env` is auto-loaded by `agent/config.py` (no python-dotenv needed). See `.env.example`.

`/api/chat` responses include `latency_ms` for benchmarking latency changes.

---

## Project layout

```
app.py                 Flask routes (chat/health/suggestions/sync), CORS, static + demo
agent/
  core.py              agent loop: clarify pre-pass, fast single-call default, agentic
                       toolbox, fallbacks, auto-RAG context, tool-call echo defence
  clarify.py           deterministic clarify pre-pass (hostel gender / branch) - zero LLM cost
  retriever.py         PDF/URL/manifest ingestion, email-break repair, chunking incl.
                       contact tables, tokenizer+stemmer, BM25, two-stage rerank, routing,
                       query expansion
  tools.py             tool JSON schemas + implementations (search/calculator/search_web)
  prompts.py           system prompt: grounding, citations, clarify rules, format rules,
                       "missing context ≠ absent" honesty rule
  llm.py               OpenAI-compatible client wrapper (OpenRouter, LLM_TIMEOUT)
  config.py            tiny .env loader
  stats.py             topic-bandit suggestion ranking → chips
static/widget.js       embeddable chat widget (vanilla JS, zero deps)
demo/index.html        mock SRAAP portal for demos/screenshots (widget wired in)
data/                  handbook PDFs + extracted text + runtime state
                       (query_stats.json, documents.json); PDFs + .txt are tracked
tests/golden_set.json  29 golden Q&A cases (both regulations, top_k=6)
scripts/
  run_eval.py          retrieval + full-pipeline scoring (CI exit code)
  check_clarify.py     no-cost clarification probes for agent/clarify.py
  extract_handbook.py  rebuild /<slug>.txt from PDFs
docs/
  API.md              integration contract
  PORTAL_INTEGRATION.md  widget embed + on-demand handbook fetch (no bundled PDFs)
ARCHITECTURE.md        design decision record (D1…D15)
PRODUCTIONIZATION.md   university-infra upgrade path
render.yaml            Render Blueprint (deploy-ready)
requirements.txt       5 dependencies only
```

---

## Design decisions

(Full record in `ARCHITECTURE.md`.)

- **D1 · BM25 first, vector DB later** — instant (~10 ms over 690 chunks), deterministic,
  zero heavy deps; one `search()` interface for a clean swap to embeddings later. Measured
  payoff: 100% hit-rate @6 with the two-stage improvement; remaining headroom =
  semantic paraphrase.
- **D1b · Intent-based multi-document routing** — merging regressions blindly dropped
  accuracy to 81%; routing by named regulation restored and beat the single-doc baseline.
- **D1c · Two-stage phrase promotion** — BM25 alone buries long table pages that hold the
  true answer; exact adjacent-pair promotion rescues them (preserving recall).
- **D2 · Always retrieve before generating (auto-RAG)** — answers are grounded by
  construction, not by hoping the model asks for context.
- **D3 · Agentic tool-calling with hard fallbacks** — free-tier models may lack tool
  support; every call is wrapped so failure ⇒ grounded direct answer. Reliability over
  purity for students.
- **D4 · Clarify-then-personalize** — one clarifying question max; profile injected into
  the system prompt. Killed the worst bug class (B.Tech rules applied to BBA students).
- **D5 · Citations are a contract** — pages flow from chunk metadata, returned as JSON,
  so any UI renders source chips and evaluators verify grounding mechanically.
- **D6 · Statelessness** — history rides with each request; drops into any portal without
  touching identity systems; horizontal scaling needs no shared state.
- **D7 · Chat-safe formatting** — LaTeX banned in prompts + mini-markdown renderer with
  LaTeX cleanup as a second net.
- **D8 · Topic-bandit suggestion ranking** — typed questions are folded onto fixed
  handbook topics and scored by **recency × frequency decay** (`count × 2^(−age/7)`), so the
  chips reflect what students actually just asked, capped at 3. JSON-persisted,
  swappable for a model-based recommender behind the same `get_suggestions` interface.
- **D11 · Tool-call echo defence** — separate tool-free prompt in fast mode + JSON unwrap
  (`_normalize_question`) + cleanup/regenerate (`_cleanup_answer`, `_looks_like_tool_call`)
  + the `_grounded_answer` final net.
- **D12 · Contact-directory row chunking** — paragraphs carrying an email *and* a mobile
  number are split into ≤400-char row groups (`CONTACT_TARGET_CHARS`), so "Who do I
  contact for Wi-Fi?" hits the Wi-Fi row instead of a 1500-char dump of every contact.
- **D13 · Query-side synonym expansion** — high-value synonyms are appended to the query
  string only (`QUERY_EXPANSIONS`/`expand_query()`), never to the index, widening recall
  for questions that name things differently than the handbook ("internet not working" vs
  "Wi-Fi related issues") without drifting the golden-set baseline.
- **D14 · Repair PDF line-splits in text extraction** — `_repair_email_breaks()` rejoins
  addresses the PDF text layer broke across lines (`sru.edu.i\n` → `@sru.edu.in`), because
  a "the handbook has a typo" bug is really a PDF-extraction artifact.
- **D15 · Deterministic clarify pre-pass** — asking (Boys/Girls hostel, programme/branch)
  is decided in *code* before any LLM call (`agent/clarify.py`, zero token cost), not left
  to the model: the hostel facet uses a document-level fact (both hostels exist), the
  branch facet requires the retrieved chunks to actually mix ≥2 programmes, both respect
  query/history/profile and skip regulation-named questions. Fixes the "gave the other
  side's info" failure class without spending LLM quota.

---

## Known limitations & roadmap

- **Latency is model-bound** — the default free model writes ~3 tok/s (P50 ≈ 75 s);
  with `AGENT_MODE=fast` the same model still takes seconds. Full 2–3 s answers need a
  faster `MODEL_NAME` (see "Reducing latency"). Responses include `latency_ms` to measure it.
- **Free-tier constraints are real** — 20 RPM / 50 RPD (unless ≥$10 lifetime credits →
  1,000 RPD), lower server priority, provider logging on free endpoints, and volatile
  availability. Prototype-grade, not an SLA. The $10 unlock + a paid/fast model is the
  path to production.
- **Contact rows split at ~400 chars** — a single entry can straddle two adjacent chunks
  (name/room in one, phone/email in the next). The top-6 pool usually still contains both,
  but worst-case wording can land one half lower than ideal.
- **Wifi phrasing still has edge cases** — natural rephrasings of the Wi-Fi contact row
  (e.g. "Internet not working, where to report it?") retrieve it at rank ~7 in testing,
  outside the top-6 window. The synonym map covers the common phrasings; more expansion
  or embedding retrieval would close the rest.
- **Semantic paraphrase** — BM25 is keyword-based; rephrasings may miss. Roadmap: hybrid
  BM25 + embedding retrieval (FAISS/Chroma behind the existing `search()` interface).
- **PDF extraction quality** — complex tables can flatten during text pull (the grading
  table survives; others need visual QA per document; email line-breaks were a real
  example now fixed). Portal-pushed JSON manifests (`/api/sync`) keep original structure
  and avoid this entirely.
- **No streaming** — answers arrive as one JSON message. Roadmap: SSE streaming
  (`stream=True` on the client), already deploy-geared via gunicorn + nginx.
- **Clarify turns add a round-trip (by design)** — Boys/Girls hostel and
  programme/branch questions that don't declare the dimension pause for exactly
  one clarifying question (`mode:"clarify"`, one-tap chips) before answering.
  Suppressions (query/history/profile, regulation-named questions) are pinned by
  `python scripts/check_clarify.py`, so the check stays cheap and deterministic.
- Also on the roadmap (see `PRODUCTIONIZATION.md`): Postgres callbacks/persistence,
  Redis caching for repeat FAQs, rate limiting, "view sources" expander in the widget,
  multilingual intake, BI/analytics on Q&A logs.

---

## Team workflow & rules

- Git repo per folder; use branches + PRs.
- AI coding tools: read `AGENTS.md` first (stack rules live there).
- **Never commit `.env`, real API keys, or student personal data.**
- Quality gate before hand-off: start `python app.py`, ask *"What is the minimum pass
  marks?"* and verify the answer cites pages.
- Run `python scripts/run_eval.py` before any retrieval/prompt change; must stay ≥80%
  (currently 100% @29).