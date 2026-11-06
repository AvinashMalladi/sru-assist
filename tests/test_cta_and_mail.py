"""Unit & Integration Tests for the Automated Call to Action (CTA) & Mail Drafting Engine."""
import unittest
import urllib.parse
from agent.cta import build_mail_draft, generate_cta
from agent.core import run_agent


class TestCTAAndMailDrafting(unittest.TestCase):
    def test_hostel_maintenance_cta_generation(self):
        """Hostel issue must produce a telephone link and a structured hostel email draft."""
        profile = {
            "roll_number": "2303A52465",
            "degree": "B.Tech",
            "program": "Computer Science & AI",
            "batch": "2023-27",
            "regulation": "R23",
        }
        contact_record = {
            "id": "hostel_boys_manager",
            "role": "Hostel Manager (Boys)",
            "current_name": "Mr. A. Surender",
            "phone": "9989671719",
            "email": "stu.boyshostel@sru.edu.in",
            "office": "Beside Dining Hall (BH-2 Desk)",
            "category": "Hostels",
        }
        cta = generate_cta("water leakage in BH-2 room 304", contact_record=contact_record, profile=profile)
        self.assertIsNotNone(cta)
        self.assertEqual(cta["phone"], "9989671719")
        self.assertEqual(cta["email"], "stu.boyshostel@sru.edu.in")
        self.assertIn("Hostel Manager", cta["action_label"])

        draft = cta["mail_draft"]
        self.assertEqual(draft["recipient"], "stu.boyshostel@sru.edu.in")
        self.assertEqual(draft["cc"], "c.vinaykumarreddy@sru.edu.in")
        self.assertIn("2303A52465", draft["subject"])
        self.assertIn("2303A52465", draft["body"])
        self.assertIn("Computer Science & AI", draft["body"])
        self.assertTrue(draft["mailto_url"].startswith("mailto:stu.boyshostel@sru.edu.in?"))

    def test_certificate_application_cta(self):
        """TC / Bonafide query must generate certificates desk draft with Room 1002."""
        profile = {"roll_number": "2403A51001", "degree": "B.Tech", "program": "ECE"}
        cta = generate_cta("how to apply my tc", profile=profile)
        self.assertIsNotNone(cta)
        self.assertEqual(cta["email"], "j.ramadevi@sru.edu.in")
        self.assertEqual(cta["phone"], "9963084035")
        self.assertIn("1002", cta["office"])

        draft = cta["mail_draft"]
        self.assertIn("Transfer Certificate", draft["body"])
        self.assertIn("2403A51001", draft["subject"])

    def test_guest_user_smart_placeholders(self):
        """When profile is missing roll number, placeholders must prevent crash."""
        cta = generate_cta("wifi not working in campus", profile=None)
        self.assertIsNotNone(cta)
        self.assertEqual(cta["email"], "a.balakrishna@sru.edu.in")
        self.assertIn("[Enter Roll Number", cta["mail_draft"]["body"])

    def test_typo_sanitization_in_subject_and_body(self):
        """Student typos like 'fafcinf problem with wifi' must be sanitized into a formal topic."""
        profile = {
            "roll_number": "2303A52665",
            "degree": "B.Tech",
            "program": "Computer Science & AI / ML",
        }
        cta = generate_cta("I'm fafcinf problem with wifi", profile=profile)
        self.assertIsNotNone(cta)
        draft = cta["mail_draft"]
        # Subject must NOT contain raw typos
        self.assertNotIn("fafcinf", draft["subject"])
        self.assertNotIn("I'm", draft["subject"])
        self.assertIn("[IT NETWORK]", draft["subject"])
        self.assertIn("Wi-Fi Connectivity", draft["subject"])
        self.assertIn("2303A52665", draft["subject"])
        # Body must NOT contain raw typos
        self.assertNotIn("fafcinf", draft["body"])
        self.assertIn("a.balakrishna@sru.edu.in", draft["recipient"])

    def test_end_to_end_agent_response_contains_cta(self):
        """run_agent for actionable queries must attach cta to the response."""
        res = run_agent(
            "who is the AO of hostel?",
            profile={"roll_number": "2303A52665", "degree": "B.Tech", "program": "CSE"}
        )
        self.assertIn("cta", res)
        cta = res["cta"]
        self.assertEqual(cta["email"], "c.vinaykumarreddy@sru.edu.in")
        self.assertEqual(cta["phone"], "9966001761")
        self.assertIn("2303A52665", cta["mail_draft"]["subject"])

    def test_greeting_and_acknowledgement_suppress_cta_and_citations(self):
        """Conversational greetings ('hlo') and acknowledgements ('ok', 'thanks')
        must NEVER inherit lingering contacts, generate CTAs, or attach prior citations."""
        history = [
            {"role": "user", "content": "I'm fafcinf problem with wifi"},
            {"role": "assistant", "content": "Contact IT support at 8886522500..."},
        ]
        # Follow-up with informal greeting 'hlo'
        res_hlo = run_agent("hlo", history=history, profile={"roll_number": "2303A52665"})
        self.assertEqual(res_hlo.get("mode"), "greeting")
        self.assertNotIn("cta", res_hlo)
        self.assertEqual(res_hlo.get("citations"), [])

        # Follow-up with conversational acknowledgement 'ok'
        res_ok = run_agent("ok", history=history, profile={"roll_number": "2303A52665"})
        self.assertEqual(res_ok.get("mode"), "acknowledgement")
        self.assertNotIn("cta", res_ok)
        self.assertEqual(res_ok.get("citations"), [])

    def test_policy_query_does_not_generate_cta(self):
        """General academic queries like pass marks must NOT generate an irrelevant CTA."""
        res = run_agent("What is the minimum pass marks?", profile={"roll_number": "2303A52665"})
        self.assertNotIn("cta", res)
        self.assertTrue(len(res.get("citations", [])) > 0)


if __name__ == "__main__":
    unittest.main()

