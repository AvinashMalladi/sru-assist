# AGENTS.md - conventions for AI coding tools working in this repo

## Project
SRU Assist: an agentic RAG chatbot over the SR University Student Handbook,
shipped as an embeddable portal widget. Owner team: student project team, 2026.

## Stack (do not change without team discussion)
- Python 3.12+ backend, Flask API (`app.py`), no database.
- LLM via OpenRouter using the `openai` client (`agent/llm.py`). Keys only from `.env`.
- Retrieval: pure-python BM25 over page-based chunks (`agent/retriever.py`).
  No vector DB / no torch / no langchain on purpose (portability for handover).
- Frontend: vanilla JS widget (`static/widget.js`) + mock portal (`demo/index.html`).

## Rules
- Never commit `.env`, real keys, or student personal data.
- Keep dependencies minimal; justify any new one in the PR description.
- Agent behavior lives in `agent/core.py` and `agent/prompts.py`; tools in `agent/tools.py`.
- All answers must cite handbook pages; never fabricate policy numbers.
- Run a manual check before handing off: start `python app.py`, ask
  "What is the minimum pass marks?" and verify the answer cites pages.
