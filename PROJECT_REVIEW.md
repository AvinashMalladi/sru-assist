# SRU Assist — Complete Project Breakdown for Mentor Review

---

## WHAT WE BUILT

**SRU Assist** — an AI chatbot that answers student questions about SR University's official handbooks. It's embedded as a floating chat widget inside the university's student portal (SRAAP).

---

## THE PROBLEM WE SOLVED

Students have 2 PDF handbooks (86 + 238 pages) covering rules, grading, attendance, hostel, exams, etc. Finding specific answers manually is painful. We built an AI that reads these PDFs and gives instant, page-cited answers inside the portal they already use.

---

## STEP-BY-STEP: WHAT WE DID FROM START TO END

### Step 1 — Data Collection & Extraction
- Collected 2 official PDFs: `student_handbook.pdf` (86pp, 2026-27) + `R23_BTECH_20240322.pdf` (238pp, old regulation)
- Built `scripts/extract_handbook.py` to convert PDFs → plain text with page markers (`--- Page N ---`)
- Pre-extracted `.txt` files stored in `data/` for fast loading (no repeated PDF parsing)

### Step 2 — Retrieval Engine (BM25 Search)
- Built `agent/retriever.py` (548 lines) — the heart of the system
- **Chunking**: splits text into ≤1400 char chunks at paragraph boundaries; contact tables get special ≤400 char row grouping
- **Tokenization**: custom tokenizer with split + hyphenless forms, 4-rule stemmer, ~40 stopwords
- **BM25 scoring**: k1=1.4, b=0.72 — per-document sub-indexes + compound index
- **Query expansion & typo tolerance**: maps student phrasing to official terminology (e.g., "slips"/"cheating" → "unfair means/CPAM", "mis exam" → "mid exam", "backlog" → "supplementary/F grade")
- **Intent routing**: detects "old regulation" questions → routes to R23 doc only
- **Two-stage reranking**: adjacent-pair promotion for better relevance
- **No vector DB, no torch, no langchain** — pure Python for portability

### Step 3 — LLM Integration
- Built `agent/llm.py` — thin wrapper around OpenRouter (using `openai` client)
- Default model: `nvidia/nemotron-3-ultra-550b-a55b:free` with automatic fallback failover chain (`nemotron-3.5-lightning:free`, `google/gemma-4-31b-it:free`) to survive upstream 503/overload spikes
- Automated thinking/reasoning trace stripping to ensure clean student responses

### Step 4 — Agent Core (Orchestration)
- Built `agent/core.py` (328 lines) — the brain
- **Two modes**:
  - **Fast mode** (default): 1 LLM call, retrieved chunks injected as context → instant answer
  - **Agentic mode** (`AGENT_MODE=agent`): multi-step loop with tool calls (up to 4 steps)
- **Clarify pre-pass**: before LLM, deterministic regex checks if question needs clarification (e.g., "hostel" without specifying gender → asks "boys or girls?")
- **Profile injection**: extracts student's programme/branch/year from chat and injects into system prompt
- **Citation harvesting**: regex extracts `[text · page N]` citations from LLM output
- **Grounded fallback**: if answer looks ungrounded, auto-regenerates with top-6 chunks + stricter prompt
- **Tool-call echo defense**: strips stray JSON/tool syntax from LLM output

### Step 5 — Tools
- Built `agent/tools.py`:
  - `search_handbook(query)` — calls the BM25 retriever
  - `calculator(expression)` — safe AST evaluator (for CGPA calculations etc.)
  - `search_web(query)` — Tavily web search (optional, gated by env flag)

### Step 6 — Prompts
- Built `agent/prompts.py` — 3 carefully crafted prompts:
  - `SYSTEM_PROMPT` — agent mode: grounding rules, multi-regulation awareness, citation format, "honesty rule" (if info missing, say so)
  - `FAST_SYSTEM_PROMPT` — fast mode: same rules but "you have NO tools"
  - `FALLBACK_PROMPT` — for auto-regeneration when answer quality is low

### Step 7 — Clarification System
- Built `agent/clarify.py` (143 lines) — zero-LLM cost clarification
- Detects when question is ambiguous (hostel gender, branch-specific, etc.)
- Returns chip options for one-tap selection
- Checks actual document content (e.g., only asks gender if handbook actually has gendered hostels)

### Step 8 — Suggestion System
- Built `agent/stats.py` — topic-bandit ranker
- Tracks query counts with time-decay (7-day half-life)
- Returns top 3 trending topics as suggestion chips
- Falls back to defaults: "Promotion rules", "Attendance criteria", "CGPA / grading"

### Step 9 — Flask API
- Built `app.py` (146 lines):
  - `POST /api/chat` — main endpoint (validates 1–1000 chars, runs agent, tracks latency)
  - `GET /api/suggestions` — trending topic chips
  - `GET /api/health` — status check
  - `POST /api/sync` — portal pushes/feeds handbook content (Bearer token auth)
  - `GET /` — serves the demo page
  - CORS enabled for all origins

