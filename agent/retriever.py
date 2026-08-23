"""Chunking + BM25 retrieval over the SR University Student Handbook.

Zero external dependencies: chunks are built from data/handbook_text.txt
(page markers produced by scripts/extract_handbook.py) and ranked with a
pure-python BM25 implementation.
"""
import math
import os
import re
from collections import Counter
from dataclasses import dataclass

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "handbook_text.txt")

PAGE_RE = re.compile(r"===== PAGE (\d+) =====")
TOKEN_RE = re.compile(r"[a-z0-9]+")
MAX_CHUNK_CHARS = 1400

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "for", "on",
    "and", "or", "with", "as", "by", "at", "from", "that", "this", "be", "it",
    "will", "shall", "can", "what", "how", "when", "which", "who", "do", "does",
    "i", "my", "me", "you", "your", "we", "us", "if", "not", "no", "yes",
}


@dataclass
class Chunk:
    text: str
    page: int
    tokens: list


def _stem(token):
    """Cheap suffix stripper so 'pass'~'passing', 'mark'~'marks'."""
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text):
    return [_stem(t) for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def load_pages(path=DATA_FILE):
    """Return [(page_number, text), ...] from the extracted handbook."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run scripts/extract_handbook.py first."
        )
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    pages = []
    parts = PAGE_RE.split(raw)
    for i in range(1, len(parts), 2):
        page_no = int(parts[i])
        text = parts[i + 1].strip()
        if text:
            pages.append((page_no, text))
    return pages


def split_page(text, page_no):
    """Split one page into <= MAX_CHUNK_CHARS chunks at paragraph boundaries."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], ""
    for para in paragraphs:
        if buf and len(buf) + len(para) + 2 > MAX_CHUNK_CHARS:
            chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        chunks.append(buf)
    # A single monster paragraph still larger than the cap: hard-split it.
    final = []
    for c in chunks:
        while len(c) > MAX_CHUNK_CHARS * 1.5:
            cut = c.rfind(" ", 0, MAX_CHUNK_CHARS)
            cut = cut if cut > 400 else MAX_CHUNK_CHARS
            final.append(c[:cut])
            c = c[cut:].strip()
        final.append(c)
    return [Chunk(text=c, page=page_no, tokens=tokenize(c)) for c in final]


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

    def _idf(self, term):
        n = self.df.get(term, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def search(self, query, top_k=6):
        q_tokens = tokenize(query)
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
        hits = [self.chunks[i] for s, i in scores[:top_k] if s > 0]
        return hits


class HandbookRetriever:
    def __init__(self, path=DATA_FILE):
        pages = load_pages(path)
        self.chunks = []
        for page_no, text in pages:
            self.chunks.extend(split_page(text, page_no))
        self.index = BM25(self.chunks)

    def search(self, query, top_k=6):
        return self.index.search(query, top_k)

    def format_hits(self, query, top_k=6):
        hits = self.search(query, top_k)
        if not hits:
            return "No relevant handbook sections found.", []
        blocks, cites = [], []
        for h in hits:
            blocks.append(f"[Handbook page {h.page}]\n{h.text}")
            cites.append(f"p.{h.page}")
        return "\n\n---\n\n".join(blocks), cites


_retriever = None


def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HandbookRetriever()
    return _retriever
