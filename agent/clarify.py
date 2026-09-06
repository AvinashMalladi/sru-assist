"""Deterministic clarify-then-answer pre-pass (zero LLM cost).

Runs BEFORE any LLM call. When a question is ambiguous on a dimension that the
handbook itself splits — Boys vs Girls hostel (rules/contacts/fees differ) and
programme/branch (graduation credits/promotion differ) — it returns a short
question plus one-tap options instead of letting the model guess and surface
the *other* side's info (e.g. giving the Boys hostel manager to a girl, or
applying a B.Tech rule to a B.Sc. student).

Design:
  * Topic keywords gate the eligible dimensions.
  * A "specified" check (query + recent user history + student profile) skips
    any dimension the student already declared.
  * Questions that name a regulation (e.g. "in R23") are skipped entirely —
    intent-based doc routing already disambiguates that axis.
  * The hostel facet is backed by a document-level fact (the handbook genuinely
    contains both a Boys and a Girls hostel), so it triggers regardless of how
    well BM25 happens to phrase-match the exact question.
  * The branch facet only fires when the retrieved chunks for THIS question
    actually mix >= 2 distinct programme labels — otherwise it stays silent and
    the prompt-level clarify rule (agent/prompts.py) covers the rest.
"""
import os
import re
from functools import lru_cache

from .retriever import DATA, get_retriever, load_pages

MODE = "clarify"

HOSTEL_TOPIC = re.compile(
    r"\b(hostel|dorm|dining|mess|accommodation|warden|hostel fee|room)\b"
)
BRANCH_TOPIC = re.compile(
    r"\b(promotion|cgpa|sgpa|gpa|grading|grade scale|attendance|condonation|"
    r"elective|electives|credits|graduation|degree|fees?|registration|minor|"
    r"honors?|scholarship)\b"
)
_PROGRAMME = re.compile(
    r"\bb\.?tech\b|\bbba\b|\bbca\b|b\.?\s?sc\.?|m\.?\s?tech|\bdiploma\b|"
    r"\b(ug|pg)\b|\bcse\b|\bece\b|\beee\b|mech\w*|\bcivil\b|ai.?ml|aiml|"
    r"data.?science"
)
_GENDER = re.compile(r"\b(boys?|girls?)\b|bh-\d|gh-\d")

_PROG_PATTERNS = (
    (r"\bb\.?\s?tech\b", "B.Tech"),
    (r"\bbba\b", "BBA"),
    (r"\bbca\b", "BCA"),
    (r"\bb\.?\s?sc\.?\b", "B.Sc."),
    (r"\bm\.?\s?tech\b", "M.Tech"),
    (r"\bdiploma\b", "Diploma"),
)


@lru_cache(maxsize=1)
def _handbook_has_gendered_hostels():
    """Document-level fact: the handbook carries both a Boys and a Girls hostel.

    Cached per process. Uses this fact so the clarification does not depend on
    how well BM25 happens to phrase-match the exact question.
    """
    path = os.path.join(DATA, "student_handbook.txt")
    if not os.path.exists(path):
        return False
    for _, text in load_pages(path):
        low = text.lower()
        if re.search(r"\bboys? hostel\b", low) and re.search(r"\bgirls? hostel\b", low):
            return True
    return False


def _user_text(history, question):
    """Query + recent student (user-role) messages only.

    Assistant messages are ignored on purpose: a previous clarify answer like
    'Boys or Girls?' contains BOTH labels and would otherwise look specified.
    """
    parts = [question or ""]
    for m in history or []:
        if isinstance(m, dict) and m.get("role") == "user":
            parts.append(m.get("content") or "")
    return " ".join(parts).lower()


def _context_str(question, history, profile):
    parts = [_user_text(history, question)]
    if isinstance(profile, dict):
        parts.append(" ".join(str(v) for v in profile.values()))
    return " ".join(parts).lower()


def _top_programme_labels(question, k=6):
    """Distinct programme labels present in the top-k retrieved chunks."""
    text = " ".join(h.text.lower() for h in get_retriever().search(question, top_k=k))
    return {name for pat, name in _PROG_PATTERNS if re.search(pat, text)}


def _reply(facet, text, options):
    return {
        "answer": text,
        "citations": [],
        "tool_calls": [],
        "mode": MODE,
        "options": options,
        "clarify_facet": facet,
    }


def check(question, history=None, profile=None):
    """Return a `mode: "clarify"` answer dict, or None when the question is
    unambiguous (or already specified) so the normal agent path runs."""
    q = (question or "").strip().lower()
    if not q:
        return None

    # Questions naming a regulation are disambiguated by doc routing already.
    if get_retriever()._doc_hints(question):
        return None

    ctx = _context_str(question, history, profile)

    if HOSTEL_TOPIC.search(q) and not _GENDER.search(ctx):
        if _handbook_has_gendered_hostels():
            return _reply(
                "hostel_gender",
                "Do you mean the Boys Hostel or the Girls Hostel? Hostel rules, "
                "facilities and contact details differ between the two, so which "
                "one are you asking about?",
                ["Boys Hostel", "Girls Hostel"],
            )

    if BRANCH_TOPIC.search(q) and not _PROGRAMME.search(ctx):
        if len(_top_programme_labels(question)) >= 2:
            return _reply(
                "branch",
                "Which programme or branch are you in? Rules like graduation "
                "credits and promotion differ between programmes (e.g. B.Tech, "
                "BBA, BCA or B.Sc.).",
                ["B.Tech", "BBA", "BCA", "B.Sc."],
            )

    return None