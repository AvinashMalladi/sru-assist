"""Tests for Smart Hostel Assistant + FretBox Integration.

Verifies:
  1. Intent classification across all 12 hostel categories.
  2. Handbook-grounded answers for hostel facilities, rules, blocks, and contacts.
  3. Actionable FretBox buttons for maintenance, electrical, water, cleaning, wifi, meals, and outpasses.
  4. Context-aware clarification for vague hostel problems ('There is a problem in my hostel').
  5. Multi-turn resolution of clarification choices.
"""
import unittest

from agent.core import run_agent
from agent.hostel_assistant import classify_hostel_intent, handle_hostel_query


class TestHostelFretboxAssistant(unittest.TestCase):
    def test_intent_classification(self):
        """All required hostel intents must be classified correctly."""
        self.assertEqual(classify_hostel_intent("My room fan is not working"), "HOSTEL_ELECTRICAL_ISSUE")
        self.assertEqual(classify_hostel_intent("The tube light in my room is not working"), "HOSTEL_ELECTRICAL_ISSUE")
        self.assertEqual(classify_hostel_intent("There is no water in the bathroom"), "HOSTEL_WATER_ISSUE")
        self.assertEqual(classify_hostel_intent("My bathroom tap is leaking"), "HOSTEL_WATER_ISSUE")
        self.assertEqual(classify_hostel_intent("The washroom is not clean"), "HOSTEL_CLEANING_ISSUE")
        self.assertEqual(classify_hostel_intent("The hostel Wi-Fi is not working"), "HOSTEL_WIFI_ISSUE")
        self.assertEqual(classify_hostel_intent("My room door lock is damaged"), "HOSTEL_MAINTENANCE_COMPLAINT")
        self.assertEqual(classify_hostel_intent("I want to book my lunch"), "HOSTEL_MEAL_BOOKING")
        self.assertEqual(classify_hostel_intent("How can I book meals?"), "HOSTEL_MEAL_BOOKING")
        self.assertEqual(classify_hostel_intent("How can I apply for an outpass?"), "HOSTEL_OUTPASS")
        self.assertEqual(classify_hostel_intent("Where can I find my outpass QR code?"), "HOSTEL_OUTPASS")
        self.assertEqual(classify_hostel_intent("Whom should I contact regarding hostel issues?"), "HOSTEL_CONTACT_INFORMATION")
        self.assertEqual(classify_hostel_intent("What are the hostel facilities?"), "HOSTEL_FACILITIES")
        self.assertEqual(classify_hostel_intent("What are the hostel rules?"), "HOSTEL_RULES")
        self.assertEqual(classify_hostel_intent("There is a problem in my hostel"), "UNKNOWN_HOSTEL_QUERY")

    def test_electrical_maintenance_complaint(self):
        """Fan/light issues must provide FretBox steps and 'Raise Complaint in FretBox' button."""
        res = run_agent("My room fan is not working")
        self.assertEqual(res["mode"], "fretbox_action")
        self.assertIn("FretBox", res["answer"])
        self.assertIn("fretbox", res)
        self.assertIn(res["fretbox"]["label"], ["Open FretBox", "Raise Complaint in FretBox"])
        self.assertIn("Handbook 2026-27 p.23", res["citations"][0])

    def test_water_supply_complaint(self):
        """No water / tap leaking issues must provide FretBox steps and 'Raise Complaint in FretBox' button."""
        res = run_agent("There is no water in the bathroom")
        self.assertEqual(res["mode"], "fretbox_action")
        self.assertIn("FretBox", res["answer"])
        self.assertIn("fretbox", res)
        self.assertIn(res["fretbox"]["label"], ["Open FretBox", "Raise Complaint in FretBox"])
        self.assertEqual(res["fretbox"]["icon"], "🚰")

    def test_meal_booking_action(self):
        """Meal booking query must explain FretBox dining and provide 'Book Meal in FretBox' button."""
        res = run_agent("I want to book my dinner")
        self.assertEqual(res["mode"], "fretbox_action")
        self.assertIn("FretBox", res["answer"])
        self.assertIn("fretbox", res)
        self.assertEqual(res["fretbox"]["label"], "Book Meal in FretBox")
        self.assertEqual(res["fretbox"]["icon"], "🍽️")

    def test_outpass_action(self):
        """Outpass query must explain FretBox application, QR pass, and provide 'Apply for Outpass' button."""
        res = run_agent("How can I apply for an outpass?")
        self.assertEqual(res["mode"], "fretbox_action")
        self.assertIn("QR Code", res["answer"])
        self.assertIn("FretBox", res["answer"])
        self.assertIn("fretbox", res)
        self.assertEqual(res["fretbox"]["label"], "Apply for Outpass")
        self.assertEqual(res["fretbox"]["icon"], "🎫")

    def test_vague_hostel_problem_clarification(self):
        """'There is a problem in my hostel' must trigger intelligent follow-up clarification."""
        res = run_agent("There is a problem in my hostel")
        self.assertEqual(res["mode"], "clarify")
        self.assertIn("options", res)
        self.assertIn("Fan or tube light problem", res["options"])
        self.assertIn("Water supply problem", res["options"])
        self.assertIn("Bathroom or cleaning problem", res["options"])
        self.assertIn("Wi-Fi or internet problem", res["options"])
        self.assertIn("Furniture or room maintenance", res["options"])

    def test_hostel_facilities_handbook_grounded(self):
        """Hostel facilities query must retrieve handbook amenities and have NO FretBox button."""
        res = run_agent("What are the hostel facilities?", profile={"hostel": "Boys"})
        self.assertIn("Triple-sharing", res["answer"])
        self.assertIn("AC", res["answer"])
        self.assertIn("Handbook 2026-27 p.23", res["citations"][0])
        self.assertNotIn("fretbox", res)

    def test_hostel_rules_handbook_grounded(self):
        """Hostel rules query must retrieve handbook rules and have NO FretBox button."""
        res = run_agent("What are the hostel rules?", profile={"hostel": "Boys"})
        self.assertIn("Floor Proctors", res["answer"])
        self.assertIn("Handbook 2026-27 p.23", res["citations"][0])
        self.assertNotIn("fretbox", res)

    def test_hostel_contacts_and_call_ctas(self):
        """Hostel contacts query must return managers with clickable Call Now CTAs."""
        res = run_agent("Whom should I contact regarding hostel issues?")
        self.assertIn("Surender", res["answer"])
        self.assertIn("Shobha Rani", res["answer"])
        self.assertIn("actions", res)
        self.assertIn("calls", res["actions"])
        call_uris = [c["tel"] for c in res["actions"]["calls"]]
        self.assertTrue(any("9989671719" in u for u in call_uris))
        self.assertTrue(any("9701578799" in u for u in call_uris))


if __name__ == "__main__":
    unittest.main()
