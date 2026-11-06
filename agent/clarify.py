"""Deterministic clarify-then-answer pre-pass (zero LLM cost).

Runs BEFORE any LLM call. When a student enters an unclear, incomplete, or ambiguous
question (e.g. 'I have a problem with attendance', 'What about my grade?', 'Can I write the exam?',
'I have a backlog', 'Boys vs Girls hostel', or programme/branch credit ambiguity):
it returns a structured natural clarification message plus 3-5 clickable one-tap options
instead of guessing or returning broad/irrelevant chunks.

Design:
  * Topic keywords gate the eligible dimensions.
  * A 'specified' check skips any dimension the student already declared.
  * Questions that name a regulation (e.g. 'in R23') or provide specific criteria
    (e.g. 'minimum pass marks', 'letter grade scale', 'condonation fee') skip clarification
    and run through direct RAG retrieval.
  * Multi-turn history is respected so sub-clarifications progress naturally and never ask
    the student to repeat already-provided details.
"""
import os
import re
from functools import lru_cache

from .retriever import DATA, get_retriever, load_pages

MODE = "clarify"

# --- Topic gates ---
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

# --- Ambiguous Umbrella Pattern Detectors ---

# 1. Attendance umbrella
_ATTENDANCE_VAGUE = re.compile(
    r"^(?:(?:i\s+have\s+(?:an?\s+)?(?:problem|issue|doubt|question)\s+(?:with|in|about)\s+)?attendance|"
    r"(?:i\s+have\s+(?:an?\s+)?)?attendance\s+(?:problem|issue|doubt|question|rules?|policy|details?)|"
    r"tell\s+me\s+about\s+attendance|"
    r"what\s+about\s+attendance|"
    r"attendance|"
    r"my\s+attendance\s+(?:is\s+)?(?:low|shortage|problem|issue)|"
    r"attendance\s+shortage)$",
    re.I
)

# 2. Grades & Marks umbrella
_GRADES_VAGUE = re.compile(
    r"^(?:(?:i\s+have\s+(?:an?\s+)?(?:problem|issue|doubt|question)\s+(?:with|in|about)\s+my\s+)?(?:marks|grades?)|"
    r"(?:i\s+have\s+(?:an?\s+)?)?(?:marks|grades?)\s+(?:problem|issue|doubt|question|rules?)|"
    r"what\s+about\s+my\s+grades?|"
    r"tell\s+me\s+about\s+grades?|"
    r"grading\s+rules|"
    r"my\s+grades?|"
    r"my\s+marks)$",
    re.I
)

# 3. Exam eligibility umbrella
_EXAM_VAGUE = re.compile(
    r"^(?:can\s+i\s+(?:write|attend|take)\s+(?:the|my)?\s*exams?|"
    r"am\s+i\s+eligible\s+(?:to\s+(?:write|attend|take)|for)\s+(?:the|my)?\s*exams?|"
    r"exam\s+eligibility|"
    r"examination\s+eligibility)$",
    re.I
)

# 4. Backlogs & Failure umbrella
_BACKLOG_VAGUE = re.compile(
    r"^(?:i\s+have\s+(?:a\s+)?backlogs?(?:\s+what\s+should\s+i\s+do)?|"
    r"what\s+happens\s+if\s+i\s+fail(?:\s+(?:an?\s+)?(?:exam|subject))?|"
    r"i\s+failed(?:\s+in\s+a?\s*subject)?|"
    r"backlog\s+rules?|"
    r"i\s+have\s+backlogs?|"
    r"what\s+if\s+i\s+fail)$",
    re.I
)

# 5. Subjects & Electives umbrella
_SUBJECTS_VAGUE = re.compile(
    r"^(?:i\s+want\s+to\s+know\s+about\s+my\s+subjects|"
    r"tell\s+me\s+about\s+(?:my\s+)?subjects|"
    r"what\s+subjects\s+do\s+i\s+have|"
    r"my\s+subjects|"
    r"tell\s+me\s+about\s+electives)$",
    re.I
)


