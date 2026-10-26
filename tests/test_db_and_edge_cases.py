"""Automated comprehensive test suite for DB persistence, htno history restoration,
and edge cases (SQL injection, malformed roll numbers, anonymous linking, smart replies).
"""
import json
import os
import unittest
from app import app
from agent import db
from agent.roll_decoder import parse_roll_number
from agent.normalize import normalize_student_text


class TestDatabaseAndEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        db.init_db()

    def setUp(self):
        # Clean test records before each test
        db.clear_conversation(htno="TEST001A00001")
        db.clear_conversation(htno="2303A51042")
        db.clear_conversation(htno="2101A04008")
        db.clear_conversation(session_id="test_sess_injection")

    def test_1_new_student_identification_and_storage(self):
        """Edge Case 1: First-time student entering htno is stored in DB with profile."""
        res = self.client.post("/api/chat", json={
            "message": "My roll number is 2303A51042",
            "session_id": "sess_student_1"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("2303A51042", data.get("answer", ""))
        self.assertEqual(data.get("htno"), "2303A51042")
        
        # Verify student table record
        student = db.get_student("2303A51042")
        self.assertIsNotNone(student)
        self.assertEqual(student["degree"], "B.Tech")
        self.assertEqual(student["regulation"], "R23")

    def test_2_returning_student_history_retrieval(self):
        """Edge Case 2: Returning student retrieves full prior conversation and personalized suggestions."""
        # Step A: Perform two turns
        self.client.post("/api/chat", json={
            "message": "My roll number is 2303A51042",
            "session_id": "sess_student_2"
        })
        self.client.post("/api/chat", json={
            "message": "What is the minimum pass marks?",
            "session_id": "sess_student_2",
            "htno": "2303A51042"
        })

        # Step B: Request history by htno
        res = self.client.get("/api/history?htno=2303A51042")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        self.assertEqual(data["htno"], "2303A51042")
        self.assertIsNotNone(data["profile"])
        self.assertGreaterEqual(len(data["messages"]), 4) # 2 user + 2 assistant messages
        
        # Check chronological order
        self.assertEqual(data["messages"][0]["role"], "user")
        self.assertEqual(data["messages"][1]["role"], "assistant")
        self.assertEqual(data["messages"][2]["role"], "user")
        self.assertEqual(data["messages"][3]["role"], "assistant")

        # Check suggestions are tailored to R23 / CSE
        self.assertTrue(any("R23" in s or "CSE" in s or "CS" in s for s in data["suggestions"]))

    def test_3_mid_session_htno_linking(self):
        """Edge Case 3: Anonymous start retroactively links all earlier turns once htno is shared."""
        sess_id = "sess_anonymous_flow"
        
        # Turn 1: Anonymous question
        res1 = self.client.post("/api/chat", json={
            "message": "What is the attendance criteria?",
            "session_id": sess_id
        })
        self.assertEqual(res1.status_code, 200)

        # Turn 2: Student enters roll number
        res2 = self.client.post("/api/chat", json={
            "message": "I am 2101A04008",
            "session_id": sess_id
        })
        self.assertEqual(res2.status_code, 200)

        # Fetch history by htno: should include Turn 1 as well!
        hist = db.get_conversation_history(htno="2101A04008")
        self.assertGreaterEqual(len(hist), 4) # Turn 1 (user+bot) + Turn 2 (user+bot)
        first_q = hist[0]["content"]
        self.assertIn("attendance", first_q.lower())

    def test_4_sql_injection_attempts(self):
        """Edge Case 4: Malicious SQL inputs are safely handled without database corruption."""
        malicious_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE conversations; --",
            "' UNION SELECT htno, degree, program FROM students --",
            "1' or 1=1--",
            '" OR ""="'
        ]

        for payload in malicious_payloads:
            res = self.client.get(f"/api/history?htno={payload}")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["messages"], []) # No data leaked

            # Verify conversations table is intact
            cur_test = db.get_conversation_history(limit=1)
            self.assertIsInstance(cur_test, list)

    def test_5_malformed_and_boundary_roll_numbers(self):
        """Edge Case 5: Malformed roll numbers fail gracefully without crash."""
        bad_numbers = ["", "   ", "ABC", "123", "2303A", "INVALID_ROLL_123", "123456789012"]
        for bad in bad_numbers:
            parsed = parse_roll_number(bad)
            self.assertIsNone(parsed)
            
            res = self.client.get(f"/api/history?htno={bad}")
            # Empty or invalid should either return 400 or empty message list without crash
            self.assertIn(res.status_code, (200, 400))

    def test_6_smart_slang_normalization(self):
        """Edge Case 6: Student shortcuts & regional slang normalized properly."""
        test_cases = [
            ("att criteria", "attendance"),
            ("short attendance for exam", "condonation"),
            ("reval process", "revaluation"),
            ("chit in midsem exam", "unfair means"),
            ("dabbulu for tution fee", "tuition fee"),
            ("food delivery at night", "hostel food outside delivery"),
            ("can i bring pet dog", "prohibited items pets"),
            ("mass bunk penalty", "unauthorized absence group absence"),
        ]
        for input_text, expected_normalized in test_cases:
            norm = normalize_student_text(input_text)
            self.assertIn(expected_normalized, norm)

    def test_7_clear_conversation(self):
        """Edge Case 7: Clearing history clears only target htno without affecting others."""
        # Create records for student A and student B
        db.save_turn("sess_a", "Hello from A", "Hi A", htno="2303A51042")
        db.save_turn("sess_b", "Hello from B", "Hi B", htno="2101A04008")

        # Clear student A
        res = self.client.delete("/api/history?htno=2303A51042")
        self.assertEqual(res.status_code, 200)

        # Student A history empty
        hist_a = db.get_conversation_history(htno="2303A51042")
        self.assertEqual(len(hist_a), 0)

        # Student B history preserved
        hist_b = db.get_conversation_history(htno="2101A04008")
        self.assertGreater(len(hist_b), 0)


if __name__ == "__main__":
    unittest.main()
