"""Deterministic counting for "how many X" questions.

A pre-LLM resolver (same spirit as agent/clarify.py) so exact numbers come from
the handbook itself, not from a model that parrots a list instead of summing.
Only "clubs" is catalogued today; the small catalog lives in _CLUB_WORD so more
countable kinds (societies, sports, facilities) can be added later.

Scope handling:
  * whole university            -> total + per-department breakdown
  * one department / branch     -> that group only, with club names
  * university / department level -> that level only
  * student profile.branch      -> used when the question is scope-less
  * unknown scope               -> one-tap clarify (options), like clarify.py

Regulation-aware: a question naming "R23" counts the R23 handbook's own club
table (Sl.No. rows); otherwise the current handbook's §2.9 section is used.
"""
import os
import re
from functools import lru_cache

from .retriever import DATA, DOC_SOURCES, _ensure_source, load_pages

CURRENT_HANDBOOK = "Handbook 2026-27"
R23_HANDBOOK = "R23 Handbook"

MODE = "count"

# --- intent gates ----------------------------------------------------------
_COUNT_HINT = re.compile(r"\b(?:how many|count|total|number of)\b", re.I)
_CLUB_WORD = re.compile(r"\bclubs?\b", re.I)

_UNI_SCOPE = re.compile(r"\b(?:universit|whole|overall|total|sr university|\bsru\b|campus|listed)\b", re.I)
_LEVEL_UNI = re.compile(r"\buniversity[- ]level\b", re.I)
_LEVEL_DEPT = re.compile(r"\bdepartment[- ]level\b", re.I)

# (regex, canonical dept label). Ordered: first match wins.
DEPT_ALIASES = (
    (re.compile(r"\bmec\w*|\bautomobil\w*\b", re.I), "Mechanical"),
    (re.compile(r"\bcse\b|cs ?& ?ai|computer sci\w*", re.I), "Computer Science and Artificial Intelligence"),
    (re.compile(r"\bai.?ml\b|artificial intelligence|data sci\w*|cyber", re.I), "Computer Science and Artificial Intelligence"),
    (re.compile(r"\beee\b|electrical", re.I), "Electrical and Electronics Engineering"),
    (re.compile(r"\bece\b|electronics|communic\w*", re.I), "Electronics and Communications Engineering"),
    (re.compile(r"\bbusiness\b|mgmt|management|marketing|\bfinance\b|\bhr \b", re.I), "Business Management"),
    (re.compile(r"\bagri\w*\b|\bsoa\b", re.I), "Agriculture"),
    (re.compile(r"\bcivil\b", re.I), "Civil"),
)

# Canonical section dept -> short label used in the answer text.
_DEPT_LABEL = {
    "University Level": "university level",
    "Mechanical": "Mechanical",
    "Computer Science and Artificial Intelligence": "CSE & AI",
    "Electrical and Electronics Engineering": "EEE",
    "Electronics and Communications Engineering": "ECE",
    "Business Management": "Business",
    "Agriculture": "Agriculture",
    "Civil": "Civil",
}

# Section sub-heading -> canonical dept label (some headings differ in wording).
_GROUP_DEPT = {
    "University Level Clubs": "University Level",
    "Mechanical": "Mechanical",
    "Computer Science and Artificial Intelligence": "Computer Science and Artificial Intelligence",
    "Electrical and Electronics Engineering": "Electrical and Electronics Engineering",
    "Electronics and Communications Engineering": "Electronics and Communications Engineering",
    "Business Management": "Business Management",
    "Agriculture": "Agriculture",
    "Civil Engineering": "Civil",
}

_GROUP_RE = re.compile(r"^\s*([A-Z][^:]{2,80}?)\s*:\s*$")
_ENTITY_RE = re.compile(r"^\s*([A-Z][^:]{2,90}?)\s*:\s*(.{8,})")


# --- text sources ----------------------------------------------------------
def _pages_for(label):
    """Raw (page_no, text) pages for a document label, honouring sync pushes."""
    for src in DOC_SOURCES:
        if src.get("label") == label:
            txt = _ensure_source(src)
            if txt:
                return load_pages(txt)
            break
    known = {
        CURRENT_HANDBOOK: os.path.join(DATA, "student_handbook.txt"),
        R23_HANDBOOK: os.path.join(DATA, "r23_btech_20240322.txt"),
    }
    path = known.get(label)
    if path and os.path.exists(path):
        return load_pages(path)
    return []


