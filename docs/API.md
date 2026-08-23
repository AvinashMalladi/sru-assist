# SRU Assist — API Contract (v1)

Base URL: `http://localhost:5000` (dev) · `https://sru-assist.onrender.com` (deployed)

The API is **stateless**: send conversation history from the client; the server
keeps no user sessions. Any stack (PHP, Node, Java…) can integrate by calling
these two endpoints.

---

## POST /api/chat

Ask a question. Returns a grounded answer with handbook citations.

### Request
```json
{
  "message": "What is the minimum pass percentage?",
  "history": [
    { "role": "user", "content": "previous question" },
    { "role": "assistant", "content": "previous answer" }
  ],
  "profile": {
    "programme": "B.Tech",
    "branch": "CSE (AI & ML)",
    "year": "2",
    "semester": "4"
  }
}
```

| Field | Type | Rules |
|---|---|---|
| `message` | string | required, 1–1000 chars |
| `history` | array | optional, last 10 messages kept; roles `user`/`assistant` only |
| `profile` | object | optional; keys `programme`, `branch`, `year`, `semester`; each ≤40 chars |

### Response `200`
```json
{
  "answer": "…markdown text with (Handbook p. X) citations…",
  "citations": [26, 30, 31],
  "tool_calls": [
    { "tool": "search_handbook", "args": { "query": "pass marks", "top_k": 3 } }
  ],
  "mode": "agent"
}
```

| Field | Meaning |
|---|---|
| `answer` | Markdown: paragraphs, `- ` bullets, pipe tables, `**bold**`. No LaTeX. |
| `citations` | Sorted handbook page numbers actually grounding the answer |
| `tool_calls` | Tools the agent invoked this turn (for transparency/debug UIs) |
| `mode` | `agent` (model used tools) · `rag-fallback` (grounded direct answer) · `error` |

Behavior notes:
- If the question's rule differs by programme/year and `profile` lacks it, the
  agent replies with exactly ONE clarifying question instead of guessing.
- Questions outside university scope are politely refused.
- Server errors still return HTTP 200 with `mode:"error"` and a safe message.

### Errors
| Status | Body |
|---|---|
| 400 | `{"error": "message is required"}` or `"message too long"` |

## GET /api/suggestions
```json
{ "suggestions": ["What are the promotion rules?", "..."] }
```
Most-searched student questions first (persisted in `data/query_stats.json`),
padded with curated defaults. Powers the widget chips.

## GET /api/health
```json
{ "status": "ok", "model": "<model id>" }
```

## Widget embed (any portal page)
```html
<script>window.SRU_CHAT = { apiUrl: "https://sru-assist.onrender.com" };</script>
<script src="https://sru-assist.onrender.com/static/widget.js"></script>
```
Config keys: `apiUrl`, `botName`, `welcome`. The widget renders markdown,
shows citation chips, asks profile via ⚙️, and shows one-tap options when the
agent asks a clarifying question.
