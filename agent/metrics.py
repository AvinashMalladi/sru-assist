"""Lightweight performance metrics and percentile calculations for AURA.

Statistically consistent percentile calculation matching NumPy's 'linear' method
(equivalent to NIST recommended percentile method 6 / R type 7).

Mathematical formula for percentile p in [0, 100] over sorted array X of length N:
    q = (p / 100.0) * (N - 1)
    i = floor(q)
    fraction = q - i
    percentile_value = X[i] + fraction * (X[i + 1] - X[i])
"""

import math
from typing import Any, Dict, List, Optional, Sequence


def calculate_percentile(data: Sequence[float], p: float, method: str = "linear") -> float:
    """Calculate the p-th percentile of a sequence of numerical values.

    Args:
        data: Sequence of numerical values (latencies in milliseconds).
        p: Percentile rank to compute, in the range [0, 100].
        method: Interpolation method. Defaults to 'linear', matching NumPy's
            default `numpy.percentile(..., method='linear')`.

    Returns:
        The computed percentile as a float. Returns 0.0 for empty data.
    """
    if not data:
        return 0.0

    if not 0.0 <= p <= 100.0:
        raise ValueError(f"Percentile p must be between 0 and 100, got {p}")

    sorted_data = sorted(float(x) for x in data)
    n = len(sorted_data)

    if n == 1:
        return sorted_data[0]

    # Index position in 0-indexed space
    q = (p / 100.0) * (n - 1)
    i = math.floor(q)
    fraction = q - i

    if i >= n - 1:
        return sorted_data[-1]

    if method == "linear":
        return sorted_data[i] + fraction * (sorted_data[i + 1] - sorted_data[i])
    elif method == "lower":
        return sorted_data[i]
    elif method == "higher":
        return sorted_data[i if fraction == 0 else i + 1]
    elif method == "nearest":
        return sorted_data[round(q)]
    else:
        raise ValueError(f"Unsupported percentile interpolation method: {method}")


def calculate_latency_stats(
    latencies: Sequence[float],
    total_requests: Optional[int] = None,
    failed_requests: int = 0,
) -> Dict[str, Any]:
    """Calculate comprehensive performance statistics from a sequence of latencies in ms.

    Args:
        latencies: Measured response times in milliseconds for successful queries.
        total_requests: Total number of requests attempted. If None, len(latencies) + failed_requests.
        failed_requests: Count of failed requests.

    Returns:
        Dictionary containing request counts, average, min, max, and percentiles (P50, P90, P95, P99).
    """
    clean_latencies = [float(x) for x in latencies if x is not None]
    n_successful = len(clean_latencies)

    if total_requests is None:
        total = n_successful + failed_requests
    else:
        total = total_requests

    if n_successful == 0:
        return {
            "total_requests": total,
            "successful_requests": 0,
            "failed_requests": failed_requests,
            "average_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "p50_ms": 0.0,
            "p90_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
        }

    avg_ms = sum(clean_latencies) / n_successful
    min_ms = min(clean_latencies)
    max_ms = max(clean_latencies)

    p50_ms = calculate_percentile(clean_latencies, 50.0, method="linear")
    p90_ms = calculate_percentile(clean_latencies, 90.0, method="linear")
    p95_ms = calculate_percentile(clean_latencies, 95.0, method="linear")
    p99_ms = calculate_percentile(clean_latencies, 99.0, method="linear")

    return {
        "total_requests": total,
        "successful_requests": n_successful,
        "failed_requests": failed_requests,
        "average_ms": round(avg_ms, 2),
        "min_ms": round(min_ms, 2),
        "max_ms": round(max_ms, 2),
        "p50_ms": round(p50_ms, 2),
        "p90_ms": round(p90_ms, 2),
        "p95_ms": round(p95_ms, 2),
        "p99_ms": round(p99_ms, 2),
    }


def format_performance_report(stats: Dict[str, Any], title: str = "AURA PERFORMANCE REPORT") -> str:
    """Format performance statistics into a clean, human-readable ASCII report."""
    lines = [
        "",
        title,
        "=" * len(title),
        f"Total Requests: {stats.get('total_requests', 0)}",
        f"Successful Requests: {stats.get('successful_requests', 0)}",
        f"Failed Requests: {stats.get('failed_requests', 0)}",
        "",
        f"Average Latency: {int(round(stats.get('average_ms', 0.0)))} ms",
        f"Minimum Latency: {int(round(stats.get('min_ms', 0.0)))} ms",
        f"Maximum Latency: {int(round(stats.get('max_ms', 0.0)))} ms",
        "",
        f"P50 Latency: {int(round(stats.get('p50_ms', 0.0)))} ms",
        f"P90 Latency: {int(round(stats.get('p90_ms', 0.0)))} ms",
        f"P95 Latency: {int(round(stats.get('p95_ms', 0.0)))} ms",
        f"P99 Latency: {int(round(stats.get('p99_ms', 0.0)))} ms",
        "",
    ]
    return "\n".join(lines)