@lru_cache(maxsize=8)
def _club_items_current():
    """Parse §2.9 of the current handbook into dept-labelled club entries."""
    pages = _pages_for(CURRENT_HANDBOOK)
    if not pages:
        return []

    items, dept, in_dept_group = [], "University Level", False
    started, done = False, False
    for page_no, text in pages:
        if done:
            break
        if not started:
            if "2.9 Student Clubs" not in text:
                continue
            started = True
        for ln in text.splitlines():
            if "2.10" in ln:
                done = True
                break
            s = ln.strip()
            if not s:
                continue
            if s.lower() == "department level clubs":
                in_dept_group = True
                continue
            m = _ENTITY_RE.match(s)
            if m:
                items.append({"dept": dept, "name": m.group(1).strip(), "page": page_no})
                continue
            m = _GROUP_RE.match(s)
            if m:
                g = m.group(1).strip()
                gl = g.lower()
                if "university level clubs" in gl or "department level clubs" in gl:
                    dept = "University Level"
                    in_dept_group = True
                elif in_dept_group and g in _GROUP_DEPT:
                    dept = _GROUP_DEPT[g]
    return items


_R23_ROW = re.compile(r"^\s*(\d{1,3})\s+(.*)$")
_R23_LEVEL = re.compile(r"(University Level|ME|CS&AI|EEE|ECE|Business|SOA|CE)\s*$")
_R23_MAP = {
    "University Level": "University Level",
    "ME": "Mechanical",
    "CS&AI": "Computer Science and Artificial Intelligence",
    "EEE": "Electrical and Electronics Engineering",
    "ECE": "Electronics and Communications Engineering",
    "Business": "Business Management",
    "SOA": "Agriculture",
    "CE": "Civil",
}


@lru_cache(maxsize=8)
def _club_items_r23():
    """Parse the R23 Sl.No. club table (handles wrapped rows)."""
    items, started, done, cur = [], False, False, None
    for page_no, text in _pages_for(R23_HANDBOOK):
        if done:
            break
        for ln in text.splitlines():
            s = ln.strip()
            if not s:
                continue
            if not started:
                if "Sl.No." in s and "Club" in s:
                    started = True
                continue
            if s.lower().startswith("club name description"):
                done = True
                break
            m = _R23_ROW.match(s)
            if m:
                rest = m.group(2)
                lm = _R23_LEVEL.search(rest)
                if lm:
                    items.append(
                        {"dept": _R23_MAP[lm.group(0)],
                         "name": rest[: lm.start()].strip(),
                         "page": page_no}
                    )
                else:
                    cur = {"dept": None, "name": rest, "page": page_no}
            elif cur is not None:
                lm = _R23_LEVEL.search(s)
                if lm:
                    cur["name"] = f"{cur['name']} {s[: lm.start()]}".strip()
                    cur["dept"] = _R23_MAP[lm.group(0)]
                    items.append(cur)
                    cur = None
                else:
                    cur["name"] = f"{cur['name']} {s}".strip()
    return items


@lru_cache(maxsize=4)
def _items_for(label):
    return _club_items_r23() if label == R23_HANDBOOK else _club_items_current()


# --- scope resolution -------------------------------------------------------
def _hints_r23(question):
    return bool(re.search(r"\br23\b", (question or "").lower()))


def _dept_from_question(question):
    q = question or ""
    for pat, label in DEPT_ALIASES:
        if pat.search(q):
            return label
    return None


def _dept_from_profile(profile):
    if not isinstance(profile, dict):
        return None
    branch = str(profile.get("branch") or "").strip()
    return _dept_from_question(branch) if branch else None


# --- answer building --------------------------------------------------------
def _pages_cite(pages):
    pages = sorted(set(pages))
    groups = []
    start = prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
            continue
        groups.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = p
    groups.append(f"{start}-{prev}" if start != prev else str(start))
    return ", ".join(groups)


def _reply(doc, items, answer, pages, scope=None):
    return {
        "answer": answer,
        "citations": sorted({f"{doc} p.{p}" for p in pages}),
        "tool_calls": [],
        "mode": MODE,
        "count_scope": scope,
    }


