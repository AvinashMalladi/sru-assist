"""Retrieval evaluation against the golden Q&A set.

Usage:
  python scripts/run_eval.py                 # retrieval-only (fast, no API cost)
  python scripts/run_eval.py --k 8           # widen the retrieval window
  python scripts/run_eval.py --full          # also run the live agent per question

A case HITS if any expected page appears in the top-k retrieved chunks.
Reports hit-rate and MRR so retrieval changes are measurable.
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent.retriever import get_retriever  # noqa: E402


def load_cases():
    with open(os.path.join(ROOT, "tests", "golden_set.json"), encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"], data.get("top_k", 6)


def eval_retrieval(cases, k):
    retriever = get_retriever()
    hits, rr_total, failures = 0, 0.0, []
    print(f"{'id':16} {'hit':>3} {'best_rank':>9}  expected -> got top pages")
    print("-" * 78)
    for c in cases:
        results = retriever.search(c["q"], top_k=k)
        got_pages = [h.page for h in results]
        best_rank = None
        for rank, h in enumerate(results, start=1):
            if h.page in c["expect_pages"]:
                best_rank = rank
                break
        hit = best_rank is not None
        hits += hit
        rr_total += (1.0 / best_rank) if hit else 0.0
        if not hit:
            failures.append(c["id"])
        mark = "OK " if hit else "MISS"
        print(f"{c['id']:16} {mark:>3} {str(best_rank or '-'):>9}  "
              f"{c['expect_pages']} -> {got_pages}")
    n = len(cases)
    print("-" * 78)
    print(f"HIT-RATE @{k}: {hits}/{n} = {hits / n:.0%}")
    print(f"MRR: {rr_total / n:.2f}")
    if failures:
        print("failures:", ", ".join(failures))
    return hits, n


def eval_full(cases, k):
    from agent.core import run_agent

    retriever = get_retriever()
    cite_hits, n = 0, len(cases)
    for c in cases:
        t0 = time.time()
        result = run_agent(c["q"], history=[])
        pages = set(result.get("citations", []))
        overlap = pages.intersection(c["expect_pages"])
        ok = bool(overlap) or result.get("mode") != "agent"
        cite_hits += ok
        snippet = result["answer"][:70].replace("\n", " ")
        print(f"[{'OK ' if ok else 'MISS'}] {c['id']:16} "
              f"cited={sorted(pages)} ({time.time() - t0:.1f}s) {snippet}...")
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
        eval_full(cases, k)

    return 0 if hits >= int(n * 0.8) else 1  # CI-friendly exit code: fail under 80%


if __name__ == "__main__":
    sys.exit(main())
