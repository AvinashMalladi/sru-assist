"""AURA Enterprise RAG Evaluation Benchmark.

Evaluates AURA against a curated Golden Dataset of 25 Ground Truth questions
extracted directly from official SR University handbooks (R23 & 2026-27).

Metrics Computed:
1. Citation Precision (% of responses containing expected handbook page citations)
2. Factual Accuracy (% of ground-truth mandatory policy figures present)
3. Zero-Hallucination Rate (% of responses free from fabricated numbers / obsolete names)
4. Latency Breakdown (Mean, Median, P90 for Retrieval and Total Response Time)
"""
import json
import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core import run_agent

DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "golden_eval_dataset.json")
RESULTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "golden_eval_results.json")


def run_benchmark():
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset not found at {DATASET_PATH}")
        return

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} Ground-Truth Test Cases from {DATASET_PATH}\n")
    print(f"{'ID':<10} {'Category':<15} {'Cite OK?':<10} {'Facts OK?':<10} {'No-Halluc?':<12} {'Latency (ms)':<14}")
    print("-" * 75)

    results = []
    latencies = []
    citation_hits = 0
    fact_hits = 0
    hallucination_free = 0

    for tc in dataset:
        qid = tc["id"]
        cat = tc["category"]
        q = tc["question"]
        prof = tc.get("profile", {})
        expected_cites = tc.get("expected_citations", [])
        required_facts = tc.get("required_facts", [])
        prohibited = tc.get("prohibited_terms", [])

        t0 = time.perf_counter()
        res = run_agent(q, history=[], profile=prof)
        total_ms = round((time.perf_counter() - t0) * 1000, 2)
        latencies.append(total_ms)

        ans = res.get("answer", "")
        cites = res.get("citations", [])
        cites_str = " ".join(cites) + " " + ans

        # 1. Citation Precision Check
        cite_ok = any(any(exp.lower() in c.lower() for c in cites) or exp.lower() in ans.lower() for exp in expected_cites)
        if cite_ok or not expected_cites:
            citation_hits += 1

        # 2. Factual Accuracy Check
        facts_ok = all(fact.lower() in ans.lower() for fact in required_facts)
        if facts_ok:
            fact_hits += 1

        # 3. Hallucination Check
        halluc_detected = any(bad.lower() in ans.lower() for bad in prohibited)
        if not halluc_detected:
            hallucination_free += 1

        print(f"{qid:<10} {cat:<15} {'PASS' if cite_ok else 'FAIL':<10} {'PASS' if facts_ok else 'FAIL':<10} {'PASS' if not halluc_detected else 'FAIL':<12} {total_ms:<14}", flush=True)

        results.append({
            "id": qid,
            "category": cat,
            "question": q,
            "citation_pass": cite_ok,
            "facts_pass": facts_ok,
            "hallucination_free": not halluc_detected,
            "latency_ms": total_ms,
            "retrieval_ms": res.get("retrieval_ms", 0.0),
            "citations": cites,
            "answer_preview": ans[:120] + "..." if len(ans) > 120 else ans
        })

    # Summary Statistics
    n = len(dataset)
    latencies.sort()
    median_lat = latencies[n // 2]
    mean_lat = round(sum(latencies) / n, 2)
    p90_lat = latencies[int(n * 0.90)]

    cite_pct = round((citation_hits / n) * 100, 1)
    fact_pct = round((fact_hits / n) * 100, 1)
    halluc_free_pct = round((hallucination_free / n) * 100, 1)

    print("\n" + "=" * 75)
    print("AURA EMPIRICAL BENCHMARK EVALUATION SUMMARY")
    print("=" * 75)
    print(f"Total Test Cases Evaluated : {n}")
    print(f"Citation Precision Rate     : {cite_pct}% ({citation_hits}/{n})")
    print(f"Factual Accuracy Rate      : {fact_pct}% ({fact_hits}/{n})")
    print(f"Zero-Hallucination Rate    : {halluc_free_pct}% ({hallucination_free}/{n})")
    print(f"Mean Total Latency         : {mean_lat} ms")
    print(f"Median Total Latency       : {median_lat} ms")
    print(f"P90 Tail Latency           : {p90_lat} ms")
    print("=" * 75 + "\n")

    summary_data = {
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_evaluated": n,
        "citation_precision_pct": cite_pct,
        "factual_accuracy_pct": fact_pct,
        "zero_hallucination_rate_pct": halluc_free_pct,
        "latency_metrics": {
            "mean_ms": mean_lat,
            "median_ms": median_lat,
            "p90_ms": p90_lat
        },
        "detailed_results": results
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"Detailed benchmark results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    run_benchmark()
