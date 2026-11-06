"""Tests for Smart Call-to-Action (CTA) and Email Draft Generation.

Verifies:
  1. Click-to-Call functionality and phone number detection.
  2. Smart Email Draft generation for all trigger phrases:
     - "Give me an email draft"
     - "Draft an email to the HOD"
     - "Write an email regarding attendance"
     - "Help me send a complaint"
     - "I need to request permission"
  3. Structured Email Draft fields (To, Subject, Body, Signature) and Gmail URL compatibility.
  4. Intelligent Intent Detection for contacts:
     - Examination department contact
     - HOD contact details
     - Placement department contact & officer email
  5. Context-aware clarification for unclear contact requests ("I want to contact someone regarding my issue").
"""
import unittest

from agent.core import run_agent
from agent.clarify import check as clarify_check
from agent.email_drafter import (
    clean_phone_uri,
    extract_contact_actions,
    generate_smart_email_draft,
    is_email_draft_request,
)


class TestCtaAndEmailDraft(unittest.TestCase):
    def test_phone_number_extraction_and_call_uri(self):
        """Valid Indian mobile numbers and landlines must produce clean tel: URIs."""
        text = "Contact Mr. G. Ranjith Kumar at 90144 32147 or Librarian Mr. Sammi Reddy at 0870-2818384."
        actions = extract_contact_actions(text)
        self.assertIn("calls", actions)
        self.assertGreaterEqual(len(actions["calls"]), 1)
        
        # Check tel URI format
        uris = [c["tel"] for c in actions["calls"]]
        self.assertTrue(any("tel:+919014432147" in u for u in uris))
        
        # Clean phone URI utility
        self.assertEqual(clean_phone_uri("9014432147"), "tel:+919014432147")
        self.assertEqual(clean_phone_uri("+91 9717696258"), "tel:+919717696258")
        self.assertEqual(clean_phone_uri("0870-2818384"), "tel:08702818384")

    def test_email_draft_trigger_detection(self):
        """All required trigger phrases must be detected as email drafting intent."""
        triggers = [
            "Give me an email draft.",
            "Draft an email to the HOD.",
            "I want to contact the examination department to draft an email.",
            "Write an email regarding attendance.",
            "Help me send a complaint.",
            "I need to request permission from the HOD.",
            "Draft an email for condonation.",
            "Write a complaint about attendance.",
        ]
        for t in triggers:
            self.assertTrue(is_email_draft_request(t), f"Trigger failed for: {t}")

        # Normal queries must NOT be falsely identified as draft requests
        non_triggers = [
            "What is the minimum pass marks?",
            "What is the attendance condonation percentage?",
            "Who is the dean of CSE?",
        ]
        for nt in non_triggers:
            self.assertFalse(is_email_draft_request(nt), f"False positive for: {nt}")

    def test_generate_email_draft_structure(self):
        """Generated email drafts must have To, Subject, Body, and verified cites."""
        res = generate_smart_email_draft(
            "Draft an email to the HOD regarding permission",
            profile={"roll_number": "2303A51001", "branch": "CSE", "name": "Rahul"}
        )
        self.assertEqual(res["mode"], "email_draft")
        self.assertIn("email_draft", res)
        draft = res["email_draft"]
        self.assertIn("to", draft)
        self.assertIn("subject", draft)
        self.assertIn("body", draft)
        
        # Verify student details are populated in body
        self.assertIn("2303A51001", draft["body"])
        self.assertIn("CSE", draft["body"])
        self.assertIn("Rahul", draft["body"])
        self.assertIn("g.ranjith@sru.edu.in", draft["to"])

    def test_attendance_complaint_email_draft(self):
        """A request like 'I want to complain about attendance' generates an email to Student Welfare."""
        res = run_agent("I want to complain about attendance", profile={"roll_number": "2303A51042"})
        self.assertEqual(res["mode"], "email_draft")
        draft = res["email_draft"]
        self.assertEqual(draft["to"], "dean.sw@sru.edu.in")
        self.assertIn("Application for Attendance", draft["subject"])
        self.assertIn("2303A51042", draft["body"])
        self.assertIn("Handbook 2026-27 p.5", res["citations"][0])

    def test_hod_contact_details_has_call_cta(self):
        """'Give me the HOD contact details' returns phone numbers with Call Now actions."""
        res = run_agent("Give me the HOD contact details")
        self.assertIn("actions", res)
        self.assertIn("calls", res["actions"])
        self.assertGreater(len(res["actions"]["calls"]), 0)
        # Check that Ranjith Kumar's phone is attached as CTA
        call_uris = [c["tel"] for c in res["actions"]["calls"]]
        self.assertTrue(any("9014432147" in u for u in call_uris))

    def test_placement_department_contact_actions(self):
        """Placement contact queries must return official placement emails."""
        res = run_agent("How can I contact the placement department?")
        self.assertIn("pc.soe@sru.edu.in", res["answer"])
        self.assertIn("actions", res)
        self.assertIn("emails", res["actions"])
        self.assertTrue(any("pc.soe@sru.edu.in" in e for e in res["actions"]["emails"]))

        res2 = run_agent("Give me the placement officer's email")
        self.assertIn("pc.soe@sru.edu.in", res2["answer"])
        self.assertIn("actions", res2)
        self.assertTrue(any("pc.soe@sru.edu.in" in e for e in res2["actions"]["emails"]))

    def test_examination_department_contact(self):
        """'What is the examination department contact number' returns official email and office."""
        res = run_agent("What is the examination department contact number")
        self.assertIn("examcell@sru.edu.in", res["answer"])
        self.assertIn("Block-I", res["answer"])
        self.assertIn("actions", res)
        self.assertTrue(any("examcell@sru.edu.in" in e for e in res["actions"]["emails"]))

    def test_unclear_contact_clarification(self):
        """'I want to contact someone regarding my issue' triggers intelligent follow-up questions."""
        res = clarify_check("I want to contact someone regarding my issue")
        self.assertIsNotNone(res)
        self.assertEqual(res["mode"], "clarify")
        self.assertIn("Attendance", res["options"])
        self.assertIn("Examinations", res["options"])
        self.assertIn("Placements", res["options"])
        self.assertIn("Fee-related issues", res["options"])
        self.assertIn("Academic issues", res["options"])

    def test_dept_contact_method_clarification(self):
        """'I want to contact this department' asks whether user prefers calling or emailing."""
        res = clarify_check("I want to contact this department")
        self.assertIsNotNone(res)
        self.assertEqual(res["mode"], "clarify")
        self.assertIn("Examination Cell", res["options"])
        self.assertIn("Department HOD", res["options"])


if __name__ == "__main__":
    unittest.main()
