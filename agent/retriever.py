"""Multi-document chunking + BM25 retrieval over SRU handbook PDFs.

Drop any PDF into data/ and register it in DOC_SOURCES (label + filename).
Text is auto-extracted on first load; chunks carry their document label so
answers can cite "(R23 Handbook p. 57)" vs "(Handbook 2026-27 p. 34)".
"""
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SYNC_REGISTRY = os.path.join(DATA, "documents.json")

PAGE_RE = re.compile(r"===== PAGE (\d+) =====")
TOKEN_RE = re.compile(r"[a-z0-9]+")
MAX_CHUNK_CHARS = 1400
CONTACT_TARGET_CHARS = 400
EMAIL_RE = re.compile(r"[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]{2,}", re.I)
MOBILE_RE = re.compile(r"\b\d{10}\b")


def _contact_table(para):
    """A paragraph that is really a contact directory: it contains both an email
    address and a 10-digit mobile number, i.e. rows like 'Service -> Person ->
    phone -> email'. We split these into small row groups so a query for one
    service (e.g. 'wifi', 'scholarship', 'transport') hits ITS row instead of a
    1500-char dump of every contact on the page."""
    return EMAIL_RE.search(para) is not None and MOBILE_RE.search(para) is not None


def _split_contact_rows(para):
    """Yield small line-group chunks so a single contact entry (3-4 lines) is not
    drowned by ~20 entries sharing 'sru.edu.in' / 'Block-I' noise."""
    chunks, buf = [], ""
    for ln in para.splitlines():
        if buf and len(buf) + len(ln) + 1 > CONTACT_TARGET_CHARS:
            chunks.append(buf)
            buf = ln
        else:
            buf = f"{buf}\n{ln}" if buf else ln
    if buf:
        chunks.append(buf)
    return chunks

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "for", "on",
    "and", "or", "with", "as", "by", "at", "from", "that", "this", "be", "it",
    "will", "shall", "can", "what", "how", "when", "which", "who", "do", "does",
    "i", "my", "me", "you", "your", "we", "us", "if", "not", "no", "yes",
}

# Register documents here: pdf file in data/ -> citation label.
# A source may use "file" (local PDF), "url" (portal-hosted PDF/JSON/text), or
# "txt" (content pushed via POST /api/sync, no PDF stored).
DOC_SOURCES = [
    {"file": "student_handbook.pdf", "label": "Handbook 2026-27"},
    {"file": "R23_BTECH_20240322.pdf", "label": "R23 Handbook"},
]


def add_source(entry):
    """Register a source (label-unique) and persist it to data/documents.json.

    Portal-pushed ("txt") and portal-fetched ("url") sources survive restarts
    without any PDF living in the repo.
    """
    for i, s in enumerate(DOC_SOURCES):
        if s.get("label") == entry.get("label"):
            DOC_SOURCES[i] = entry
            break
    else:
        DOC_SOURCES.append(entry)
    os.makedirs(DATA, exist_ok=True)
    with open(SYNC_REGISTRY, "w", encoding="utf-8") as f:
        json.dump(DOC_SOURCES, f, indent=1)
    return DOC_SOURCES


def _merge_sync_registry():
    """On import, re-attach sources persisted via /api/sync so portal-pushed
    content stays loaded across restarts (no code edits, no PDFs)."""
    try:
        with open(SYNC_REGISTRY, encoding="utf-8") as f:
            remote = json.load(f)
    except Exception:  # noqa: BLE001 - missing/corrupt registry -> code list wins
        return
    for entry in remote:
        if isinstance(entry, dict) and entry.get("label"):
            for i, s in enumerate(DOC_SOURCES):
                if s.get("label") == entry["label"]:
                    DOC_SOURCES[i] = entry
                    break
            else:
                DOC_SOURCES.append(entry)


_merge_sync_registry()


@dataclass
class Chunk:
    text: str
    page: int
    doc: str
    tokens: list


