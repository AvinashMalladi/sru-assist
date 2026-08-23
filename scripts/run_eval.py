"""Retrieval evaluation against the golden Q&A set (multi-document aware).

Usage:
  python scripts/run_eval.py                 # retrieval-only (fast, no API cost)
  python scripts/run_eval.py --k 8           # widen the retrieval window
  python scripts/run_eval.py --full          # also run the live agent per question

A case HITS if an expected page of the case's document appears in the top-k
retrieved chunks. Reports hit-rate and MRR so retrieval changes are measurable.
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent.retriever import get_retriever  # noqa: E402

DEFAULT_DOC = "Handbook 2026-27"


def load_cases():
    with open(os.path.join(ROOT, "tests", "golden_set.json"), encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"], data.get("top_k", 6)


def eval_retrieval(cases, k):
    retriever = get_retriever()
    hits, rr_total, failures = 0, 0.0, []
    print(f"{'id':16} {'doc':17} {'hit':>4} {'rank':>4}  got top pages")
    print("-" * 84)
    for c in cases:
        want_doc = c.get("doc", DEFAULT_DOC)
        results = retriever.search(c["q"], top_k=k)
        best_rank = None
        for rank, h in enumerate(results, start=1):
            if h.doc == want_doc and h.page in c["expect_pages"]:
                best_rank = rank
                break
        hit = best_rank is not None
        hits += hit
        rr_total += (1.0 / best_rank) if hit else 0.0
        if not hit:
            failures.append(c["id"])
        mark = "OK" if hit else "MISS"
        got = [f"{h.doc.split()[0]}:{h.page}" for h in results]
        print(f"{c['id']:16} {want_doc:17} {mark:>4} {str(best_rank or '-'):>4}  {got}")
    n = len(cases)
    print("-" * 84)
    print(f"HIT-RATE @{k}: {hits}/{n} = {hits / n:.0%}")
    print(f"MRR: {rr_total / n:.2f}")
    if failures:
        print("failures:", ", ".join(failures))
    return hits, n


def eval_full(cases):
    from agent.core import run_agent

    cite_hits, n = 0, len(cases)
    for c in cases:
        t0 = time.time()
        result = run_agent(c["q"], history=[])
        cites = result.get("citations", [])
        want_doc = c.get("doc", DEFAULT_DOC)
        ok = any(
            cite.startswith(want_doc) and int(cite.rsplit("p.", 1)[1]) in c["expect_pages"]
            for cite in cites
            if "p." in cite
        )
        cite_hits += ok
        snippet = result["answer"][:70].replace("\n", " ")
        print(f"[{'OK ' if ok else 'MISS'}] {c['id']:16} "
              f"cited={cites} ({time.time() - t0:.1f}s) {snippet}...")
    print(f"\nFULL-PIPELINE HIT-RATE: {cite_hits}/{n} = {cite_hits / n:.0%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=None)
    ap.add_argument("--full", action="store_true", help="also test live LLM answers")
    args = ap.parse_args()

    cases, default_k = load_cases()
    k = args.k or default_k
    print(f"Evaluating {len(cases)} cases @ top_k={k}\n")

    hits, n = eval_retrieval(cases, k)
    if args.full:
        print("\n--- full pipeline (live LLM) ---")
        eval_full(cases)

    return 0 if hits >= int(n * 0.8) else 1  # CI-friendly exit code: fail under 80%


if __name__ == "__main__":
    sys.exit(main())
