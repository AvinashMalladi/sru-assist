# SRU Assist — Agentic Student Handbook Chatbot

An **agentic RAG chatbot** for the SR University student portal. Students ask
questions about credits, grading, CGPA, pass marks, attendance, exams, hostel,
fees, and policies — the bot answers from the **official Student Handbook PDF**,
with page citations, and can fall back to web search when needed.

Built as a self-contained project: zip this folder and it works anywhere.

---

## Quick start (2 minutes)

```bash
cd sru-chatbot
pip install -r requirements.txt

# one-time: create .env (see .env.example) with your OPENROUTER_API_KEY
python app.py
```

Open **http://localhost:5000** → mock student portal loads → click the 💬 bubble.

---

## What it does (architecture)

```
 Student question
        │
        ▼
 ┌─────────────────┐     1. Auto-retrieve top handbook chunks (pure-python BM25)
 │  agent/core.py  │     2. LLM (OpenRouter) may call tools:
 └─────────────────┘        • search_handbook(query)  – more retrieval
        │                   • calculator(expr)       – CGPA / percentage math
        ▼                   • search_web(query)        – Tavily fallback
   Grounded answer          3. Final answer cites "(Handbook p. X)"
   + citations
```

| File | Purpose |
|---|---|
| `app.py` | Flask API (`POST /api/chat`, `GET /api/health`) + serves demo |
| `agent/core.py` | Agentic loop: auto-RAG + tool calling + safety fallbacks |
| `agent/retriever.py` | Page-based chunking + BM25 ranking (zero heavy deps) |
| `agent/tools.py` | Tool definitions & implementations |
| `agent/prompts.py` | System prompt (grounding + citation rules) |
| `static/widget.js` | Embeddable chat widget (one `<script>` tag) |
| `demo/index.html` | Mock portal page for demos/screenshots |
| `data/student_handbook.pdf` | Source document (86 pages) |
| `scripts/extract_handbook.py` | Rebuilds `data/handbook_text.txt` from the PDF |

### Why not a vector database?
BM25 over ~300 chunks is fast, deterministic, needs no model download, and is
trivial to swap later. `retriever.py` exposes a single `.search()` interface so
a mentor can drop in FAISS/Chroma embeddings without touching anything else.

---

## Integrating into the real portal (handover notes)

The widget is dependency-free JS. On any portal page:

```html
<script>
  window.SRU_CHAT = {
    apiUrl: "https://chatbot.yourdomain.com", // where app.py is hosted
    botName: "SRU Assist",
  };
</script>
<script src="https://chatbot.yourdomain.com/static/widget.js"></script>
```

### Real portal notes (sraap.in)
- The live portal (`sraap.in`) is server-rendered **PHP + Bootstrap 5 + jQuery**.
  Integration = paste the two tags above into the dashboard template
  (e.g. `student/dash_board.php`, or a shared footer include) just before `</body>`.
- Brand palette matched from `assets/css/style.css`: primary **#23468A**, light
  accents #97B9E2 / #dbe7f7 — widget + demo already use these.
- The public pages disable right-click/devtools via inline JS; this does not
  affect the widget.
- The API host must be reachable from students' browsers over HTTPS; keep
  `add_cors` in `app.py` restricted to `https://sraap.in` in production.

Checklist for production:
- [ ] Host `app.py` behind HTTPS (e.g. gunicorn + nginx, or Render/Railway).
- [ ] Restrict CORS in `app.py` (`add_cors`) to the real portal domain.
- [ ] Add rate limiting / auth if exposed publicly.
- [ ] Replace free OpenRouter model with a production-grade model id in `.env`.
- [ ] Optional: log Q&A pairs to improve the FAQ later.

---

## Configuration (`.env`)

See `.env.example`. Key options: `OPENROUTER_API_KEY` (required),
`MODEL_NAME`, `TAVILY_API_KEY` (optional web fallback), `ENABLE_WEB_SEARCH=false`
to force handbook-only answers.

---

## Deploying (Render free tier)

Code is deploy-ready (`render.yaml`, `gunicorn`, `$PORT` support included).

1. **Push to GitHub**
   ```bash
   cd sru-chatbot
   git remote add origin https://github.com/<your-username>/sru-assist.git
   git push -u origin master
   ```
2. **Render** → sign in with GitHub → **New + → Blueprint** → select the repo.
   Render reads `render.yaml` automatically.
3. When prompted, fill the secret values: `OPENROUTER_API_KEY`, `MODEL_NAME`,
   `TAVILY_API_KEY` (paste from your local `.env`).
4. Deploy → live at `https://sru-assist-xxxx.onrender.com` with valid HTTPS.
5. Point the widget there on any page:
   `window.SRU_CHAT = { apiUrl: "https://sru-assist-xxxx.onrender.com" };`

Free-tier notes: sleeps after ~15 min idle (first request then takes ~40 s);
`data/query_stats.json` resets on redeploys (ephemeral disk).

---

## Team workflow

- Git repo per folder; use branches + pull requests.
- AI tools: read `AGENTS.md` first (stack rules live there).
- Never commit `.env`.

## Known limitations / roadmap

- BM25 is keyword-based; semantic paraphrases may miss. Roadmap: hybrid
  BM25 + embeddings.
- Answers depend on PDF text extraction quality (tables can flatten).
- No streaming yet; responses arrive as one JSON message (~2–6 s).