def tokenize(text):
    """Stemmed tokens; hyphenated words are emitted in BOTH their split and
    hyphenless forms so 'wifi' matches 'Wi-Fi', 're-evaluation' matches
    'reevaluation', 'non-credit' matches 'noncredit', and so on — the whole
    class of hyphen/compound misses, not just known pairs."""
    tokens = []
    for unit in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower()):
        parts = [t for t in unit.split("-") if t not in STOPWORDS]
        stems = [_stem(t) for t in parts]
        tokens.extend(stems)
        if len(parts) == 2:
            joined = _stem(parts[0] + parts[1])
            if joined not in tokens:
                tokens.append(joined)
    return tokens


def _stem(token):
    """Cheap suffix stripper so 'pass'~'passing', 'mark'~'marks'."""
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


TYPO_CORRECTIONS = [
    (re.compile(r"\bmis[- ]?exam\b", re.I), "mid exam"),
    (re.compile(r"\bmidsem\b", re.I), "mid semester"),
    (re.compile(r"\bmid-sem\b", re.I), "mid semester"),
    (re.compile(r"\battendence\b", re.I), "attendance"),
    (re.compile(r"\bhostle\b", re.I), "hostel"),
    (re.compile(r"\breval\b", re.I), "revaluation"),
    (re.compile(r"\breeval\b", re.I), "revaluation"),
    (re.compile(r"\breevaluation\b", re.I), "re-evaluation"),
    (re.compile(r"\bsuplementary\b", re.I), "supplementary"),
    (re.compile(r"\bsuplimentary\b", re.I), "supplementary"),
    (re.compile(r"\binvigilater\b", re.I), "invigilator"),
    (re.compile(r"\bmalpractise\b", re.I), "malpractice"),
    (re.compile(r"\braging\b", re.I), "ragging"),
    (re.compile(r"\bhall[- ]?ticket\b", re.I), "admit card examination hall ticket"),
    (re.compile(r"\bhallticket\b", re.I), "admit card examination hall ticket"),
    (re.compile(r"\bdabbulu\b", re.I), "fee payment refund"),
    (re.compile(r"\bentha\b", re.I), "how much minimum"),
    (re.compile(r"\bfail ayya\b", re.I), "failed course backlog F grade"),
    (re.compile(r"\bfail ayanu\b", re.I), "failed course backlog F grade"),
]

# Query-side expansion for high-value synonyms. Retrieved content is untouched,
# so this cannot disturb indexing statistics or the golden-set baseline. It only
# widens the query string (and phrase-candidates) before BM25 + rerank.
QUERY_EXPANSIONS = {
    # Malpractice / cheating / unfair means / slips
    "slip": "slip slips unfair means malpractice invigilator CPAM seize evidence",
    "slips": "slips unfair means malpractice invigilator CPAM seize answer script",
    "chit": "chits slips unfair means malpractice invigilator CPAM",
    "chits": "chits slips unfair means malpractice invigilator CPAM",
    "cheating": "cheating unfair means malpractice invigilator CPAM misconduct",
    "cheat": "cheating unfair means malpractice invigilator CPAM",
    "copying": "copying unfair means malpractice invigilator CPAM",
    "invigilator": "invigilator seize answer script unfair means CPAM statement evidence",
    "malpractice": "malpractice unfair means CPAM invigilator disciplinary action",
    "unfair means": "unfair means malpractice CPAM invigilator seize answer script",
    "caught": "caught invigilator seize answer script unfair means malpractice",

    # Wi-Fi / connectivity
    "wifi": "wifi wi-fi wireless network",
    "wi-fi": "wifi wi-fi wireless network",
    "wireless": "wifi wi-fi wireless network",
    "internet": "internet wifi broadband network",
    "network": "wifi network internet",
    "not working": "not working issue problem down disconnected",
    "not connecting": "not working issue problem connecting",
    "contact": "contact reach report help desk helpline number",
    "issue": "issue problem complaint help",
    "problem": "problem issue complaint help",
    "complaint": "complaint issue problem help",

    # Backlogs / Supplementary / Promotion
    "backlog": "backlog supplementary F grade clearing exam",
    "arrear": "arrear backlog supplementary F grade",
    "supply": "supply supplementary exam F grade",
    "supplementary": "supplementary advance supplementary backlog F grade",
    "detained": "detained detention promotion criteria credits attendance",
    "detention": "detention detained promotion criteria credits attendance",

    # Condonation / Attendance
    "condonation": "condonation attendance shortage medical 65 75 percentage",
    "medical leave": "medical leave condonation attendance shortage certificate",

    # Re-evaluation
    "revaluation": "revaluation re-evaluation answer script verification recounting",
    "re-evaluation": "re-evaluation revaluation answer script verification",

    # Department leadership & Engineering Schools (Handbook p.54-55)
    "computer": "computer cse cs & ai socs computer science ranjith",
    "compuster": "computer cse cs & ai socs computer science ranjith",
    "cse": "cse computer science cs & ai socs ranjith",
    "civil": "civil ce soe assistant dean gaurav tyagi",
    "ce": "ce civil soe assistant dean gaurav tyagi",
    "mechanical": "mechanical me soe assistant dean vijay reddy",
    "mech": "mech mechanical me soe assistant dean vijay reddy",
    "electrical": "electrical eee soe assistant dean sathyavani",
    "eee": "eee electrical soe assistant dean sathyavani",
    "electronics": "electronics ece soe assistant dean kallepelli sagar",
    "ece": "ece electronics soe assistant dean kallepelli sagar",
    "business": "business sob management bba mba assistant dean ramesh babu",
    "sob": "sob business management bba mba assistant dean ramesh babu",
    "agriculture": "agriculture soa assistant dean pandit vaibhav bhagwan",
    "soa": "soa agriculture assistant dean pandit vaibhav bhagwan",
    "innovation": "innovation startups nest girirajan chakradhar srix",
    "startups": "startups innovation nest girirajan chakradhar",
    "alumni": "alumni madan kumar srikanth association",
    "welfare": "welfare student welfare dean sw dean.sw",
    "sports": "sports physical education srinivas goud gym",
    "ambulance": "ambulance medical driver emergency sai kumar",
    "dean": "dean assistant dean associate dean head hod contact",
    "hod": "hod head department dean assistant dean coordinator",
    "head": "head hod department dean assistant dean coordinator in-charge",
    "incharge": "incharge in-charge coordinator head dean director",
    "in-charge": "in-charge incharge coordinator head dean director",
    "director": "director associate director head dean coordinator",
    "controller": "controller examinations coe exam branch evaluation",
    "coe": "coe controller examinations exam branch",
}

