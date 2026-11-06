"""Unit tests for Intelligent Response and Conditional Action Handling in AURA."""
import unittest
from agent.core import run_agent
from agent.hostel_assistant import classify_hostel_intent, handle_hostel_query


class TestConditionalActionHandling(unittest.TestCase):

    def test_01_greeting_no_actions(self):
        """TEST 1: Greetings like 'Hlo', 'Hi', 'How are you?' receive simple friendly replies with zero actions."""
        for greeting in ["Hlo", "hlo", "Hello", "Hi", "Hey", "Good morning", "How are you?"]:
            res = run_agent(greeting)
            self.assertEqual(res.get("mode"), "greeting", f"Failed for {greeting}")
            self.assertEqual(res.get("citations"), [], f"Failed citations for {greeting}")
            actions = res.get("actions", {})
            self.assertFalse(actions.get("calls"), f"Unexpected calls for {greeting}")
            self.assertFalse(actions.get("emails"), f"Unexpected emails for {greeting}")
            self.assertFalse(actions.get("draft"), f"Unexpected draft for {greeting}")
            self.assertIn("SRU Assist", res.get("answer"))

    def test_02_attendance_eligibility_no_contact_buttons(self):
        """TEST 2: Academic queries provide handbook answers without indiscriminate contact buttons."""
        res = run_agent("What is the attendance eligibility criteria?")
        self.assertTrue(len(res.get("citations", [])) > 0)
        self.assertIn("75%", res.get("answer"))
        actions = res.get("actions", {})
        self.assertFalse(actions.get("calls"), "Call action should not be present on eligibility query")
        self.assertFalse(actions.get("emails"), "Email action should not be present on eligibility query")

    def test_03_examination_contact_with_call_now(self):
        """TEST 3: Direct contact requests for examination department include official number and 'Call Now' button."""
        for q in [
            "Give me the examination department number.",
            "What is the examination department contact number?",
            "What is the examination department contact",
        ]:
            res = run_agent(q)
            self.assertTrue(any("6" in c for c in res.get("citations", [])))
            actions = res.get("actions", {})
            self.assertTrue(actions.get("calls"), f"Missing call action for {q}")
            call_item = actions["calls"][0]
            self.assertIn("9908336336", call_item["tel"])
            self.assertEqual(call_item.get("label"), "Call Now")

    def test_04_vague_attendance_clarification(self):
        """TEST 4: 'I have an attendance issue.' triggers clarification chips."""
        res = run_agent("I have an attendance issue.")
        self.assertEqual(res.get("mode"), "clarify")
        self.assertTrue(len(res.get("options", [])) >= 3)
        self.assertTrue(any("Minimum Attendance" in opt for opt in res["options"]))

    def test_05_attendance_wrongly_marked_absent(self):
        """TEST 5: Reporting wrongly marked absent offers official procedure and draft email prompt."""
        for q in [
            "My attendance is wrongly marked absent.",
            "My attendance is incorrectly marked absent.",
            "I was present but marked absent",
        ]:
            res = run_agent(q)
            self.assertEqual(res.get("mode"), "attendance_correction")
            self.assertIn("Would you like me to prepare a professional email draft", res.get("answer"))
            self.assertEqual(res.get("options"), ["Yes, Draft Email", "No, Thanks"])

    def test_06_followup_yes_draft_email(self):
        """TEST 6: 'Yes, draft an email' after attendance correction generates full email draft."""
        history = [
            {"role": "user", "content": "My attendance is wrongly marked absent."},
            {
                "role": "assistant",
                "content": (
                    "I understand your concern. You can follow the official attendance correction procedure...\n\n"
                    "Would you like me to prepare a professional email draft to the HOD regarding this issue?"
                ),
            },
        ]
        res = run_agent("Yes, draft an email", history=history)
        self.assertEqual(res.get("mode"), "email_draft")
        self.assertIn("email_draft", res)
        draft = res["email_draft"]
        self.assertIn("Attendance", draft["subject"])
        self.assertTrue(res.get("actions", {}).get("draft"))

        # Also test "No, Thanks"
        res_no = run_agent("No, Thanks", history=history)
        self.assertIn("No problem", res_no.get("answer"))
        self.assertNotIn("email_draft", res_no)

    def test_07_hostel_electrical_issue_fretbox_and_ao(self):
        """TEST 7: Hostel electrical complaints provide FretBox steps, [Open FretBox], and [Call Hostel AO]."""
        res = run_agent("My hostel fan is not working.")
        self.assertEqual(res.get("mode"), "fretbox_action")
        self.assertIn("fretbox", res)
        self.assertEqual(res["fretbox"]["label"], "Open FretBox")
        actions = res.get("actions", {})
        self.assertTrue(actions.get("calls"))
        ao_call = actions["calls"][0]
        self.assertIn("9966001761", ao_call["tel"])
        self.assertEqual(ao_call.get("label"), "Call Hostel AO")

    def test_08_hostel_facilities_no_fretbox(self):
        """TEST 8: General hostel facilities query provides handbook details without FretBox/Call buttons."""
        res = run_agent("What are the hostel facilities?")
        self.assertIn("Triple-sharing", res.get("answer"))
        self.assertNotIn("fretbox", res)
        actions = res.get("actions", {})
        self.assertFalse(actions.get("calls"))

    def test_09_hostel_meal_booking(self):
        """TEST 9: Booking meals directs to FretBox with meal action."""
        res = run_agent("I want to book dinner.")
        self.assertEqual(res.get("mode"), "fretbox_action")
        self.assertIn("fretbox", res)
        self.assertEqual(res["fretbox"]["label"], "Book Meal in FretBox")

    def test_10_hostel_outpass(self):
        """TEST 10: Hostel outpass requests direct to FretBox outpass module."""
        res = run_agent("I want an outpass.")
        self.assertEqual(res.get("mode"), "fretbox_action")
        self.assertIn("fretbox", res)
        self.assertEqual(res["fretbox"]["label"], "Apply for Outpass")

    def test_11_security_refusal_change_cgpa(self):
        """TEST 11: Attempting to modify CGPA or marks triggers security refusal with NO action buttons."""
        for q in ["Change my CGPA.", "Modify my marks", "Hack my attendance"]:
            res = run_agent(q)
            self.assertEqual(res.get("mode"), "security_refusal")
            self.assertIn("Security & Academic Integrity Notice", res.get("answer"))
            actions = res.get("actions", {})
            self.assertFalse(actions.get("calls"))
            self.assertFalse(actions.get("emails"))

    def test_12_hostel_ao_contact(self):
        """TEST 12: 'Who is the AO of the hostel?' provides official details with 'Call AO' button."""
        res = run_agent("Who is the AO of the hostel?")
        self.assertIn("Vinay Kumar", res.get("answer"))
        self.assertTrue(any("24" in c for c in res.get("citations", [])))
        actions = res.get("actions", {})
        self.assertTrue(actions.get("calls"))
        call_item = actions["calls"][0]
        self.assertIn("9966001761", call_item["tel"])
        self.assertEqual(call_item.get("label"), "Call AO")


if __name__ == "__main__":
    unittest.main()
