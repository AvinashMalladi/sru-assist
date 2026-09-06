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
        │      • compound-word normalization ("non-credit" ↔ "noncredit")
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
4. [Retrieval engine (how answers are found)](#retrieval-engine)
5. [Agentic loop & tools](#agentic-loop--tools)
6. [Multi-document support (2026-27 + R23)](#multi-document-support)
7. [Personalization, clarifying questions & suggestions](#personalization--conversation-features)
8. [API contract](#api-contract)
9. [Embeddable widget](#embeddable-widget)
10. [Evaluation & quality](#evaluation--quality)
11. [Deployment (live)](#deployment--live-url)
12. [Real portal integration notes (sraap.in)](#real-portal-integration)
13. [Configuration (.env)](#configuration)
14. [Project layout](#project-layout)
15. [Design decisions (why it was built this way)](#design-decisions)
16. [Known limitations & roadmap](#known-limitations--roadmap)
17. [Team workflow & rules](#team-workflow--rules)

---

## What has been built

Built by the SRU student project team (2026). Each bullet maps to a commit in `git log`:

| # | Milestone | What it delivered |
|---|---|---|
| 1 | **SRU Assist v1** | Working agentic handbook chatbot: Flask API (`POST /api/chat`, `GET /api/health`), page-based chunking + pure-Python BM25 retrieval over the 86-page Student Handbook, LLM tool-calling loop via OpenRouter, embeddable vanilla-JS widget + mock demo portal. |
| 2 | **Chat-friendly formatting** | LaTeX/math markup banned in prompts; the widget ships a **mini-markdown renderer** (paragraphs, dash bullets, numbered lists, tables, bold, inline code, subscripts) with LaTeX cleanup (`\frac`, `\times`, `\[...\]`…) as a second safety net. Fixes the "raw `\frac` in the chat bubble" failure class seen in testing. |
| 3 | **Personalization & clarify-then-answer** | Student profile (⚙️ in widget: programme/branch/year/semester) injected into the system prompt, persisted in `localStorage`. When a rule depends on programme/year and it is unknown, the agent asks **exactly ONE** clarifying question instead of guessing. Popular-search tracking (`agent/stats.py` → `data/query_stats.json`) powers dynamic suggestion chips. |
| 4 | **Branding & portal prep** | Widget + demo rebranded to the SRAAP/SRU palette (primary **#23468A**, accents #97B9E2 / #dbe7f7), matching the live portal's stylesheet. Real-portal integration notes written up (see below). |
| 5 | **Production readiness** | `gunicorn` startup, `$PORT`/`FLASK_PORT` support, `render.yaml` Blueprint for one-click Render deploy. Deployed live at **https://sru-assist.onrender.com**. |
| 6 | **Documented live deployment** | Deploy URL recorded; README deploy guide verified. |
| 7 | **Eval harness + contract** | `tests/golden_set.json` (linked below), `docs/API.md` (API contract), `ARCHITECTURE.md` (decision record), `PRODUCTIONIZATION.md` (path to university infra). CI-friendly exit code (fails under 80% hit-rate). |
| 8 | **Multi-document + intent routing** | Second regulation added — **R23 B.Tech Handbook** (238 pages) — with per-document indexes, intent-based routing (name a regulation → search only that doc; comparison → split; else default to current handbook), `(R23 Handbook p. N)` citations. Eval expanded to **27 golden cases @ 93% → 100% hit-rate**. |
| 9 | **100% retrieval hit-rate** | Two-stage retrieval: BM25 recall + **exact query-phrase promotion** and **compound-word normalization** — e.g. "non-credit" matches the PDF's "noncredit". Final baseline: **100% hit-rate @ top-6, MRR 0.76** across all 27 cases. |

**Current baseline:** `100% hit-rate @ top-6 · MRR 0.76` on 28 golden questions spanning
BOTH regulations. Remaining headroom is semantic paraphrase — the motivation for hybrid
embedding retrieval (roadmap).

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
   ├─1► auto-retrieve: BM25 over handbook chunks (always; grounds the model)
   │
   ├─2► LLM (OpenRouter, OpenAI-compatible) with tools:
   │      search_handbook(query)     more retrieval on demand
   │      calculator(expr)           safe arithmetic for CGPA math
   │      search_web(query)          Tavily fallback ONLY if handbook lacks it
   │    loop up to MAX_STEPS=4 tool rounds
   │
   └─3► answer + page citations  (+ mode/tool_calls metadata)
```

**Key guarantee — never crashes the widget:** if the provider rejects tool-calling or any
LLM call errors mid-loop, `core.py` degrades to a *grounded no-tool answer*
(`_grounded_answer`, mode `rag-fallback` / `rag-fallback-midloop`) instead of failing.
The HTTP layer returns HTTP 200 with `mode:"error"` and a safe message on any unexpected
exception.

---

## Retrieval engine

Files: `agent/retriever.py` (all logic), built on text extracted by `pypdf` (lazy,
on first load, per document).

**Pipeline (per document in `data/`):**
1. **Extract** PDF → `data/<slug>.txt` with `===== PAGE <n> =====` markers.
2. **Page-based chunking** → paragraphs joined into chunks of ≤1400 chars (hard-split
   overlong blocks; keeps ~300 chunks per handbook).
3. **Tokenize + stem** → lowercase tokens with a cheap suffix stripper
   (`pass`↔`passing`, `mark`↔`marks`), stopword removal.
4. **Index** → a pure-Python **BM25** scorer (`k1=1.4`, `b=0.72`, standard IDF), one
   compound index + one per-document sub-index.

**Single search call does:**
- **Intent-based routing** (`_doc_hints`): query names a regulation (e.g. "in R23…") →
  search that document only; names several (comparison) → evenly round-robin across
  them; names none → default to the current handbook (the proven single-doc baseline).
- **Two-stage reranking** (`_phrase_rerank`): BM25 supplies recall; a second pass scans
  candidates for the query's *adjacent term pairs* as an exact phrase and promotes those
  chunks to the front (preserving BM25 order inside each group). "Promote, don't
  replace" keeps recall safe — non-matches backfill instead of being discarded.
- **Compound-word normalization**: "non-credit" matches the PDF's "noncredit",
  "re-evaluation" ↔ "reevaluation" (handled inside `tokenize`).

**Why BM25 and not a vector DB?** BM25 over ~300–600 chunks is instant (milliseconds),
deterministic, needs no model downloads or GPU, and has zero heavy dependencies. The
retriever exposes one stable interface — `get_retriever().search(query, top_k)` and
`format_hits(query, top_k)` — so a future embedding/FAISS/Chroma upgrade touches one file.

---

## Agentic loop & tools

`agent/core.py` orchestrates:
1. **Auto-RAG** — the top-6 chunks for the latest question always ride into the prompt
   as `[system note]` context, so answers are grounded *by construction* even if the
   model never calls a tool.
2. **LLM with tools** — the model decides when to search again, compute, or (optionally)
   hit the web. Loop bounded at `MAX_STEPS=4`.
3. **Citation harvesting** — every `search_handbook` result is scanned with a regex
   (`[<label> · page <n>]`) and merged (with auto-context pages) into the final
   `citations` array returned to the UI.

Tools (`agent/tools.py`):

| Tool | Purpose | Notes |
|---|---|---|
| `search_handbook(query, top_k)` | Keyword retrieval on demand | Same engine as auto-RAG; result blocks carry doc+page headers |
| `calculator(expression)` | CGPA / percentage math | Safe AST evaluator — only numbers, `+ - * / ( ) . %`; no `eval()` |
| `search_web(query)` | Tavily web fallback | Only exposed when `ENABLE_WEB_SEARCH=true`; prompt forbids using it before `search_handbook` |

The default model is `nvidia/nemotron-3-ultra-550b-a55b:free` on OpenRouter — swappable
via `.env` with no code changes (see PRODUCTIONIZATION.md for provider table).

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
- **Popular-search suggestions** — every question is normalized and counted
  (`agent/stats.py`, thread-safe, persisted to `data/query_stats.json`). `GET
  /api/suggestions` returns the most-asked questions (padded with curated defaults) →
  rendered as tap-able chips under the input.
- **History** — the widget keeps the conversation in memory and sends the last 10
  messages with each request (stateless server, no user accounts).

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
`message` required (1–1000 chars). Response:
```json
{
  "answer": "…markdown text with (Handbook 2026-27 p. 34) citations…",
  "citations": ["Handbook 2026-27 p.34"],
  "tool_calls": [ { "tool": "search_handbook", "args": { "query": "pass marks", "top_k": 5 } } ],
  "mode": "agent"
}
```
| `mode` | Meaning |
|---|---|
| `fast` | single LLM call, grounded by auto-context (default `AGENT_MODE=fast`) |
| `fast-fallback` | single-call path failed → grounded direct answer |
| `agent` | model used tools in the loop (`AGENT_MODE=agent`) |
| `rag-fallback` | provider rejected tools → grounded direct answer |
| `rag-fallback-midloop` | errored mid-loop → grounded direct answer |
| `error` | unexpected exception → safe generic message (still HTTP 200) |

**`GET /api/suggestions`** → `{ "suggestions": ["…", "…"] }` (most-searched first).
**`GET /api/health`** → `{ "status": "ok", "model": "<id>" }`.

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

features: floating 💬 bubble + panel (460px, brand gradient), mini-markdown renderer with
LaTeX cleanup, citation chips (`📖 Handbook 2026-27 p.34`), typing indicator, profile
⚙️ drawer, dynamic suggestion chips, one-tap clarify chips, safe escaping
(escape-first before any markup), Enter-to-send, busy/disabled handling, and a graceful
"can't reach server" message. All CSS is injected as a namespaced stylesheet; the widget
is safe against sandboxed content because it escapes before rendering.

---

## Evaluation & quality

`tests/golden_set.json` holds **28 real student questions** across both regulations,
each annotated with `expect_pages` — the handbook pages that *must* be retrieved. Score it
any time:

```bash
python scripts/run_eval.py            # retrieval-only, fast, no API cost
python scripts/run_eval.py --k 8      # widen retrieval window
python scripts/run_eval.py --full     # also runs the live agent and checks citations
```

**Baseline (current): 100% hit-rate @ top-6 · MRR 0.76** (28/28). Coverage spans pass
marks, grade scales, SGPA/CGPA, F-grade & I-grade handling, promotion rules, attendance /
condonation, graduation credits, malpractice (CPAM), summer semester, re-evaluation,
dress code, hostel, scholarships, anti-ragging, library, exam fees, ID cards, mentoring —
plus R23-specific cases (professional/open electives, honors & minor, non-credit
courses, grading scale).

The harness is **CI-friendly**: exit code fails under 80% hit-rate. Eval is a **training
dojo before deployment** — any retrieval/prompt change must be measured against it.

---

## Reducing latency

Answers already arrive in a few seconds; to hit a consistent **2–3 s**, fix these in order.

### 1. The model is the single biggest factor
The default `nvidia/nemotron-3-ultra-550b-a55b:free` is a huge MoE and **writes ~5 tok/s**
(p50 latency 42 s, 98.7% uptime). At that speed a 100-word answer alone takes 15–40 s of
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

---

## Deployment & live URL

**Live:** https://sru-assist.onrender.com (Render free tier, Blueprint `render.yaml`,
`gunicorn app:app --workers 2 --threads 4`).

1. Push to GitHub: `git remote add origin https://github.com/<you>/sru-assist.git && git push -u origin master`.
2. Render → Sign in with GitHub → **New + → Blueprint** → select the repo (reads `render.yaml`).
3. Fill secrets: `OPENROUTER_API_KEY`, `MODEL_NAME`, `TAVILY_API_KEY`.
4. Deploy → HTTPS URL → point any page's widget at it.

Free-tier notes: sleeps after ~15 min idle (first request ~40 s warm-up);
`data/query_stats.json` resets on redeploys (ephemeral disk). `$PORT` is respected, so
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
- [ ] Swap the free model for a production-grade model in `.env`.
- [ ] Optional: log Q&A pairs to improve the FAQ.

---

## Configuration

| Env var | Required | Default | Meaning |
|---|---|---|---|
| `OPENROUTER_API_KEY` | yes | — | OpenRouter key (never commit) |
| `MODEL_NAME` | no | `nvidia/nemotron-3-ultra-550b-a55b:free` | Any OpenRouter / OpenAI-compatible model id — **swap for a fast model to hit 2–3 s latency** |
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
  core.py              agent loop: fast single-call default, agentic toolbox, fallbacks
  retriever.py         PDF/URL/manifest ingestion, chunking, BM25, two-stage rerank, routing
  tools.py             tool JSON schemas + implementations (search/calculator/search_web)
  prompts.py           system prompt: grounding, citations, clarify rules, format rules
  llm.py               OpenAI-compatible client wrapper (OpenRouter)
  config.py            tiny .env loader
  stats.py             popularity tracking → suggestion chips
static/widget.js       embeddable chat widget (vanilla JS, zero deps)
demo/index.html        mock SRAAP portal for demos/screenshots (widget wired in)
data/                  handbook PDFs + extracted text + query_stats.json + documents.json
tests/golden_set.json  28 golden Q&A cases (both regulations)
scripts/
  run_eval.py          retrieval + full-pipeline scoring (CI exit code)
  extract_handbook.py  rebuild /<slug>.txt from PDFs
docs/
  API.md              integration contract
  PORTAL_INTEGRATION.md  widget embed + on-demand handbook fetch (no bundled PDFs)
ARCHITECTURE.md        design decision record (D1…D8)
PRODUCTIONIZATION.md   university-infra upgrade path
render.yaml            Render Blueprint (deploy-ready)
requirements.txt       5 dependencies only
```

---

## Design decisions

(Full record in `ARCHITECTURE.md`.)

- **D1 · BM25 first, vector DB later** — instant, deterministic, zero heavy deps; one
  `search()` interface for a clean swap to embeddings later. Measured payoff: 100%
  hit-rate @6 with the two-stage improvement; remaining headroom = semantic paraphrase.
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
- **D8 · Popularity tracking without infra** — JSON-file counters power dynamic
  suggestion chips; swappable for Redis later behind the same interface.

---

## Known limitations & roadmap

- **Latency is model-bound** — the default free model writes ~5 tok/s; with
  `AGENT_MODE=fast` the same model still takes seconds. Full 2–3 s answers need a faster
  `MODEL_NAME` (see "Reducing latency"). Responses include `latency_ms` to measure it.
- **Semantic paraphrase** — BM25 is keyword-based; rephrasings may miss. Roadmap: hybrid
  BM25 + embedding retrieval (FAISS/Chroma behind the existing `search()` interface).
- **PDF extraction quality** — complex tables can flatten during text pull (the grading
  table survives; others need visual QA per document). Portal-pushed JSON manifests
  (`/api/sync`) keep original structure and avoid this entirely.
- **No streaming** — answers arrive as one JSON message. Roadmap: SSE streaming
  (`stream=True` on the client), already deploy-geared via gunicorn + nginx.
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
  (currently 100%).