REGULATION_TOPIC = re.compile(
    r"\b(promotion|promoted|detained|detention|regulations?)\b",
    re.I,
)


def expand_query(query):
    """Normalize typos and widen a query string with synonym variants before tokenization.

    Uses word boundary regex matching so short keys ('ce', 'me', 'soa') never
    accidentally trigger on substrings of normal words ('percentage', 'placement')."""
    q_norm = query or ""
    for pattern, replacement in TYPO_CORRECTIONS:
        q_norm = pattern.sub(replacement, q_norm)

    q_lower = q_norm.lower()
    parts = [q_norm]
    for key, value in QUERY_EXPANSIONS.items():
        if re.search(r"\b" + re.escape(key) + r"\b", q_lower):
            parts.append(value)
    if len(parts) == 1:
        return q_norm
    return " ".join(dict.fromkeys(parts))


def _slug(name):
    base = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_").lower()[:40]


def _slug_url(url):
    """Slug from a URL path, robust to trailing slashes/query strings."""
    path = url.split("?")[0].rstrip("/")
    base = os.path.basename(path) or "remote_doc"
    return re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_").lower()[:40]


def _repair_email_breaks(text):
    """Rejoin email addresses that the PDF text layer split across lines
    (e.g. 'g.rajeshwarreddy@sru.edu.i\\nn'). Only stitches fragments when the
    combined tail is a known TLD, so ordinary line breaks are left untouched."""
    known = {
        "in", "on", "com", "net", "org", "edu", "ac", "gov", "co",
        "uk", "io", "ai", "id", "us", "me", "info", "biz",
    }

    def fix(m):
        if m.group(2) + m.group(3) in known:
            return m.group(1) + m.group(2) + m.group(3)
        return m.group(0)

    return re.sub(
        r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.)([a-z]{1,3})\s*\n\s*([a-z]{1,3})",
        fix,
        text,
    )