def _build_answer(doc, items, scope, dept=None, from_profile=False):
    pages = [it["page"] for it in items]
    cite = f"{doc} p.{_pages_cite(pages)}"

    counts = {}
    for it in items:
        counts[it["dept"]] = counts.get(it["dept"], 0) + 1
    uni = counts.get("University Level", 0)
    dept_counts = {k: v for k, v in counts.items() if k != "University Level"}
    dept_total = sum(dept_counts.values())
    total = len(items)

    if scope == "university":
        breakdown = " · ".join(
            f"{_DEPT_LABEL.get(k, k)} {v}" for k, v in sorted(dept_counts.items(), key=lambda x: -x[1])
        )
        ans = (
            f"The handbook lists **{total} student clubs and societies** in total "
            f"— {uni} at university level and {dept_total} at department level. "
            f"By department: {breakdown}. ({cite})"
        )
        return _reply(doc, items, ans, pages, scope)

    if scope == "university-level":
        ans = (
            f"The university-level section lists **{uni} student clubs and societies** "
            f"(including the Community Service Center). ({cite})"
        )
        return _reply(doc, items, ans, pages, scope)

    if scope == "department-level":
        breakdown = " · ".join(
            f"{_DEPT_LABEL.get(k, k)} {v}" for k, v in sorted(dept_counts.items(), key=lambda x: -x[1])
        )
        ans = (
            f"The handbook lists **{dept_total} department-level student clubs** "
            f"(university level has {uni}). By department: {breakdown}. ({cite})"
        )
        return _reply(doc, items, ans, pages, scope)

    if scope == "dept":
        names = [it["name"] for it in items if it["dept"] == dept]
        prefix = f"In your branch ({_DEPT_LABEL.get(dept, dept)}), " if from_profile else ""
        ans = (
            f"{prefix}the handbook lists **{len(names)} student clubs** under "
            f"{_DEPT_LABEL.get(dept, dept)}: {', '.join(names)}. ({cite})"
        )
        return _reply(doc, items, ans[:1].upper() + ans[1:], pages, scope)

    return None


# --- entry point ------------------------------------------------------------
def check(question, history=None, profile=None):
    """Return a `mode: "count"` answer dict, or None to fall through to the LLM."""
    q = (question or "").strip()
    if not q or not _COUNT_HINT.search(q) or not _CLUB_WORD.search(q):
        return None

    label = R23_HANDBOOK if _hints_r23(q) else CURRENT_HANDBOOK
    items = _items_for(label)
    dept_page = {it["page"] for it in items}
    if not items:
        return None

    dept = _dept_from_question(q)
    if dept:
        dept_items = [it for it in items if it["dept"] == dept]
        if not dept_items:
            return _reply(
                label,
                items,
                f"I could not find any clubs listed under {_DEPT_LABEL.get(dept, dept)} "
                f"in the handbook. I can give you the total for the whole university "
                f"or another department. ({label} p.{_pages_cite(dept_page)})",
                dept_page,
                "dept-unknown",
            )
        return _build_answer(label, dept_items, "dept", dept=dept)

    if _LEVEL_UNI.search(q):
        return _build_answer(label, items, "university-level")

    if _LEVEL_DEPT.search(q):
        return _build_answer(label, items, "department-level")

    if _UNI_SCOPE.search(q):
        return _build_answer(label, items, "university")

    profile_dept = _dept_from_profile(profile)
    if profile_dept:
        dept_items = [it for it in items if it["dept"] == profile_dept]
        if dept_items:
            return _build_answer(label, dept_items, "dept", dept=profile_dept, from_profile=True)

    if label == R23_HANDBOOK:
        return _build_answer(label, items, "university")

    return {
        "answer": (
            "Sure! Which do you want me to count — the clubs for the whole university, "
            "or for one department? (Tap an option below.)"
        ),
        "citations": [],
        "tool_calls": [],
        "mode": MODE,
        "options": [
            "How many clubs are there in total?",
            "How many clubs does Mechanical have?",
            "How many clubs does CSE & AI have?",
            "How many clubs does ECE have?",
            "How many clubs does EEE have?",
            "How many clubs does Business have?",
            "How many clubs does Agriculture have?",
            "How many clubs does Civil have?",
        ],
    }