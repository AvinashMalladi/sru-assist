# Productionization Guide

For the team moving SRU Assist from free-tier prototype to university
infrastructure. The code is intentionally small; this page lists every change
worth making, in order.

## 1. Model choice (the only *required* change)
The LLM layer is OpenAI-compatible via env vars — no code edits needed:

| Provider | OPENROUTER_BASE_URL | MODEL_NAME | Notes |
|---|---|---|---|
| OpenRouter (current) | `https://openrouter.ai/api/v1` | any OpenRouter id | free tier rate-limits |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` etc. | paid, tool-calling solid |
| Azure OpenAI | Azure endpoint + key | deployment name | enterprise standard |
| Local (Ollama/vLLM) | `http://llm-host:11434/v1` | e.g. `llama3.1:8b` | data stays on campus |

After switching, run `python scripts/run_eval.py --full` and compare hit-rate
against the baseline in `tests/golden_set.json`. Numbers decide the model.

## 2. Hosting on university servers
- `pip install -r requirements.txt`, then:
  `gunicorn app:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:8000`
- Put nginx/Apache in front for TLS; proxy `/` and `/static/`.
- Or keep Render/Railway if a public URL is acceptable.
- Set real env vars (never commit `.env`). Restrict CORS in `app.py`
  (`add_cors`) to the portal origin, e.g. `https://sraap.in`.

## 3. Persistence (replace JSON files)
- Conversations/analytics → Postgres (`psycopg` or SQLAlchemy). Tables:
  `messages(id, ts, question, answer, mode, citations jsonb)`,
  `feedback(id, message_id, rating, comment)`,
  `query_stats(query_hash, count, last_seen)`.
- Keep `agent/stats.py`'s function signatures; swap the storage inside.

## 4. Reliability & cost controls
- Rate-limit per student (e.g. 10 req/min) at nginx or app level.
- Cache identical normalized questions (Redis) — campus FAQs repeat heavily.
- Budget guard: log tokens per request; alert when daily spend crosses limit.

## 5. Security checklist
- [ ] Prompt-injection review: retrieved handbook text is data; keep it that
      way if you edit prompts (`agent/prompts.py`).
- [ ] Sanitize/escape widget rendering is already done client-side; keep the
      markdown renderer's escape-first order if modified.
- [ ] No student PII in logs; strip profile fields from access logs.
- [ ] Secrets via vault/env only; rotate the OpenRouter/Tavily keys shared
      during the prototype.

## 6. Knowledge updates (semester ritual)
```bash
# drop new PDF(s) into data/, then:
python scripts/extract_handbook.py data/new_doc.pdf   # extend to loop all PDFs
python scripts/run_eval.py        # must stay >= 80% before deploy
```
Roadmap: make ingestion a folder loop with per-document labels so multiple
regulations coexist; filter chunks by the student's admission batch.

## 7. Quality gates (adopt these)
- CI runs `run_eval.py` on every PR; block merges under 80% retrieval hit-rate.
- Track MRR trend after each model/prompt change.
- Review 👎 feedback weekly; turn recurring failures into new golden cases.

## 8. Nice next features (cheap wins)
- SSE streaming (`stream=True` on the OpenAI client; chunked transfer already
  enabled by gunicorn+nginx).
- "View sources" expander using the returned `citations` + stored chunk text.
- Multilingual intake (translate query -> English, answer -> student language).
