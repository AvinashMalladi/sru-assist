"""AURA Performance Benchmark Suite.

Executes representative question sets against the AURA API, measures query latency
using time.perf_counter(), calculates statistical percentiles (P50, P90, P95, P99),
and exports comprehensive reports to console, CSV, and JSON.

Usage:
  # Against running local server (default: http://127.0.0.1:5000)
  python scripts/benchmark.py --iterations 2 --timeout 30

  # Against custom URL
  python scripts/benchmark.py --url http://localhost:5000 --dataset tests/golden_set.json

  # Direct in-process execution (no server required)
  python scripts/benchmark.py --in-process --dataset tests/golden_set.json --limit 10

  # Export custom files
  python scripts/benchmark.py --csv data/benchmark.csv --json data/benchmark.json
"""

import argparse
import csv
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agent.metrics import (
    calculate_latency_stats,
    calculate_percentile,
    format_performance_report,
)


def load_benchmark_dataset(dataset_path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load evaluation questions from JSON or CSV dataset file.

    Supports:
      - tests/golden_set.json (cases list with 'q' or 'question')
      - tests/daily_100_questions.json (cases list with 'question')
      - CSV files with 'question' or 'q' column.
    """
    if not os.path.isabs(dataset_path):
        dataset_path = os.path.join(ROOT, dataset_path)

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at: {dataset_path}")

    cases = []
    if dataset_path.endswith(".json"):
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw_cases = data.get("cases", []) if isinstance(data, dict) else data
        for idx, item in enumerate(raw_cases):
            q_text = item.get("question") or item.get("q")
            if q_text and q_text.strip():
                cases.append({
                    "id": item.get("id", f"case_{idx+1}"),
                    "question": q_text.strip(),
                    "doc": item.get("doc", ""),
                    "note": item.get("note", item.get("canonical_fact", "")),
                })
    elif dataset_path.endswith(".csv"):
        with open(dataset_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                q_text = row.get("question") or row.get("q")
                if q_text and q_text.strip():
                    cases.append({
                        "id": row.get("id") or row.get("question_id", f"case_{idx+1}"),
                        "question": q_text.strip(),
                        "doc": row.get("doc", ""),
                        "note": row.get("note", ""),
                    })
    else:
        raise ValueError(f"Unsupported dataset format: {dataset_path}. Use .json or .csv")

    if limit is not None and limit > 0:
        cases = cases[:limit]

    return cases


def send_query_http(
    base_url: str,
    question: str,
    session_id: str,
    timeout: float = 30.0,
) -> Tuple[bool, int, float, Dict[str, Any], Optional[str]]:
    """Execute a single query over HTTP and measure roundtrip response time.

    Returns:
        (is_success, http_status, client_latency_ms, response_data, error_message)
    """
    import requests

    endpoint = base_url.rstrip("/") + "/api/chat"
    payload = {
        "message": question,
        "session_id": session_id,
    }

    t0 = time.perf_counter()
    try:
        resp = requests.post(endpoint, json=payload, timeout=timeout)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        status_code = resp.status_code

        if status_code == 200:
            try:
                data = resp.json()
                return True, status_code, elapsed_ms, data, None
            except Exception as e:
                return False, status_code, elapsed_ms, {}, f"Invalid JSON response: {e}"
        else:
            return False, status_code, elapsed_ms, {}, f"HTTP Error {status_code}: {resp.text[:120]}"

    except requests.exceptions.Timeout:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return False, 408, elapsed_ms, {}, f"Request timed out after {timeout}s"
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return False, 0, elapsed_ms, {}, str(exc)


def send_query_in_process(
    app_client: Any,
    question: str,
    session_id: str,
) -> Tuple[bool, int, float, Dict[str, Any], Optional[str]]:
    """Execute a single query in-process using Flask test_client."""
    payload = {
        "message": question,
        "session_id": session_id,
    }

    t0 = time.perf_counter()
    try:
        resp = app_client.post("/api/chat", json=payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        status_code = resp.status_code

        if status_code == 200:
            data = resp.get_json() or {}
            return True, status_code, elapsed_ms, data, None
        else:
            return False, status_code, elapsed_ms, {}, f"HTTP Error {status_code}"
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return False, 0, elapsed_ms, {}, str(exc)


def run_benchmark(
    dataset_path: str = "tests/golden_set.json",
    iterations: int = 1,
    base_url: str = "http://127.0.0.1:5000",
    timeout: float = 30.0,
    limit: Optional[int] = None,
    in_process: bool = False,
    quiet: bool = False,
) -> Dict[str, Any]:
    """Execute the full benchmark run and return results dictionary."""
    cases = load_benchmark_dataset(dataset_path, limit=limit)
    if not cases:
        raise ValueError(f"No test cases loaded from {dataset_path}")

    app_client = None
    if in_process:
        from app import app
        app.config["TESTING"] = True
        app_client = app.test_client()

    records = []
    successful_client_latencies = []
    successful_server_latencies = []
    retrieval_latencies = []
    llm_latencies = []
    failed_count = 0

    benchmark_run_id = f"bench_{uuid.uuid4().hex[:8]}"

    if not quiet:
        print(f"\n[AURA Benchmark] Starting Run: {benchmark_run_id}")
        print(f"Dataset: {dataset_path} ({len(cases)} questions)")
        print(f"Iterations: {iterations} | Total Target Requests: {len(cases) * iterations}")
        print(f"Mode: {'In-Process TestClient' if in_process else f'HTTP ({base_url})'} | Timeout: {timeout}s\n")
        print(f"{'#':<4} {'Iter':<5} {'ID':<20} {'Status':<8} {'Client (ms)':<12} {'Server (ms)':<12} {'Mode':<15}")
        print("-" * 80)

    request_counter = 0

    for it in range(1, iterations + 1):
        for idx, case in enumerate(cases):
            request_counter += 1
            # Unique test session ID per request to guarantee clean isolation
            session_id = f"{benchmark_run_id}_it{it}_{idx+1}"

            if in_process:
                success, http_code, client_ms, data, err = send_query_in_process(
                    app_client, case["question"], session_id
                )
            else:
                success, http_code, client_ms, data, err = send_query_http(
                    base_url, case["question"], session_id, timeout=timeout
                )

            server_ms = data.get("latency_ms") if success else None
            retrieval_ms = data.get("retrieval_ms") if success else None
            llm_ms = data.get("llm_ms") if success else None
            resp_mode = data.get("mode", "error" if not success else "normal")

            if success:
                successful_client_latencies.append(client_ms)
                if server_ms is not None:
                    successful_server_latencies.append(server_ms)
                if retrieval_ms is not None:
                    retrieval_latencies.append(retrieval_ms)
                if llm_ms is not None:
                    llm_latencies.append(llm_ms)
            else:
                failed_count += 1

            rec = {
                "request_num": request_counter,
                "iteration": it,
                "case_id": case["id"],
                "question": case["question"],
                "status": "SUCCESS" if success else "FAILED",
                "http_status": http_code,
                "client_latency_ms": round(client_ms, 2),
                "server_latency_ms": server_ms,
                "retrieval_ms": retrieval_ms,
                "llm_ms": llm_ms,
                "mode": resp_mode,
                "session_id": session_id,
                "error": err or "",
            }
            records.append(rec)

            if not quiet:
                status_str = "OK" if success else f"FAIL({http_code})"
                client_str = f"{client_ms:.1f}"
                server_str = f"{server_ms}" if server_ms is not None else "-"
                print(f"{request_counter:<4} {it:<5} {case['id'][:19]:<20} {status_str:<8} {client_str:<12} {server_str:<12} {resp_mode[:14]:<15}")

    # Compute overall performance percentiles on client-observed total latency
    client_stats = calculate_latency_stats(
        successful_client_latencies,
        total_requests=request_counter,
        failed_requests=failed_count,
    )

    # Compute server processing latency stats if recorded
    server_stats = calculate_latency_stats(
        successful_server_latencies,
        total_requests=request_counter,
        failed_requests=failed_count,
    ) if successful_server_latencies else None

    # Compute component breakdown stats (retrieval & LLM)
    retrieval_stats = calculate_latency_stats(retrieval_latencies) if retrieval_latencies else None
    llm_stats = calculate_latency_stats(llm_latencies) if llm_latencies else None

    result_payload = {
        "benchmark_run_id": benchmark_run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset": dataset_path,
        "questions_count": len(cases),
        "iterations": iterations,
        "total_requests": request_counter,
        "successful_requests": len(successful_client_latencies),
        "failed_requests": failed_count,
        "client_stats": client_stats,
        "server_stats": server_stats,
        "retrieval_stats": retrieval_stats,
        "llm_stats": llm_stats,
        "records": records,
    }

    return result_payload


def export_csv(records: List[Dict[str, Any]], filepath: str) -> None:
    """Export benchmark query records to CSV."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    fieldnames = [
        "request_num",
        "iteration",
        "case_id",
        "question",
        "status",
        "http_status",
        "client_latency_ms",
        "server_latency_ms",
        "retrieval_ms",
        "llm_ms",
        "mode",
        "session_id",
        "error",
    ]
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