def extract_pdf(pdf_path):
    """PDF -> data/<slug>.txt with page markers. Returns txt path."""
    from pypdf import PdfReader

    out = os.path.join(DATA, f"{_slug(pdf_path)}.txt")
    reader = PdfReader(pdf_path)
    parts = []
    for i, page in enumerate(reader.pages):
        text = _repair_email_breaks(page.extract_text() or "")
        if not text.strip():
            text = f"[page {i + 1} - no extractable text]"
        parts.append(f"\n\n===== PAGE {i + 1} =====\n{text}")
    with open(out, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    return out


def load_pages(txt_path):
    """Return [(page_number, text), ...] from an extracted text file."""
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f"{txt_path} not found")
    with open(txt_path, encoding="utf-8") as f:
        raw = f.read()
    pages = []
    parts = PAGE_RE.split(raw)
    for i in range(1, len(parts), 2):
        page_no = int(parts[i])
        text = parts[i + 1].strip()
        if text:
            pages.append((page_no, text))
    return pages


def sync_from_json(txt_path, label, payload):
    """Write a text file from a JSON manifest so the bot needs no PDFs.

    Accepted shapes:
      {"label": "2026 Handbook", "sections": [{"page": 5, "text": "..."}, ...]}
      {"pages": [{"page": 5, "text": "..."}, ...]}
      {"chunks":  [{"page": 5, "text": "..."}, ...]}   (same as above)
      each section may also be a plain string -> page number = index + 1
    Returns the txt path (also used by load_pages).
    """
    sections = payload.get("sections") or payload.get("pages") or payload.get("chunks") or []
    parts = []
    for i, sec in enumerate(sections, start=1):
        if isinstance(sec, str):
            page_no, text = i, sec
        elif isinstance(sec, dict):
            page_no = int(sec.get("page") or sec.get("page_no") or sec.get("n") or i)
            text = sec.get("text") or sec.get("content") or ""
        else:
            continue
        text = text.strip()
        if text:
            parts.append(f"\n\n===== PAGE {page_no} =====\n{text}")
    if not parts:
        raise ValueError("manifest has no sections/pages/chunks with text")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    return txt_path


def _write_remote_text(txt_path, text, step=100):
    """Plain text response -> labeled page chunks (page per ~step lines)."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("remote content is empty")
    parts = []
    for i in range(0, len(lines), step):
        parts.append(f"\n\n===== PAGE {i // step + 1} =====\n" + "\n".join(lines[i:i + step]))
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    return txt_path


def fetch_remote(url, label):
    """Download a handbook source from the portal instead of shipping a PDF.

    Supports three content types:
      * *.pdf          -> downloaded then extracted like a local PDF
      * *.json or JSON -> manifest sections/pages/chunks -> page-labeled text
      * anything else  -> raw text, split into page-sized blocks
    Returns the cached txt path under data/.
    """
    import requests

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    sl = url.lower()
    if sl.endswith(".pdf"):
        pdf_path = os.path.join(DATA, f"{_slug_url(url)}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(resp.content)
        return extract_pdf(pdf_path)

    slug = _slug_url(url)
    txt_path = os.path.join(DATA, f"{slug}.txt")
    ctype = resp.headers.get("content-type", "")
    if "json" in ctype or sl.endswith(".json") or (resp.text.lstrip() or " ")[:1] == "{":
        try:
            return sync_from_json(txt_path, label, resp.json())
        except ValueError:
            return _write_remote_text(txt_path, resp.text)
    return _write_remote_text(txt_path, resp.text)


def _ensure_source(src):
    """Return a local txt path for a source entry.

    Supports:
      {"file": "x.pdf",     "label": "..."}   PDF shipped in data/
      {"url":  "https://…", "label": "..."}   remote PDF / JSON manifest / text
    Local txt is cached next to the source so repeated boots skip the fetch.
    """
    if src.get("file"):
        pdf = os.path.join(DATA, src["file"])
        txt = os.path.join(DATA, f"{_slug(src['file'])}.txt")
        if not os.path.exists(txt):
            print(f"* extracting {src['file']} ...")
            txt = extract_pdf(pdf)
        return txt

    if src.get("txt"):
        # A text file written by /api/sync (portal-pushed content, no PDF).
        txt = os.path.join(DATA, src["txt"])
        if not os.path.exists(txt):
            print(f"* WARNING: sync text missing: {src['txt']}")
            return ""
        return txt

    if src.get("url"):
        txt = os.path.join(DATA, f"{_slug_url(src['url'])}.txt")
        if not os.path.exists(txt):
            print(f"* fetching {src['url']} ...")
            try:
                txt = fetch_remote(src["url"], src["label"])
            except Exception as exc:  # noqa: BLE001 - skip a dead source, keep the rest
                print(f"* WARNING: could not fetch {src['url']}: {exc}")
                return ""
        return txt

    raise ValueError(f"source needs 'file' or 'url': {src}")


def split_page(text, page_no, doc_label):
    """Split one page into <= MAX_CHUNK_CHARS chunks at paragraph boundaries.
    Contact-directory paragraphs (email + mobile) are broken into small row
    groups so any single 'service -> contact' entry stays retrievable."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    raw_chunks, buf = [], ""
    for para in paragraphs:
        if _contact_table(para):
            if buf:
                raw_chunks.append(buf)
                buf = ""
            raw_chunks.extend(_split_contact_rows(para))
        elif buf and len(buf) + len(para) + 2 > MAX_CHUNK_CHARS:
            raw_chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        raw_chunks.append(buf)

    final = []
    for c in raw_chunks:
        while len(c) > MAX_CHUNK_CHARS * 1.5:
            cut = c.rfind(" ", 0, MAX_CHUNK_CHARS)
            cut = cut if cut > 400 else MAX_CHUNK_CHARS
            final.append(c[:cut])
            c = c[cut:].strip()
        final.append(c)
    return [Chunk(text=c, page=page_no, doc=doc_label, tokens=tokenize(c)) for c in final]


