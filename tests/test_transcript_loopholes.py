"""Regression Tests for Transcript Loopholes & Student Experience Fixes.

Verifies:
  1. Telugu slang & typo normalization ('AO conatct number undaaa' -> Mr. Ch. Vinay Kumar).
  2. Administrative services cross-handbook retrieval (TC / Bonafide / ID card for R23 students).
  3. Page-specific query resolver ('what p.30 is saying ?' retrieves exact page chunks).
  4. Live personnel directory overlay ensuring active wardens (Ms. S. Shobha Rani, Mr. A. Surender)
     override deprecated 2023 handbook names.
"""
import unittest
from agent.contacts import match_contact_override
from agent.core import run_agent
from agent.normalize import normalize_student_text
from agent.retriever import get_retriever


class TestTranscriptLoopholes(unittest.TestCase):
    def setUp(self):
        self.retriever = get_retriever()

    def test_ao_typo_and_slang_resolution(self):
        """'AO conatct number undaaa' must match Mr. Ch. Vinay Kumar (AO Hostels)."""
        hit = match_contact_override("AO conatct number undaaa")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["id"], "hostel_admin_officer")
        self.assertIn("Vinay Kumar", hit["current_name"])
        self.assertEqual(hit["phone"], "9966001761")

        # Also verify via run_agent
        res = run_agent("AO conatct number undaaa")
        self.assertEqual(res.get("mode"), "live_directory_match")
        self.assertIn("9966001761", res["answer"])
        self.assertIn("Vinay Kumar", res["answer"])

    def test_telugu_slang_normalizer(self):
        """Verifies vernacular question particles and common spelling errors."""
        norm1 = normalize_student_text("AO conatct number undaaa")
        self.assertIn("contact", norm1)
        self.assertIn("available", norm1)

        norm2 = normalize_student_text("tc kavali ekkada apply cheppandi")
        self.assertIn("transfer certificate", norm2)
        self.assertIn("required", norm2)
        self.assertIn("where is", norm2)

    def test_tc_application_under_r23_profile(self):
        """R23 profile students must be able to retrieve university-wide TC / certificate procedure."""
        hits = self.retriever.search("how to apply my tc", profile={"regulation": "R23", "degree": "B.Tech"})
        # Must include page 6 of Handbook 2026-27 where certificates desk is located
        docs_and_pages = [(h.doc, h.page) for h in hits]
        self.assertTrue(
            any("2026" in doc and page == 6 for doc, page in docs_and_pages),
            f"Expected Handbook 2026-27 p.6 in hits, got: {docs_and_pages}"
        )

        res = run_agent("how to apply my tc", profile={"regulation": "R23", "degree": "B.Tech"})
        self.assertIn("Ramadevi", res["answer"])
        self.assertIn("1002", res["answer"])

    def test_page_specific_query_resolver(self):
        """'what p.30 is saying ?' must retrieve chunks specifically from page 30."""
        hits = self.retriever.search("what p.30 is saying ?", profile={"regulation": "R23"})
        self.assertTrue(len(hits) > 0)
        self.assertEqual(hits[0].page, 30)
        self.assertIn("WEBOPAC", hits[0].text)

        res = run_agent("what p.30 is saying ?", profile={"regulation": "R23"})
        self.assertIn("R23 Handbook p.30", res.get("citations", []))
        self.assertIn("WEBOPAC", res["answer"])

    def test_hostel_curfew_girls_uses_current_warden(self):
        """Girls hostel curfew/late arrival must cite Ms. S. Shobha Rani and not Ms. Anitha GP."""
        history = [
            {"role": "user", "content": "what if i came to hostel at 12 o clock !"},
            {"role": "assistant", "content": "Do you mean the Boys Hostel or the Girls Hostel?"},
        ]
        res = run_agent("Girls", history=history, profile={"regulation": "R23"})
        ans = res["answer"]
        self.assertIn("Shobha Rani", ans)
        self.assertIn("9701578799", ans)
        self.assertNotIn("Anitha GP", ans)
        self.assertNotIn("9599042878", ans)


if __name__ == "__main__":
    unittest.main()