@lru_cache(maxsize=1)
def _handbook_has_gendered_hostels():
    path = os.path.join(DATA, "student_handbook.txt")
    if not os.path.exists(path):
        return False
    for _, text in load_pages(path):
        low = text.lower()
        if re.search(r"\bboys? hostel\b", low) and re.search(r"\bgirls? hostel\b", low):
            return True
    return False


def _user_text(history, question):
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


def _last_assistant_message(history):
    if not history:
        return ""
    for m in reversed(history):
        if isinstance(m, dict) and m.get("role") == "assistant":
            return str(m.get("content", "")).lower()
    return ""


def check(question, history=None, profile=None):
    """Return a `mode: "clarify"` answer dict, or None when the question is
    unambiguous (or already specified) so the normal agent path runs."""
    q_raw = (question or "").strip()
    q = q_raw.lower()
    if not q:
        return None
    q_clean = re.sub(r"[^a-zA-Z0-9\s%]+", " ", q).strip()

    q_clean = re.sub(r"\s+", " ", q_clean)

    # 1. Questions naming a regulation are disambiguated by doc routing already.
    if get_retriever()._doc_hints(question):
        return None

    ctx = _context_str(question, history, profile)
    last_bot = _last_assistant_message(history)

    # 2. Hostel facet takes precedence for any hostel question lacking gender declaration.
    if HOSTEL_TOPIC.search(q) and not _GENDER.search(ctx):
        if _handbook_has_gendered_hostels():
            return _reply(
                "hostel_gender",
                "Do you mean the Boys Hostel or the Girls Hostel? Hostel rules, "
                "facilities and contact details differ between the two, so which "
                "one are you asking about?",
                ["Boys Hostel", "Girls Hostel"],
            )

    # 3. Specific questions that already declare their concrete requirement must NOT be clarified.
    # Exclude questions asking for specific percentages, scales, formulas, fees, or leadership contacts.
    is_specific_query = bool(re.search(
        r"\b(minimum\s+pass|pass\s+percentage|letter\s+grade\s+scale|who\s+is\s+the|who\s+do\s+i\s+contact|"
        r"anti\s*-?\s*ragging|lost\s+(?:my\s+)?(?:id|identity)|wi-?fi|dress\s+code|"
        r"how\s+is\s+(?:sgpa|cgpa)\s+calculated|cgpa\s+formula|revaluation\s+fee|"
        r"condonation\s+fee|fee\s+refund|what\s+cgpa\s+is\s+needed)\b",
        q
    ))
    if is_specific_query:
        return None

    # -------------------------------------------------------------
    # 3. Multi-turn Sub-level Attendance Clarifications
    # -------------------------------------------------------------
    # If the student says 'My attendance is below 75%' after an attendance thread:
    if re.search(r"\b(below\s*75%?|less\s+than\s*75%?|under\s*75%?|attendance\s+is\s+below\s*75%?)\b", q):
        return _reply(
            "attendance_below_75",
            "Understood. Are you asking whether you are eligible to write your semester examinations, "
            "or do you want to know about attendance condonation rules and application procedure?",
            ["Examination Eligibility", "Attendance Condonation Rules"],
        )

    # If student clarifies with 'condonation' following an attendance clarification:
    if q_clean in ("condonation", "attendance condonation", "condone", "second one", "2nd one") and "attendance" in last_bot:
        return _reply(
            "attendance_condonation_sub",
            "I can help with attendance condonation! Are you asking about the eligibility criteria "
            "(the 65%–75% threshold) or the application procedure (medical certificate and Dean approval)?",
            ["Condonation Eligibility (65-75%)", "Application Procedure & Medical Certificate"],
        )

    # -------------------------------------------------------------
    # 4. First-turn Umbrella Clarifications
    # -------------------------------------------------------------
    # (A) Attendance Umbrella
    if _ATTENDANCE_VAGUE.match(q_clean):
        return _reply(
            "attendance",
            "I can help you with that! Are you trying to understand:\n\n"
            "- Minimum attendance required to write examinations?\n"
            "- What happens if your attendance is below the required percentage (detention)?\n"
            "- Attendance condonation rules (medical / duty leave)?\n"
            "- Attendance calculation for individual subjects or labs?\n\n"
            "Which one are you looking for?",
            [
                "Minimum Attendance (75%)",
                "Attendance Condonation (65-75%)",
                "Detention Rules (<65%)",
                "Subject-wise Attendance",
            ],
        )

    # (B) Grades & Marks Umbrella
    if _GRADES_VAGUE.match(q_clean):
        return _reply(
            "grades",
            "Sure! Are you asking about:\n\n"
            "- Grade points and letter grades (O, A+, A, B+, B, C, F)?\n"
            "- SGPA or CGPA calculation formula?\n"
            "- Supplementary examination grades and attempts?\n"
            "- Revaluation or improvement of grades?\n\n"
            "Please tell me which one you want to understand.",
            [
                "Grade Points & Letter Grades",
                "SGPA / CGPA Calculation",
                "Supplementary Exam Grades",
                "Revaluation & Improvement",
            ],
        )

    # (C) Examination Eligibility Umbrella
    if _EXAM_VAGUE.match(q_clean):
        return _reply(
            "exam_eligibility",
            "Of course, I can help you check your examination eligibility. Are you asking about:\n\n"
            "- Attendance eligibility (minimum percentage required)?\n"
            "- Eligibility after failing a subject (backlog)?\n"
            "- Supplementary examination eligibility and registration?\n"
            "- Hall ticket, attendance condonation, or fee clearance requirements?\n\n"
            "Which one would you like to check?",
            [
                "Attendance Eligibility",
                "Eligibility with Backlogs",
                "Supplementary Exam Eligibility",
                "Hall Ticket & Fee Clearance",
            ],
        )

    # (D) Backlogs Umbrella
    if _BACKLOG_VAGUE.match(q_clean):
        return _reply(
            "backlogs",
            "Don't worry, I can help you understand the rules. Are you looking for information about:\n\n"
            "- How to clear a backlog and supplementary examinations?\n"
            "- Supplementary examination eligibility and schedule?\n"
            "- Number of attempts and maximum duration allowed?\n"
            "- How a backlog affects your SGPA / CGPA?\n"
            "- Whether you can be promoted to the next semester or year?\n\n"
            "Which one would you like to know?",
            [
                "How to Clear Backlogs",
                "Supplementary Exam Rules",
                "Number of Attempts Allowed",
                "Effect on SGPA / CGPA",
                "Promotion to Next Year",
            ],
        )

    # (E) Subjects & Electives Umbrella
    if _SUBJECTS_VAGUE.match(q_clean):
        return _reply(
            "subjects",
            "I can help you with the curriculum and course structure! Are you looking for:\n\n"
            "- Professional Electives vs Open Electives rules?\n"
            "- MOOCs / NPTEL course registration and credit transfer?\n"
            "- Minors and Honors degree requirements?\n"
            "- Course structure and credit requirements for your branch?\n\n"
            "Which one are you asking about?",
            [
                "Professional vs Open Electives",
                "MOOCs / NPTEL Credit Transfer",
                "Minors & Honors Degree",
                "Branch Course Structure",
            ],
        )

    # -------------------------------------------------------------
    # 5. Preserved Branch / Programme Dimension
    # -------------------------------------------------------------
    profile_has_branch = False
    if isinstance(profile, dict):
        if any(profile.get(k) for k in ("degree", "program", "stream", "branch", "programme", "roll_number")):
            profile_has_branch = True

    if BRANCH_TOPIC.search(q) and not _PROGRAMME.search(ctx) and not profile_has_branch:
        if len(_top_programme_labels(question)) >= 2:
            return _reply(
                "branch",
                "Which programme or branch are you in? Rules like graduation "
                "credits and promotion differ between programmes (e.g. B.Tech, "
                "BBA, BCA or B.Sc.). You can also simply share your 10-digit roll number!",
                ["B.Tech", "BBA", "BCA", "B.Sc."],
            )

    return None
