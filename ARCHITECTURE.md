# Architecture & Decision Record

## What this system is
An agentic RAG chatbot that answers student questions strictly from the SR
University Student Handbook, exposed as (a) an HTTP API and (b) an embeddable
portal widget.

## Request flow
```
student question
      │
      ▼
Flask  POST /api/chat  ──►  agent/core.run_agent()
      │
      ├─1► auto-retrieve: BM25 over handbook chunks (always; grounds the model)
      │
      ├─2► LLM (OpenRouter, OpenAI-compatible) with tools:
      │      search_handbook(query)   more retrieval on demand
      │      calculator(expr)         safe arithmetic for CGPA math
      │      search_web(query)        Tavily fallback ONLY if handbook lacks it
      │    loop up to MAX_STEPS=4 tool rounds
      │
      └─3► answer + page citations  (+ mode/tool_calls metadata)
```
If the provider rejects tool-calling or errors mid-loop, `core.py` degrades to a
grounded no-tool answer instead of failing — the widget never shows a crash.

## Decisions and their reasons

### D1 · BM25 first, vector DB later
Pure-python BM25 (no numpy/torch/langchain). At handbook scale it is instant,
deterministic, dependency-free, and trivially portable. The retriever exposes
one interface (`search(query, top_k)`), so swapping in embeddings/FAISS/Chroma
later changes one file. Measured on the 27-case golden set spanning two
regulations: 100% hit-rate @6, MRR 0.76 — after adding a second retrieval
stage: BM25 candidates are promoted when their text contains the query's
adjacent term pairs as an exact phrase (handles hyphen/compound variants,
e.g. "non-credit" vs the PDF's "noncredit"). Remaining headroom is semantic
paraphrase, which motivates hybrid retrieval next.

### D1c · Two-stage phrase promotion
BM25 alone over-favors short chunks repeating a single query term; long table
pages holding the true answer sink under length normalization. Stage two scans
each document's candidate pool for exact adjacent-pair matches ("professional
elective") and moves those chunks to the front, preserving BM25 order within
each group. Promote-not-replace keeps recall safe: non-matching results
backfill instead of being discarded.

### D1b · Intent-based multi-document routing
With multiple regulations indexed, naive merged search pollutes results (the
wrong regulation crowds out the right one — measured drop to 81%). Instead:
queries naming a regulation search only that document's sub-index; comparison
questions split slots evenly; everything else searches the current handbook
exactly as the proven single-doc baseline did.

### D2 · Always retrieve before generating (auto-RAG)
Even if the model never calls a tool, top-6 chunks ride along with the prompt.
This makes answers grounded by construction, not by hoping the model asks.

### D3 · Agentic tool-calling with hard fallbacks
The model chooses when to search again or calculate. Free-tier models
sometimes lack tool support → every LLM call is wrapped: failure ⇒ grounded
direct-answer path (`_grounded_answer`). Reliability beats purity for students.

### D4 · Clarify-then-personalize instead of guessing
Handbook rules differ by programme/year. The profile (from the widget's ⚙️)
is injected into the system prompt; when a rule depends on unknown programme/
year, the agent must ask exactly ONE clarifying question. This killed the
worst class of wrong answers (applying B.Tech rules to BBA students).

### D5 · Citations are a contract
Every policy claim carries `(Handbook p. X)`; pages flow from chunk metadata.
Citations returned in JSON let any UI render source chips and let evaluators
verify grounding mechanically.

### D6 · Statelessness
No user accounts, no server-side sessions. History rides with each request.
Consequence: the API drops into any portal without touching their identity
system, and horizontal scaling needs no shared state.

### D7 · Formatting constrained to chat-safe markdown
Prompts ban LaTeX/math markup; widget ships a mini-markdown renderer (tables,
bold, lists) with LaTeX cleanup as a second net. Fixes the "raw \frac in the
bubble" failure class observed in testing.

### D8 · Topic-bandit suggestion ranking without infra
Typed questions fold onto fixed handbook topics and are scored by **recency ×
frequency decay** (`Σ 2^(-age_days/7)`, half-life 7 d), so chips mirror what
students just asked and stale history fades. Returns up to 3 clean labels
(`/api/suggestions?limit=3`); raw query counts are persisted too. Swap for a
model-based recommender/Redis later; the `get_suggestions` interface stays.

### D9 · Latency-first fast mode
Default is a single LLM call grounded by auto-context (`AGENT_MODE=fast`).
The multi-step tool loop remains opt-in (`AGENT_MODE=agent`) for models with
solid tool-calling. The real latency lever is model choice (~5 tok/s free model
vs fast paid tiers); server-side knobs (`AUTO_CONTEXT_TOP_K`, `MAX_TOKENS`,
`LLM_TIMEOUT`) shrink prompt size and generation caps. `/api/chat` returns
`latency_ms` so every change is measurable.

### D10 · Content from the portal, not the repo
Sources may be `file` (bundled PDF), `url` (portal-hosted PDF/JSON/text, fetched
at boot), or `txt` (pushed via `POST /api/sync`, registered in
`data/documents.json`, rebuilt in place). The portal stays the single source of
truth; the backend stores only a cacheable text copy and needs no PDF.

### D11 · Tool-call echo defence
Free models sometimes echo the tool-call payload as plain text (e.g.
`{"query": "...", "topk": 5}`) instead of answering. Three layers: a separate
tool-free `FAST_SYSTEM_PROMPT` names no tools in fast mode; `_normalize_question`
unwraps a pasted tool-call JSON to the real query up front; and `_cleanup_answer`
+ `_looks_like_tool_call` strip stray JSON/regenerate a grounded answer if the
model slips. `_grounded_answer` is the final net with an explicit non-answer.

## Layout
```
app.py               Flask routes, CORS, static serving
agent/retriever.py   page parsing -> chunks -> BM25 index
agent/tools.py       tool specs + implementations (search/calc/web)
agent/prompts.py     system prompt: grounding, citations, clarify rules
agent/core.py        agentic loop, fallbacks, citation collection
agent/stats.py       topic-bandit suggestion ranking
static/widget.js     embeddable UI (vanilla JS, zero deps)
tests/golden_set.json  evaluation cases
scripts/run_eval.py    retrieval/full-pipeline scoring
```

## Known limits
- Keyword retrieval can miss semantic paraphrases (roadmap: hybrid embeddings).
- PDF table extraction flattens complex tables (grading table survives).
- No streaming yet; single JSON response (~2–6 s).