def export_json(data: Dict[str, Any], filepath: str) -> None:
    """Export benchmark summary and records to JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="AURA Performance Benchmark Suite")
    parser.add_argument("--dataset", type=str, default="tests/golden_set.json", help="Path to evaluation dataset JSON/CSV")
    parser.add_argument("--iterations", type=int, default=1, help="Number of repetitions across questions (default: 1)")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:5000", help="Base URL of AURA API (default: http://127.0.0.1:5000)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request HTTP timeout in seconds (default: 30.0)")
    parser.add_argument("--limit", type=int, default=None, help="Cap maximum questions loaded from dataset")
    parser.add_argument("--in-process", action="store_true", help="Execute directly via Flask test_client without external server")
    parser.add_argument("--csv", type=str, default="data/benchmark_results.csv", help="CSV export destination")
    parser.add_argument("--json", type=str, default="data/benchmark_results.json", help="JSON export destination")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-query output table")

    args = parser.parse_args()

    results = run_benchmark(
        dataset_path=args.dataset,
        iterations=args.iterations,
        base_url=args.url,
        timeout=args.timeout,
        limit=args.limit,
        in_process=args.in_process,
        quiet=args.quiet,
    )

    # Print the clean performance report
    report_text = format_performance_report(results["client_stats"], title="AURA PERFORMANCE REPORT")
    print(report_text)

    # If server stats or breakdown available, display component timings
    if results.get("retrieval_stats") and results["retrieval_stats"].get("successful_requests", 0) > 0:
        ret_stats = results["retrieval_stats"]
        print("Component Breakdown (Average / P50 / P95):")
        print(f"  • Retrieval: {ret_stats.get('average_ms', 0):.1f} ms avg | P50: {ret_stats.get('p50_ms', 0):.1f} ms | P95: {ret_stats.get('p95_ms', 0):.1f} ms")
    if results.get("llm_stats") and results["llm_stats"].get("successful_requests", 0) > 0:
        llm_stats = results["llm_stats"]
        print(f"  • LLM Inference: {llm_stats.get('average_ms', 0):.1f} ms avg | P50: {llm_stats.get('p50_ms', 0):.1f} ms | P95: {llm_stats.get('p95_ms', 0):.1f} ms")
        print("")

    if args.csv:
        csv_path = os.path.join(ROOT, args.csv) if not os.path.isabs(args.csv) else args.csv
        export_csv(results["records"], csv_path)
        print(f"Exported CSV records to: {csv_path}")

    if args.json:
        json_path = os.path.join(ROOT, args.json) if not os.path.isabs(args.json) else args.json
        export_json(results, json_path)
        print(f"Exported JSON metrics to: {json_path}")


if __name__ == "__main__":
    main()

