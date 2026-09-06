# Connecting SRU Assist to the Portal (sraap.in)

Two integrations, both optional, both work together:

| Part | What it does | Where it lives |
|---|---|---|
| **A · Widget embed** | Puts the chat bubble into portal pages | Frontend (PHP templates) |
| **B · Content on demand** | The bot fetches the handbook **from the portal itself** — the backend does **not** need the PDF stored in the repo | Backend + one portal endpoint |

Part B is the important one for handover: after it's wired, the bot loads the Student
Handbook and regulations straight from the portal's own storage. To update the handbook,
the portal team updates *their* content — the bot picks it up automatically. **No PDF is
ever committed to the backend again.**

---

## Part A — Embed the widget in portal pages

The widget is a single dependency-free JS file. On any portal page (PHP + Bootstrap 5 +
jQuery in sraap.in), paste just before `</body>`:

```html
<script>
  window.SRU_CHAT = {
    apiUrl: "https://sru-assist.onrender.com", // deployed API host
    botName: "SRU Assist",
  };
</script>
<script src="https://sru-assist.onrender.com/static/widget.js"></script>
```

Typical placement: a shared footer include, or `student/dash_board.php` so every student
page has the bubble.

**Three CORS facts you must know**
1. The API must send `Access-Control-Allow-Origin` for the portal origin. Dev code uses
   `*`; **in production restrict it** to `https://sraap.in` in `app.py` `add_cors`.
2. Calls happen from the *student's browser* to the API host, so the API host must be
   reachable over HTTPS from public internet.
3. The widget remembers the student's profile (programme/branch/year/semester/hostel,
   captured from the bot's in-chat clarifying questions — no settings form) in
   `localStorage`; no server-side session needed.

Config keys: `apiUrl` (defaults to the widget's own origin), `botName`, `welcome`.

---

## Part B — Handbook from the portal (no bundled PDFs)

Two supported mechanisms. Use one or both.

### B1 · Portal *serves* content → bot fetches (recommended)

Make the portal expose the handbook as one of these:

| Portal endpoint format | Example | Notes |
|---|---|---|
| **JSON manifest** | `GET https://sraap.in/api/handbook` → `{ "sections": [{"page": 34, "text": "..."}] }` | Best — page numbers arrive intact, citations stay correct |
| PDF hosted on the portal | `GET https://sraap.in/api/handbook.pdf` | Downloaded, then extracted exactly like a local PDF |
| Plain text/markdown | `GET https://sraap.in/api/handbook.txt` | Split into pseudo-pages on ingest |

Then tell the backend about it — in `agent/retriever.py`, one line:

```python
DOC_SOURCES = [
    {"url": "https://sraap.in/api/handbook",   "label": "Handbook 2026-27"},  # fetched at startup
    {"file": "R23_BTECH_20240322.pdf",         "label": "R23 Handbook"},       # or keep local
]
```

On every boot the bot **fetches** the URL, caches it to `data/<slug>.txt`, builds the
BM25 index, and cites answers as `(Handbook 2026-27 p. 34)`. When the portal publishes a
new handbook, bump a version query (`?v=2027`) or clear `data/<slug>.txt` and restart.

**JSON manifest schema** (the portal team just needs to produce this shape):
```json
{
  "label": "Handbook 2026-27",
  "sections": [
    { "page": 34, "text": "A student shall be deemed to have passed..." },
    { "page": 35, "text": "Promotion rules ..." }
  ]
}
```
`text` is free-form (paragraphs, tables as pipe-separated rows). The bot splits long
pages into ≤1400-char chunks automatically.

### B2 · Portal *pushes* content → `/api/sync`

If the portal (or a CI job) wants to push content on every handbook change instead of the
bot polling, call the sync endpoint:

```
POST https://sru-assist.onrender.com/api/sync
Authorization: Bearer <SYNC_TOKEN>        # required only if SYNC_TOKEN is set in .env
Content-Type: application/json
```

**Push JSON (same manifest shape):**
```json
{
  "label": "Handbook 2026-27",
  "sections": [
    { "page": 34, "text": "..." },
    { "page": 35, "text": "..." }
  ]
}
```

**Or push a URL to fetch:** `{ "label": "Handbook 2026-27", "url": "https://sraap.in/api/handbook" }`

The backend writes the text, registers the document in `data/documents.json`, and
**rebuilds the index immediately** — no restart, no PDF stored.

Response:
```json
{ "ok": true, "label": "Handbook 2026-27", "chunks": 312, "source": "handbook_2026_27.txt" }
```

#### PHP example (drop into a portal admin script, runs after handbook edits)
```php
$payload = json_encode([
  "label" => "Handbook 2026-27",
  "sections" => $db->query("SELECT page_no, body FROM handbook_pages")->fetchAll(PDO::FETCH_ASSOC),
]);

$ch = curl_init("https://sru-assist.onrender.com/api/sync");
curl_setopt_array($ch, [
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_POST => true,
  CURLOPT_POSTFIELDS => $payload,
  CURLOPT_HTTPHEADER => [
    "Content-Type: application/json",
    "Authorization: Bearer " . getenv("SRU_SYNC_TOKEN"),
  ],
]);
echo curl_exec($ch);
```

#### curl for testing
```bash
curl -X POST https://sru-assist.onrender.com/api/sync \
  -H "Authorization: Bearer $SRU_SYNC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"label":"Handbook 2026-27","sections":[{"page":34,"text":"Pass rules ..."}]}'
```

---

## Sync lifecycle & persistence

```
 Portal handbook changes
   │
   ├─ B1 (fetch): bot restarts / clears cache  →  POST url or reload DOC_SOURCES
   │
   └─ B2 (push): portal admin script or cron   →  POST /api/sync  →  write txt
                                                    │
                                                    ▼
                                             indexes rebuilt  (rebuild())
                                                    │
                                        data/documents.json  (source registry)
                                                    │
                                   survives restarts — no code edit, no PDF
```

- The registry is `data/documents.json`. On restart the bot re-attaches every
  portal-pushed entry automatically; delete the file to forget remote sources.
- On Render free tier the disk is ephemeral — re-push (B2) or re-fetch (B1) after each
  redeploy. For persistence use a postgres-backed sync or Render persistent disk.
- Keep the source of truth on the **portal's** database; this backend is a stateless,
  disposable reader.

---

## Security checklist for production

- [ ] Set a strong `SYNC_TOKEN` and keep it out of client-side code — sync is
      server-to-server only.
- [ ] Restrict CORS in `app.py` (`add_cors`) to `https://sraap.in`.
- [ ] Validate the portal's manifest (page numbers sane, text length capped) before push.
- [ ] HTTPS everywhere; the widget and sync endpoint must never be plain HTTP.
- [ ] Rate limit `/api/chat` per student (nginx or app-level) if exposed publicly.
- [ ] Rotate the shared OpenRouter/Tavily keys before this leaves the prototype box.

---

## Decision summary

| Concern | Answer |
|---|---|
| Where does the handbook live? | **Portal database / portal URL** — backend keeps a cached text copy only |
| How does it update? | Bot fetches on boot (B1) or portal pushes on change (B2) |
| Does the backend need the PDF? | **No** — `file:` sources can be dropped entirely |
| Citations still correct? | Yes — page numbers come from the manifest/PDF markers |
| Restart-safe? | Yes — `data/documents.json` registry re-registers sources |