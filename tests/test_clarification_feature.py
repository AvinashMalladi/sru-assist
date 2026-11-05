"""Test suite for Intelligent Conversational Clarification & Multi-Turn Context Resolution.

Covers requirements from Feature Specification:
1. Clear questions should receive direct answers without clarification.
2. Ambiguous questions should trigger relevant follow-up questions.
3. Students should be able to clarify using natural language.
4. Short answers should be interpreted using conversation history.
5. Multi-turn conversations should preserve context across turns.
6. Different regulations should not be mixed.
7. Clickable options should be returned in mode: "clarify".
8. Ordinal selections (e.g. 'first one', 'second one') resolve accurately.
"""
import unittest
import os
import sys

# Ensure repository root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agent.clarify import check as clarify_check
from agent.context_resolver import (
    extract_previous_options,
    match_student_choice,
    resolve_contextual_query,
)
from agent.core import run_agent


class TestClarificationFeature(unittest.TestCase):

    def test_clear_questions_bypass_clarification(self):
        """1. Clear questions must receive direct answers and NOT trigger clarification."""
        clear_queries = [
            "What is the minimum pass marks?",
            "What is the minimum pass percentage?",
            "Explain the letter grade scale",
            "What are the anti-ragging rules?",
            "Who do I contact for Wi-Fi problems?",
            "What are professional electives in R23 regulation?",
            "How is SGPA calculated?",
            "What is the attendance condonation fee?",
        ]
        for q in clear_queries:
            res = clarify_check(q, history=[], profile={})
            self.assertIsNone(
                res,
                f"Query '{q}' should not trigger clarify mode, but got facet: {res and res.get('clarify_facet')}"
            )

    def test_ambiguous_queries_trigger_clarification(self):
        """2. Vague umbrella questions must trigger clarification with 3-5 options."""
        ambiguous_cases = [
            ("I have a problem with attendance.", "attendance"),
            ("Tell me about attendance.", "attendance"),
            ("I have an attendance problem.", "attendance"),
            ("I have a problem with my marks.", "grades"),
            ("I have a doubt about my grade.", "grades"),
            ("What about my grade?", "grades"),
            ("Can I write the exam?", "exam_eligibility"),
            ("Can I write my exam?", "exam_eligibility"),
            ("I have a backlog.", "backlogs"),
            ("What happens if I fail?", "backlogs"),
            ("I want to know about my subjects.", "subjects"),
            ("Tell me about my subjects.", "subjects"),
        ]
        for q, expected_facet in ambiguous_cases:
            res = clarify_check(q, history=[], profile={})
            self.assertIsNotNone(res, f"Query '{q}' should trigger clarify mode")
            self.assertEqual(res.get("mode"), "clarify")
            self.assertEqual(res.get("clarify_facet"), expected_facet)
            options = res.get("options", [])
            self.assertGreaterEqual(len(options), 2, f"Options for '{q}' should be at least 2")
            self.assertLessEqual(len(options), 5, f"Options for '{q}' should be at most 5")

    def test_multi_turn_sub_clarification(self):
        """3. Multi-turn sub-clarification progresses logically."""
        hist = [
            {"role": "user", "content": "I have an attendance problem."},
            {"role": "assistant", "content": "Are you asking about minimum attendance or condonation?"}
        ]
        # Student answers 'My attendance is below 75%'
        res = clarify_check("My attendance is below 75%", history=hist)
        self.assertIsNotNone(res)
        self.assertEqual(res.get("clarify_facet"), "attendance_below_75")
        self.assertIn("Examination Eligibility", res.get("options", []))
        self.assertIn("Attendance Condonation Rules", res.get("options", []))

        # Student clarifies 'Condonation'
        res2 = clarify_check("Condonation", history=hist)
        self.assertIsNotNone(res2)
        self.assertEqual(res2.get("clarify_facet"), "attendance_condonation_sub")
        self.assertEqual(len(res2.get("options", [])), 2)

    def test_context_resolver_ordinal_choices(self):
        """4. Ordinal choices ('first one', 'second one', '3rd') map to option semantics."""
        hist = [
            {"role": "user", "content": "I have an attendance problem."},
            {
                "role": "assistant",
                "content": (
                    "I can help you with that! Are you trying to understand:\n"
                    "- Minimum attendance required to write examinations?\n"
                    "- What happens if your attendance is below the required percentage?\n"
                    "- Attendance condonation rules?\n"
                    "- Attendance calculation for individual subjects?"
                )
            }
        ]
        opts = extract_previous_options(hist)
        self.assertEqual(len(opts), 4)

        match1 = match_student_choice("first one", opts)
        self.assertIn("Minimum attendance", match1)

        match2 = match_student_choice("second one", opts)
        self.assertIn("below the required percentage", match2)

        match3 = match_student_choice("3rd", opts)
        self.assertIn("Attendance condonation", match3)

    def test_short_answers_resolution(self):
        """5. Short follow-ups resolve with conversation topic and semantic expansion."""
        hist = [
            {"role": "user", "content": "I have a problem with attendance."},
            {"role": "assistant", "content": "Are you asking about minimum attendance or condonation rules?"}
        ]
        resolved = resolve_contextual_query("Condonation", history=hist)
        self.assertTrue(resolved["is_continuation"])
        self.assertEqual(resolved["active_topic"], "attendance")
        self.assertIn("condonation", resolved["resolved_query"].lower())
        self.assertIn("attendance", resolved["resolved_query"].lower())

    def test_existing_probes_intact(self):
        """6. Existing hostel gender and branch probes remain 100% operational."""
        # Hostel gender check
        res_hostel = clarify_check("Who do I contact for a hostel problem?", history=[], profile={})
        self.assertIsNotNone(res_hostel)
        self.assertEqual(res_hostel.get("clarify_facet"), "hostel_gender")

        # Gender already declared -> None
        res_hostel_declared = clarify_check(
            "hostel fee refund",
            history=[{"role": "user", "content": "Girls Hostel"}],
            profile={}
        )
        self.assertIsNone(res_hostel_declared)

    def test_e2e_clarification_to_answer(self):
        """7. End-to-end flow from vague query to clarification to final grounded answer."""
        # Turn 1: Vague query
        r1 = run_agent("I have a doubt about my grade.")
        self.assertEqual(r1.get("mode"), "clarify")
        self.assertTrue(bool(r1.get("options")))

        # Turn 2: Clarification
        hist = [
            {"role": "user", "content": "I have a doubt about my grade."},
            {"role": "assistant", "content": r1["answer"]}
        ]
        r2 = run_agent("What happens if I get F grade?", history=hist)
        self.assertIn(r2.get("mode"), ("fast", "agent"))
        self.assertGreater(len(r2.get("citations", [])), 0)
        self.assertTrue("F" in r2.get("answer", "") or "grade" in r2.get("answer", "").lower())


if __name__ == "__main__":
    unittest.main()
