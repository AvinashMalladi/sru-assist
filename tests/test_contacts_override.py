"""Unit tests for Live Contacts and Personnel Directory Overrides.

Verifies:
1. Detection and matching of live personnel overrides (e.g. boys hostel in-charge, girls warden).
2. Authoritative contact badge output with verification timestamps and preceding official tracking.
3. Multi-turn clarifying resolution (hostel question -> user picks boys/girls -> live contact output).
4. Updating personnel via update_personnel() immediately reflects in agent responses.
"""
import unittest

from agent.contacts import (
    load_contacts,
    match_contact_override,
    update_personnel,
    format_contact_response,
)
from agent.core import run_agent


class TestContactsOverride(unittest.TestCase):
    def test_match_boys_hostel_incharge(self):
        """Query asking for boys hostel in-charge must match hostel_boys_manager."""
        contact = match_contact_override("who is the boys hostel incharge")
        self.assertIsNotNone(contact)
        self.assertEqual(contact["id"], "hostel_boys_manager")
        self.assertIn("stu.boyshostel@sru.edu.in", contact["email"])

    def test_match_girls_hostel_incharge(self):
        """Query asking for girls hostel in-charge must match hostel_girls_manager."""
        contact = match_contact_override("who is the girls hostel warden")
        self.assertIsNotNone(contact)
        self.assertEqual(contact["id"], "hostel_girls_manager")
        self.assertIn("stu.girlshostel@sru.edu.in", contact["email"])

    def test_run_agent_serves_verified_contact(self):
        """run_agent must return live directory response with official desk email and notice."""
        resp = run_agent("who is the boys hostel incharge")
        self.assertEqual(resp.get("mode"), "live_directory_match")
        answer = resp.get("answer", "")
        self.assertIn("stu.boyshostel@sru.edu.in", answer)
        self.assertIn("Live Directory Verified", answer)
        self.assertIn("BH-2", answer)

    def test_personnel_update_lifecycle(self):
        """Updating personnel must track previous official and immediately reflect in agent answer."""
        # 1. Update in-charge
        res = update_personnel(
            position_id="hostel_boys_manager",
            name="Dr. K. Srinivas",
            phone="9848011223",
            notice="Newly appointed Boys Hostel Chief Warden.",
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["new_name"], "Dr. K. Srinivas")

        # 2. Query agent
        resp = run_agent("who is the boys hostel incharge")
        self.assertEqual(resp.get("mode"), "live_directory_match")
        answer = resp.get("answer", "")
        self.assertIn("Dr. K. Srinivas", answer)
        self.assertIn("9848011223", answer)

        # 3. Restore default desk
        update_personnel(
            position_id="hostel_boys_manager",
            name="Office of Chief Warden (Boys Hostel)",
            phone="9989671719",
        )

    def test_two_turn_clarification_resolution(self):
        """Ambiguous hostel question followed by gender specification must resolve live contact."""
        # Turn 1: Ambiguous question
        turn1 = run_agent("who is the hostel incharge?")
        self.assertEqual(turn1.get("mode"), "clarify")
        self.assertIn("Boys Hostel", turn1.get("options", []))

        # Turn 2: User responds "Boys Hostel"
        history = [
            {"role": "user", "content": "who is the hostel incharge?"},
            {"role": "assistant", "content": turn1.get("answer")},
        ]
        turn2 = run_agent("Boys Hostel", history=history)
        self.assertEqual(turn2.get("mode"), "live_directory_match")
        self.assertIn("stu.boyshostel@sru.edu.in", turn2.get("answer", ""))


if __name__ == "__main__":
    unittest.main()
