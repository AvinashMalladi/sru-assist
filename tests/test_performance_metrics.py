"""Unit tests for AURA Performance Metrics and Percentile Calculations.

Tests:
- Percentile calculations using known analytical datasets.
- Empty datasets.
- Single-request datasets.
- Repeated queries (identical values).
- Handling of failed requests.
- CSV and JSON benchmark report generation.
"""

import csv
import json
import os
import shutil
import tempfile
import unittest

from agent.metrics import (
    calculate_latency_stats,
    calculate_percentile,
    format_performance_report,
)
from scripts.benchmark import export_csv, export_json


class TestPerformanceMetrics(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_percentile_known_dataset(self):
        """Verify linear percentile interpolation against known analytical values.
        
        Dataset: [10.0, 20.0, 30.0, 40.0, 50.0]
        N = 5
        For p=50: q = 0.5 * 4 = 2.0 -> index 2 -> 30.0
        For p=90: q = 0.9 * 4 = 3.6 -> 40.0 + 0.6*(50.0 - 40.0) = 46.0
        For p=95: q = 0.95 * 4 = 3.8 -> 40.0 + 0.8*(50.0 - 40.0) = 48.0
        For p=99: q = 0.99 * 4 = 3.96 -> 40.0 + 0.96*(50.0 - 40.0) = 49.6
        """
        data = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertAlmostEqual(calculate_percentile(data, 50.0), 30.0, places=4)
        self.assertAlmostEqual(calculate_percentile(data, 90.0), 46.0, places=4)
        self.assertAlmostEqual(calculate_percentile(data, 95.0), 48.0, places=4)
        self.assertAlmostEqual(calculate_percentile(data, 99.0), 49.6, places=4)
        self.assertAlmostEqual(calculate_percentile(data, 0.0), 10.0, places=4)
        self.assertAlmostEqual(calculate_percentile(data, 100.0), 50.0, places=4)

    def test_percentile_empty_dataset(self):
        """Empty dataset should safely return 0.0 without errors."""
        self.assertEqual(calculate_percentile([], 50.0), 0.0)
        self.assertEqual(calculate_percentile([], 90.0), 0.0)
        self.assertEqual(calculate_percentile([], 99.0), 0.0)

        stats = calculate_latency_stats([])
        self.assertEqual(stats["total_requests"], 0)
        self.assertEqual(stats["successful_requests"], 0)
        self.assertEqual(stats["failed_requests"], 0)
        self.assertEqual(stats["average_ms"], 0.0)
        self.assertEqual(stats["p50_ms"], 0.0)
        self.assertEqual(stats["p90_ms"], 0.0)
        self.assertEqual(stats["p95_ms"], 0.0)
        self.assertEqual(stats["p99_ms"], 0.0)

    def test_percentile_single_request(self):
        """Single-request dataset should return that single value for all percentiles."""
        data = [150.0]
        self.assertEqual(calculate_percentile(data, 0.0), 150.0)
        self.assertEqual(calculate_percentile(data, 50.0), 150.0)
        self.assertEqual(calculate_percentile(data, 90.0), 150.0)
        self.assertEqual(calculate_percentile(data, 95.0), 150.0)
        self.assertEqual(calculate_percentile(data, 99.0), 150.0)
        self.assertEqual(calculate_percentile(data, 100.0), 150.0)

        stats = calculate_latency_stats(data)
        self.assertEqual(stats["total_requests"], 1)
        self.assertEqual(stats["successful_requests"], 1)
        self.assertEqual(stats["failed_requests"], 0)
        self.assertEqual(stats["min_ms"], 150.0)
        self.assertEqual(stats["max_ms"], 150.0)
        self.assertEqual(stats["average_ms"], 150.0)
        self.assertEqual(stats["p50_ms"], 150.0)
        self.assertEqual(stats["p90_ms"], 150.0)
        self.assertEqual(stats["p95_ms"], 150.0)
        self.assertEqual(stats["p99_ms"], 150.0)

    def test_percentile_repeated_queries(self):
        """Repeated identical queries should yield identical percentile and average values."""
        data = [200.0] * 20
        stats = calculate_latency_stats(data)
        self.assertEqual(stats["total_requests"], 20)
        self.assertEqual(stats["successful_requests"], 20)
        self.assertEqual(stats["failed_requests"], 0)
        self.assertEqual(stats["min_ms"], 200.0)
        self.assertEqual(stats["max_ms"], 200.0)
        self.assertEqual(stats["average_ms"], 200.0)
        self.assertEqual(stats["p50_ms"], 200.0)
        self.assertEqual(stats["p90_ms"], 200.0)
        self.assertEqual(stats["p95_ms"], 200.0)
        self.assertEqual(stats["p99_ms"], 200.0)

    def test_failed_requests_handling(self):
        """Verify failed requests are accounted for properly in summary stats."""
        latencies = [100.0, 200.0, 300.0]
        stats = calculate_latency_stats(latencies, total_requests=5, failed_requests=2)
        self.assertEqual(stats["total_requests"], 5)
        self.assertEqual(stats["successful_requests"], 3)
        self.assertEqual(stats["failed_requests"], 2)
        self.assertEqual(stats["average_ms"], 200.0)
        self.assertEqual(stats["min_ms"], 100.0)
        self.assertEqual(stats["max_ms"], 300.0)
        self.assertEqual(stats["p50_ms"], 200.0)

    def test_invalid_percentile_raises(self):
        """Passing percentile < 0 or > 100 should raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_percentile([1.0, 2.0], -5.0)
        with self.assertRaises(ValueError):
            calculate_percentile([1.0, 2.0], 105.0)

    def test_format_performance_report(self):
        """Verify format_performance_report produces expected text format."""
        stats = {
            "total_requests": 100,
            "successful_requests": 98,
            "failed_requests": 2,
            "average_ms": 1250.4,
            "min_ms": 450.0,
            "max_ms": 4200.0,
            "p50_ms": 1100.0,
            "p90_ms": 2100.0,
            "p95_ms": 2800.0,
            "p99_ms": 3900.0,
        }
        report = format_performance_report(stats)
        self.assertIn("AURA PERFORMANCE REPORT", report)
        self.assertIn("Total Requests: 100", report)
        self.assertIn("Successful Requests: 98", report)
        self.assertIn("Failed Requests: 2", report)
        self.assertIn("Average Latency: 1250 ms", report)
        self.assertIn("Minimum Latency: 450 ms", report)
        self.assertIn("Maximum Latency: 4200 ms", report)
        self.assertIn("P50 Latency: 1100 ms", report)
        self.assertIn("P90 Latency: 2100 ms", report)
        self.assertIn("P95 Latency: 2800 ms", report)
        self.assertIn("P99 Latency: 3900 ms", report)

    def test_csv_and_json_report_generation(self):
        """Verify CSV and JSON export functions write valid and readable files."""
        records = [
            {
                "case_id": "test_1",
                "question": "What are the pass marks?",
                "iteration": 1,
                "status": "success",
                "http_status": 200,
                "latency_ms": 150.5,
                "retrieval_ms": 12.3,
                "llm_ms": 135.0,
                "backend_total_ms": 149.0,
                "confidence": 0.95,
                "cached": False,
                "error": None,
            },
            {
                "case_id": "test_2",
                "question": "Invalid query",
                "iteration": 1,
                "status": "failed",
                "http_status": 500,
                "latency_ms": 50.0,
                "retrieval_ms": 0.0,
                "llm_ms": 0.0,
                "backend_total_ms": 0.0,
                "confidence": 0.0,
                "cached": False,
                "error": "TimeoutError",
            },
        ]
        overall_stats = {
            "total_requests": 2,
            "successful_requests": 1,
            "failed_requests": 1,
            "average_ms": 150.5,
            "min_ms": 150.5,
            "max_ms": 150.5,
            "p50_ms": 150.5,
            "p90_ms": 150.5,
            "p95_ms": 150.5,
            "p99_ms": 150.5,
        }
        retrieval_stats = {"average_ms": 12.3, "p50_ms": 12.3}
        llm_stats = {"average_ms": 135.0, "p50_ms": 135.0}

        csv_path = os.path.join(self.temp_dir, "benchmark.csv")
        json_path = os.path.join(self.temp_dir, "benchmark.json")

        export_csv(records, csv_path)
        export_json(
            {
                "summary": {"overall": overall_stats, "retrieval": retrieval_stats, "llm": llm_stats},
                "records": records,
            },
            json_path,
        )

        self.assertTrue(os.path.exists(csv_path))
        self.assertTrue(os.path.exists(json_path))

        # Check CSV content
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 2)
            self.assertEqual(reader[0]["case_id"], "test_1")
            self.assertEqual(reader[0]["status"], "success")
            self.assertEqual(reader[1]["case_id"], "test_2")
            self.assertEqual(reader[1]["status"], "failed")

        # Check JSON content
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
            self.assertIn("summary", payload)
            self.assertIn("records", payload)
            self.assertEqual(payload["summary"]["overall"]["total_requests"], 2)
            self.assertEqual(len(payload["records"]), 2)


if __name__ == "__main__":
    unittest.main()
