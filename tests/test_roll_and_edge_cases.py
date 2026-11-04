"""Unit tests for Roll Number Validation, Lateral Entry, and Regulation Cohort Edge Cases.

Verifies:
1. Out-of-bounds future year roll numbers (e.g. 3103A52313 -> FUTURE_YEAR).
2. Pre-university year roll numbers (e.g. 1503A51001 -> PRE_UNIVERSITY_YEAR).
3. Invalid school/degree codes (e.g. 2399Z99001 -> UNKNOWN_SCHOOL).
4. Lateral entry degree code 'L' (e.g. 2403L51001).
5. TS ECET lateral entry format with '5' (e.g. 24035A0501).
6. Lateral entry serial numbering (e.g. 2303A51501).
7. Missing regulation disclaimer (R24).
8. Auto-discovered regulation presence (R25).
9. Agent handling of invalid roll numbers and lateral entry queries.
"""

import unittest

from agent.core import run_agent
from agent.roll_decoder import parse_roll_number


class TestRollAndEdgeCases(unittest.TestCase):
    def test_future_year_rejection(self):
        """Roll number with future year (e.g. 2031) must be rejected."""
        res = parse_roll_number("3103A52313")
        self.assertIsNotNone(res)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["validation_status"], "FUTURE_YEAR")
        self.assertIn("in the future", res["validation_error"])

        # In run_agent, it must trigger mode 'invalid_roll_number'
        resp = run_agent("3103A52313")
        self.assertEqual(resp.get("mode"), "invalid_roll_number")
        self.assertIn("could not be validated", resp.get("answer", ""))
        self.assertIn("2031", resp.get("answer", ""))

    def test_pre_university_year_rejection(self):
        """Roll number with year prior to SRU establishment (e.g. 2015) must be rejected."""
        res = parse_roll_number("1503A51001")
        self.assertIsNotNone(res)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["validation_status"], "PRE_UNIVERSITY_YEAR")
        self.assertIn("began in 2020", res["validation_error"])

        resp = run_agent("1503A51001")
        self.assertEqual(resp.get("mode"), "invalid_roll_number")

    def test_invalid_school_rejection(self):
        """Roll number with unlisted school code (e.g. 99) must be rejected."""
        res = parse_roll_number("2399A51001")
        self.assertIsNotNone(res)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["validation_status"], "UNKNOWN_SCHOOL")

    def test_lateral_entry_degree_code_l(self):
        """Degree code 'L' must be decoded as B.Tech (Lateral Entry)."""
        res = parse_roll_number("2403L51001")
        self.assertIsNotNone(res)
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["is_lateral_entry"])
        self.assertEqual(res["entry_type"], "Lateral Entry")
        self.assertEqual(res["degree"], "B.Tech (Lateral Entry)")
        self.assertIn("110–130 credits", res["prescribed_credits"])

        # Agent identify
        resp = run_agent("2403L51001")
        self.assertEqual(resp.get("mode"), "profile_identified")
        self.assertIn("Lateral Entry", resp.get("answer", ""))
        self.assertIn("110–130 credits", resp.get("answer", ""))

    def test_lateral_entry_ts_ecet_format(self):
        """TS ECET format (e.g. 24035A0501) must be parsed as Lateral Entry."""
        res = parse_roll_number("24035A0501")
        self.assertIsNotNone(res)
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["is_lateral_entry"])
        self.assertEqual(res["entry_type"], "Lateral Entry")

    def test_lateral_entry_serial_range(self):
        """Serial numbers starting with 5 (e.g. 501) must mark Lateral Entry."""
        res = parse_roll_number("2303A51501")
        self.assertIsNotNone(res)
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["is_lateral_entry"])

    def test_r24_uses_r23_framework(self):
        """R24 (sharing R23 framework) must map to R23 Handbook with has_dedicated_handbook True."""
        res = parse_roll_number("2403A51001")
        self.assertIsNotNone(res)
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["has_dedicated_handbook"])
        self.assertEqual(res["handbook_doc"], "R23 Handbook")
        self.assertIsNone(res["regulation_disclaimer"])

    def test_r20_cohort_mapping(self):
        """2020-2022 batches must map to R20 cohort."""
        res = parse_roll_number("2101A04008")
        self.assertIsNotNone(res)
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["regulation"], "R20 (2020–2022 Cohort)")
        self.assertIn("R20", res["regulation_disclaimer"])

    def test_discovered_regulation_r25(self):
        """R25 (with R25_BTECH_20260808.pdf present) must have dedicated handbook flag True."""
        res = parse_roll_number("2503A51001")
        self.assertIsNotNone(res)
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["has_dedicated_handbook"])
        self.assertEqual(res["handbook_doc"], "R25 Handbook")
        self.assertIsNone(res["regulation_disclaimer"])


if __name__ == "__main__":
    unittest.main()

