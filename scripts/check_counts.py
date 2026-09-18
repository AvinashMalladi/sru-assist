"""No-cost probes for the deterministic count layer (agent/counts.py).

Runs agent/counts.check() over a fixed question battery and prints the exact
answers plus the raw parsed table, so the numbers can be eyeballed against the
handbook. No LLM calls, no API cost.

Usage: python scripts/check_counts.py     (exit 1 on any unexpected None)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent.counts import (
    CURRENT_HANDBOOK,
    R23_HANDBOOK,
    check,
    _club_items_current,
    _club_items_r23,
)


def main():
    current = _club_items_current()
    r23 = _club_items_r23()

    print("== Handbook 2026-27 §2.9 (parsed) ==")
    by_dept = {}
    for it in current:
        by_dept.setdefault(it["dept"], []).append(it["name"])
    total = 0
    for dept, names in by_dept.items():
        print(f"  {dept}: {len(names)}  -> {names}")
        total += len(names)
    print(f"  TOTAL parsed = {total}")
    print(f"  pages = {sorted({it['page'] for it in current})}")

    print("\n== R23 club table (parsed) ==")
    by_dept = {}
    for it in r23:
        by_dept.setdefault(it["dept"], []).append(it["name"])
    total = 0
    for dept, names in by_dept.items():
        print(f"  {dept}: {len(names)}  -> {names}")
        total += len(names)
    print(f"  TOTAL parsed = {total}")
    print(f"  pages = {sorted({it['page'] for it in r23})}")

    questions = [
        "how many clubs are there in total?",
        "total no.of clubs in the university",
        "how many clubs does Mechanical have?",
        "count of clubs in ECE",
        "how many university-level clubs are there?",
        "how many department-level clubs are there?",
        "how many clubs does Civil have?",
        "how many clubs are there?",  # ambiguous -> clarify options
        ("how many clubs are there?", [], {"branch": "CSE"}),  # profile-driven
        "How many clubs are listed in R23 regulation?",
        "how many clubs does Business have in R23?",
    ]
    print("\n== check() answers ==")
    fails = 0
    for item in questions:
        if isinstance(item, tuple):
            q, hist, prof = item
            args, note = (q, hist, prof), q
        else:
            q, args, note = item, (item, [], {}), item
        result = check(*args)
        if result is None:
            fails += 1
            print(f"  !! None  for: {note}")
            continue
        print(f"\n  Q: {note}")
        print(f"  A: {result['answer']}")
        if result.get("citations"):
            print(f"  C: {result['citations']}")
        if result.get("options"):
            print(f"  OPTIONS: {result['options']}")

    print("\n" + "-" * 60)
    print(f"count probes: {'PASS' if fails == 0 else f'{fails} FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())