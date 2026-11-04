"""Unit tests for API payload edge cases and database safety."""

import unittest
from app import app
from agent import db


class TestApiEdgeCases(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_invalid_roll_does_not_save_to_db(self):
        """Sending future roll 3103A52313 should return invalid notice and NOT save student."""
        res = self.client.post("/api/chat", json={
            "message": "3103A52313",
            "session_id": "test_future_roll_session"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("mode"), "invalid_roll_number")

        # Verify DB does not contain 3103A52313
        student = db.get_student("3103A52313")
        self.assertIsNone(student)

    def test_non_string_session_id_does_not_crash(self):
        """Passing integer session_id or htno should not raise AttributeError."""
        res = self.client.post("/api/chat", json={
            "message": "hello",
            "session_id": 99999,
            "htno": 12345
        })
        self.assertEqual(res.status_code, 200)

    def test_oversized_history_is_truncated(self):
        """Giant history array should be handled gracefully without memory blowup."""
        fake_history = [{"role": "user", "content": f"msg {i}"} for i in range(200)]
        res = self.client.post("/api/chat", json={
            "message": "What is the pass mark?",
            "history": fake_history,
            "session_id": "test_oversized_history"
        })
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()