class BM25:
    def __init__(self, chunks, k1=1.4, b=0.72):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.doc_lens = [len(c.tokens) or 1 for c in chunks]
        self.avgdl = sum(self.doc_lens) / len(self.doc_lens)
        self.df = Counter()
        for c in chunks:
            self.df.update(set(c.tokens))
        self.N = len(chunks)

    def search(self, query_tokens, top_k):
        q_tokens = tokenize(query_tokens) if isinstance(query_tokens, str) else query_tokens
        scores = []
        for idx, chunk in enumerate(self.chunks):
            tf = Counter(chunk.tokens)
            dl = self.doc_lens[idx]
            s = 0.0
            for t in q_tokens:
                f = tf.get(t, 0)
                if not f:
                    continue
                s += self._idf(t) * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                )
            scores.append((s, idx))
        scores.sort(reverse=True)
        return [self.chunks[i] for s, i in scores[:top_k] if s > 0]

    def _idf(self, term):
        n = self.df.get(term, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))


class MultiDocRetriever:
    def __init__(self, sources=None):
        sources = sources or DOC_SOURCES
        self.chunks = []
        loaded = []
        for src in sources:
            txt = _ensure_source(src)
            if not txt:
                continue
            doc_chunks = []
            for page_no, text in load_pages(txt):
                doc_chunks.extend(split_page(text, page_no, src["label"]))
            self.chunks.extend(doc_chunks)
            loaded.append(src["label"])
        if not self.chunks:
            raise RuntimeError("no documents loaded - check DOC_SOURCES in agent/retriever.py")
        self.labels = loaded
        self.default_label = loaded[0]
        # Per-document sub-indexes so each regulation gets fair representation.
        self.index_by_doc = {}
        for src in sources:
            label = src["label"]
            sub = [c for c in self.chunks if c.doc == label]
            self.index_by_doc[label] = BM25(sub)
        self.index = BM25(self.chunks)

    def _match_doc_label(self, text):
        t = (text or "").lower()
        if not t:
            return []
        # Explicit R23 / batch 2023-24 patterns
        if re.search(r"\b(r23|r-23|2023[-–/]?24|23[-–/]?24|2023|2024)\b", t):
            r23 = next((l for l in self.labels if "r23" in l.lower()), None)
            if r23:
                return [r23]
        # Explicit 2026-27 / R26 patterns
        if re.search(r"\b(r26|r-26|2026[-–/]?27|26[-–/]?27|2026|2027)\b", t):
            r26 = next((l for l in self.labels if "2026" in l.lower()), None)
            if r26:
                return [r26]
        # Previous/old regulation hints
        if re.search(r"\b(old|previous|earlier|last year)\b", t):
            older = next((l for l in self.labels if l != self.default_label), None)
            if older:
                return [older]
        # Label-token matching fallback
        hinted = []
        for label in self.labels:
            tokens = [tok.lower() for tok in re.findall(r"[a-zA-Z0-9]+", label)]
            ids = [tok for tok in tokens if re.fullmatch(r"[a-z]\d{2}|\d{4}", tok)] or [
                tok for tok in tokens if len(tok) >= 4
            ]
            if any(re.search(r"\b" + re.escape(tok) + r"\b", t) for tok in ids):
                hinted.append(label)
        return hinted

    def _doc_hints(self, query, history=None, profile=None):
        """Which regulations does the query / conversation context name explicitly?"""
        hinted = self._match_doc_label(query)
        if hinted:
            return hinted
        if history:
            user_texts = [
                m.get("content", "")
                for m in history
                if isinstance(m, dict) and m.get("role") == "user"
            ]
            for ut in reversed(user_texts):
                h = self._match_doc_label(ut)
                if h:
                    return h
        if isinstance(profile, dict):
            p_text = " ".join(str(v) for v in profile.values())
            h = self._match_doc_label(p_text)
            if h:
                return h
        return []

    def _phrase_rerank(self, query, pool):
        """Two-stage retrieval: BM25 provides recall; exact query-phrase matches
        provide precision. Candidates containing one of the query's adjacent
        term pairs are promoted to the front (original BM25 order preserved),
        the rest backfill behind them. Handles hyphen/space variants
        ('non-credit' vs 'noncredit') via a squashed comparison string."""
        q_tokens = [t for t in tokenize(query) if len(t) > 2]
        phrases = list(dict.fromkeys(zip(q_tokens, q_tokens[1:])))
        if not phrases:
            return pool

        def has_phrase(chunk):
            t = " " + re.sub(r"[\s\-]+", " ", chunk.text.lower()) + " "
            compact = t.replace(" ", "")
            return any(
                f" {a} {b} " in t or f"{a}{b}" in compact for a, b in phrases
            )

        hits = [c for c in pool if has_phrase(c)]
        if not hits:
            return pool
        hit_ids = {id(c) for c in hits}
        return hits + [c for c in pool if id(c) not in hit_ids]

    def search(self, query, top_k=6, history=None, profile=None):
        """Intent-aware routing:
        - named regulation (in query, history or profile) -> search that regulation
        - unhinted regulation-sensitive query -> retrieve from BOTH handbooks so AI has both
        - general campus queries -> search default handbook (Handbook 2026-27)
        Results are re-ranked by exact-phrase matches.
        """
        hinted = self._doc_hints(query, history=history, profile=profile)
        if not hinted:
            if REGULATION_TOPIC.search(query):
                labels = list(self.labels)
            else:
                labels = [self.default_label]
        elif len(hinted) == 1:
            labels = hinted
        else:
            labels = hinted

        expanded = expand_query(query)
        pools = {}
        for label in labels:
            raw = self.index_by_doc[label].search(expanded, max(top_k * 6, 30))
            pools[label] = self._phrase_rerank(query, raw)

        out, seen = [], set()
        # keep the intended doc balance: round-robin in label order
        while len(out) < top_k and any(pools.values()):
            for label in labels:
                lst = pools.get(label) or []
                if lst and len(out) < top_k:
                    nxt = lst.pop(0)
                    if id(nxt) not in seen:
                        out.append(nxt)
                        seen.add(id(nxt))
        return out

    def format_hits(self, query, top_k=6, history=None, profile=None):
        hits = self.search(query, top_k=top_k, history=history, profile=profile)
        if not hits:
            return "No relevant handbook sections found.", []
        blocks, cites = [], []
        for h in hits:
            blocks.append(f"[{h.doc} · page {h.page}]\n{h.text}")
            cites.append(f"{h.doc} p.{h.page}")
        return "\n\n---\n\n".join(blocks), cites


_retriever = None


def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = MultiDocRetriever()
    return _retriever


def rebuild():
    """Drop cached index so new/updated sources are re-ingested on next call.

    Used by /api/sync after the portal pushes refreshed handbook content.
    """
    global _retriever
    _retriever = None
    return get_retriever()
