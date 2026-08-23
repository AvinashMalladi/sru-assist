"""Multi-document chunking + BM25 retrieval over SRU handbook PDFs.

Drop any PDF into data/ and register it in DOC_SOURCES (label + filename).
Text is auto-extracted on first load; chunks carry their document label so
answers can cite "(R23 Handbook p. 57)" vs "(Handbook 2026-27 p. 34)".
"""
import math
import os
import re
from collections import Counter
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

PAGE_RE = re.compile(r"===== PAGE (\d+) =====")
TOKEN_RE = re.compile(r"[a-z0-9]+")
MAX_CHUNK_CHARS = 1400

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "for", "on",
    "and", "or", "with", "as", "by", "at", "from", "that", "this", "be", "it",
    "will", "shall", "can", "what", "how", "when", "which", "who", "do", "does",
    "i", "my", "me", "you", "your", "we", "us", "if", "not", "no", "yes",
}

# Register documents here: pdf file in data/ -> citation label.
DOC_SOURCES = [
    {"file": "student_handbook.pdf", "label": "Handbook 2026-27"},
    {"file": "R23_BTECH_20240322.pdf", "label": "R23 Handbook"},
]


@dataclass
class Chunk:
    text: str
    page: int
    doc: str
    tokens: list


def tokenize(text):
    return [_stem(t) for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def _stem(token):
    """Cheap suffix stripper so 'pass'~'passing', 'mark'~'marks'."""
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _slug(name):
    base = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_").lower()[:40]


def extract_pdf(pdf_path):
    """PDF -> data/<slug>.txt with page markers. Returns txt path."""
    from pypdf import PdfReader

    out = os.path.join(DATA, f"{_slug(pdf_path)}.txt")
    reader = PdfReader(pdf_path)
    parts = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
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


def split_page(text, page_no, doc_label):
    """Split one page into <= MAX_CHUNK_CHARS chunks at paragraph boundaries."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    raw_chunks, buf = [], ""
    for para in paragraphs:
        if buf and len(buf) + len(para) + 2 > MAX_CHUNK_CHARS:
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
            pdf = os.path.join(DATA, src["file"])
            txt = os.path.join(DATA, f"{_slug(src['file'])}.txt")
            if not os.path.exists(txt):
                print(f"* extracting {src['file']} ...")
                txt = extract_pdf(pdf)
            doc_chunks = []
            for page_no, text in load_pages(txt):
                doc_chunks.extend(split_page(text, page_no, src["label"]))
            self.chunks.extend(doc_chunks)
            loaded.append(src["label"])
        self.labels = loaded
        self.default_label = loaded[0]
        # Per-document sub-indexes so each regulation gets fair representation.
        self.index_by_doc = {}
        for src in sources:
            label = src["label"]
            sub = [c for c in self.chunks if c.doc == label]
            self.index_by_doc[label] = BM25(sub)
        self.index = BM25(self.chunks)

    def _doc_hints(self, query):
        """Which regulations does the query name explicitly? Empty = none."""
        q = query.lower()
        hinted = []
        for label in self.labels:
            tokens = [t.lower() for t in re.findall(r"[a-zA-Z0-9]+", label)]
            ids = [t for t in tokens if re.fullmatch(r"[a-z]\d{2}|\d{4}", t)] or [
                t for t in tokens if len(t) >= 4
            ]
            if any(re.search(r"\b" + re.escape(t) + r"\b", q) for t in ids):
                hinted.append(label)
        if not hinted and re.search(r"\b(old|previous|earlier|last year)\b", q):
            older = next((l for l in self.labels if l != self.default_label), None)
            if older:
                hinted.append(older)
        return hinted

    def search(self, query, top_k=6):
        """Intent-aware routing:
        - no named regulation -> search the current handbook (proven baseline)
        - one named -> search that regulation alone
        - several named (comparison) -> even split across them
        """
        hinted = self._doc_hints(query)
        if not hinted:
            return self.index_by_doc[self.default_label].search(query, top_k)

        if len(hinted) == 1:
            return self.index_by_doc[hinted[0]].search(query, top_k)

        per_doc = math.ceil(top_k / len(hinted))
        out = []
        for label in hinted:
            out.extend(self.index_by_doc[label].search(query, per_doc))
        return out[:top_k]

    def format_hits(self, query, top_k=6):
        hits = self.search(query, top_k)
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