### Step 10 — Frontend Widget
- Built `static/widget.js` (440 lines) — **zero-dependency vanilla JS**
- Floating chat bubble → expandable 460px panel
- Brand gradient (#23468A → #3E6BC0)
- In-flight request cancellation via interactive **Stop button** (`AbortController`)
- Cross-browser keyboard Enter key support with `preventDefault`
- Mini markdown renderer (tables, bold, italic, code, lists, LaTeX cleanup)
- One-tap option chips (server-driven clarify + heuristic chips)
- Profile capture from chat answers (localStorage)
- Suggestion chips auto-refresh

### Step 11 — Demo Portal
- Built `demo/index.html` — mock SRAAP portal with:
  - University branding, sidebar nav
  - Fake student dashboard (Avinash, B.Tech CSE AI&ML, Sem IV)
  - Widget embedded in 3 lines of code

### Step 12 — Testing & Evaluation
- Built `scripts/run_eval.py` — automated eval against 29 golden test cases
- **Result: 100% hit-rate @ top-6, MRR 0.79**
- Built `scripts/check_clarify.py` — 19 probes for clarification logic
- All in `tests/golden_set.json`

### Step 13 — Deployment
- Deployed to **Render.com** (free tier)
- `render.yaml` blueprint: Python 3.13.7, gunicorn, 2 workers, 4 threads
- Live at: `https://sru-assist-uyo4.onrender.com`

---

## TECHNOLOGY STACK

| Layer | What | Why |
|-------|------|-----|
| Backend | Python 3.12+, Flask | Lightweight, no database needed |
| LLM | OpenRouter (free tier nemotron model) | Zero cost, good enough for RAG |
| Search | Pure Python BM25 | No vector DB, portable, fast |
| PDF parsing | pypdf | Lightweight, no heavy deps |
| Frontend | Vanilla JS (no framework) | Zero dependencies, embeddable |
| Deployment | Render.com | Free tier, auto-deploys from git |

**Total dependencies: 5** (flask, openai, requests, pypdf, gunicorn)

---

## HOW TO EXPLAIN TO YOUR MENTOR — SUGGESTED FLOW

### 1. Start with the Problem (2 min)
> "Students struggle to find rules in 300+ page PDF handbooks. We built an AI chatbot that gives instant, cited answers inside the existing portal."

### 2. Show the Live Demo (3 min)
- Open `https://sru-assist-uyo4.onrender.com`
- Ask: "What is the minimum pass marks?" → shows cited answer
- Ask: "Tell me about hostel" → shows clarification chips (boys/girls)
- Show suggestion chips at bottom

### 3. Explain the Architecture (5 min)
Point to this flow:
```
Student types question
    → Clarify pre-pass (regex, zero cost, checks if ambiguous)
    → BM25 retrieval (top chunks from 2 handbooks)
    → LLM generates answer with chunks as context
    → Citation extraction & grounding check
    → Answer with page references
```

### 4. Explain Key Technical Decisions (5 min)
- **Why BM25 not vector search?** — Portable, no GPU needed, 100% hit rate on test set
- **Why two modes?** — Fast (1 call) for simple questions, Agentic for complex multi-step
- **Why clarify before LLM?** — Saves API calls, deterministic, zero cost
- **Why vanilla JS widget?** — Drops into any portal with 3 lines, no React/Vue dependency

### 5. Show the Evaluation (2 min)
- 29 golden test cases, 100% retrieval hit rate
- MRR 0.79 (relevant answers always in top results)

### 6. Explain Portal Integration (3 min)
This is the key part — **how the real portal connects**:

---

## PORTAL INTEGRATION — EXACTLY HOW IT WORKS

There are **two ways** the real portal integrates:

### Option A: Embed the Widget (3 lines)
The portal team adds these 3 lines to their portal page:
```html
<script>
  window.SRU_CHAT = { apiUrl: "https://sru-assist-uyo4.onrender.com" };
</script>
<script src="https://sru-assist-uyo4.onrender.com/static/widget.js"></script>
```
That's it. The floating chat bubble appears automatically.

### Option B: Sync Live Portal Data (for up-to-date content)
If the portal has live student data (not just static PDFs), the portal backend pushes content:

**Portal sends a JSON manifest:**
```bash
curl -X POST https://sru-assist-uyo4.onrender.com/api/sync \
  -H "Authorization: Bearer YOUR_SYNC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sections":[{"page":1,"text":"Current exam schedule..."}]}'
```

Or the bot **fetches from a URL** the portal provides:
```bash
curl -X POST https://sru-assist-uyo4.onrender.com/api/sync \
  -H "Authorization: Bearer YOUR_SYNC_TOKEN" \
  -d '{"url":"https://sraap.in/handbook.json"}'
```

The `SYNC_TOKEN` (set in `.env`) prevents unauthorized access.

**Detailed integration guide**: `docs/PORTAL_INTEGRATION.md` (196 lines, includes PHP examples)

---

## PROJECT STRUCTURE (for reference)

```
sru-chatbot/
├── agent/              # Backend brain
│   ├── core.py         # Orchestration (328 lines)
│   ├── retriever.py    # BM25 search (548 lines) ← biggest file
│   ├── llm.py          # OpenRouter wrapper
│   ├── tools.py        # search + calculator + web
│   ├── prompts.py      # System prompts
│   ├── clarify.py      # Ambiguity detection
│   ├── config.py       # .env loader
│   └── stats.py        # Suggestion ranker
├── app.py              # Flask API (146 lines)
├── static/widget.js    # Chat widget (404 lines)
├── demo/index.html     # Mock portal
├── data/               # PDFs + extracted text
├── scripts/            # Eval + extraction scripts
├── tests/              # Golden test set
└── docs/               # API + integration docs
```

---

## WHERE TO START EXPLAINING

1. **Start with the demo** — show it working live
2. **Then show `agent/retriever.py`** — explain the retrieval pipeline (this is the core innovation)
3. **Then show `agent/core.py`** — explain the orchestration flow
4. **Then show `static/widget.js`** — show how the frontend works
5. **End with `docs/PORTAL_INTEGRATION.md`** — show how it plugs into the real portal
