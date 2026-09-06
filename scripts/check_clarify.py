"""No-cost probes for the deterministic clarify layer (agent/clarify.py).

Runs agent/clarify.check() over a fixed question battery and asserts which
dimension (if any) each should clarify. No LLM calls, no API cost.

Usage: python scripts/check_clarify.py     (exit 1 on any mismatch)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent.clarify import check  # noqa: E402

# (args_for_check, expected_facet or None)
CASES = [
    # hostel facet (fires when gender is not declared anywhere)
    (("Who do I contact for a hostel problem?", [], {}), "hostel_gender"),
    (("I have a complaint about my hostel", [], {}), "hostel_gender"),
    (("tell me about hostel timings and mess", [], {}), "hostel_gender"),
    (("can I change my hostel room", [], {}), "hostel_gender"),
    (("hostel curfew for bba students", [], {}), "hostel_gender"),
    # gender already declared -> never ask
    (("hostel fee refund", [{"role": "user", "content": "Girls Hostel"}], {}), None),
    (("boys hostel fee details", [], {}), None),
    (("where is the boys hostel located", [], {}), None),
    # branch facet (only when retrieved chunks mix >=2 programmes)
    (("how many total credits do I need to graduate?", [], {}), "branch"),
    (("what cgpa is needed for promotion", [], {},), None),  # retrieval is single-programme
    # programme already declared (query / profile / history) -> never ask
    (("B.Tech promotion credits required", [], {}), None),
    (("what cgpa for promotion", [], {"programme": "B.Tech", "branch": "CSE"}), None),
    # questions naming a regulation skip clarify (doc routing handles it)
    (("What are professional electives in R23 regulation?", [], {}), None),
    # unrelated / fully answerable questions
    (("what is the minimum pass percentage?", [], {}), None),
    (("Who do I contact for Wi-Fi problems?", [], {}), None),
    (("I lost my identity card", [], {}), None),
    (("explain the letter grade scale", [], {}), None),
    (("what are the anti-ragging rules", [], {}), None),
]


def main():
    fails = 0
    print(f"{'question':46} expected      got")
    print("-" * 84)
    for args, want in CASES:
        result = check(*args)
        got = result and result.get("clarify_facet")
        ok = got == want
        fails += 0 if ok else 1
        mark = "OK " if ok else "FAIL"
        q = args[0][:44]
        print(f"{q:46} {str(want):12} {str(got):12} {mark}")
    passed = len(CASES) - fails
    print("-" * 84)
    print(f"clarify probes passed: {passed}/{len(CASES)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())