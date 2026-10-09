"""Offline script to precompute dense vector embeddings for all handbook chunks.

Embeddings are saved to data/embeddings.json.
Uses Google Gemini's models/gemini-embedding-001 (dimension 256 for minimal memory & speed).
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

# Ensure root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.config import load_env
from agent.retriever import get_retriever

load_env()

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY not found in environment.")
    sys.exit(1)

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "embeddings.json")
EMBEDDING_DIM = 256
BATCH_SIZE = 50


def fetch_embeddings_batch(texts):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents"
    req_body = {
        "requests": [
            {
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": t[:2000]}]},
                "outputDimensionality": EMBEDDING_DIM,
            }
            for t in texts
        ]
    }
    data = json.dumps(req_body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": API_KEY,
        },
    )
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return [e["values"] for e in res_data.get("embeddings", [])]
        except urllib.error.HTTPError as e:
            wait_time = (attempt + 1) * 5
            print(f"  [Attempt {attempt+1}] Batch error: {e}. Waiting {wait_time}s...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"  [Attempt {attempt+1}] Batch error: {e}. Retrying in 2s...")
            time.sleep(2)
    raise RuntimeError("Failed to fetch embeddings batch after multiple attempts.")


def main():
    print("Loading chunks from retriever...")
    r = get_retriever()
    all_chunks = []
    for label, idx in r.index_by_doc.items():
        for ch in idx.chunks:
            all_chunks.append({
                "doc": ch.doc,
                "page": ch.page,
                "text": ch.text,
            })

    total = len(all_chunks)
    print(f"Total chunks to embed: {total}")

    embedded_data = []
    # If file exists, load existing progress
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                embedded_data = json.load(f)
                print(f"Resuming from {len(embedded_data)} already embedded chunks.")
        except Exception:
            embedded_data = []

    start_idx = len(embedded_data)
    for i in range(start_idx, total, BATCH_SIZE):
        batch = all_chunks[i:i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        print(f"Embedding batch {i+1} to {min(i+BATCH_SIZE, total)} / {total}...")
        vectors = fetch_embeddings_batch(texts)
        for chunk_meta, vec in zip(batch, vectors):
            embedded_data.append({
                "doc": chunk_meta["doc"],
                "page": chunk_meta["page"],
                "text": chunk_meta["text"],
                "vector": [round(v, 5) for v in vec],
            })
        # Save progress incrementally
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(embedded_data, f, separators=(",", ":"))
        time.sleep(2.5)

    print(f"Saving embeddings to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(embedded_data, f, separators=(",", ":"))

    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"Done! Saved {len(embedded_data)} embeddings ({size_mb:.2f} MB).")


if __name__ == "__main__":
    main()

