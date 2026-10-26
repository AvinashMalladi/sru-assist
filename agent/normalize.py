"""Student Slang, Shortcuts & Typo Normalizer for SRU Assist.

Handles:
  1. Shortcuts & Abbreviations: 'att', 'midsem', 'supply', 'reval', 'condo', 'halltkt', 'pe', 'oe', 'cgpa'
  2. Common Student Spelling Errors: 'attendence', 'hostle', 'invigilater', 'malpractise', 'scholorship'
  3. Regional / Vernacular Terminology: 'dabbulu', 'fail ayya', 'chits', 'slips'
  4. Word-boundary replacements to prevent accidental substring corruption
"""
import re

# Direct word replacements (Word boundary enforced)
STUDENT_TYPO_MAP = {
    # Attendance & Condonation
    r"\b(att|attnd|attendence|attandance|attenance|attendace)\b": "attendance",
    r"\b(condo|condonashun|condonation fee)\b": "condonation medical grounds",
    r"\b(short attendance|less attendance|attendance shortage)\b": "attendance shortage condonation 65 percentage",
    r"\b(detain|detentn|detaintion)\b": "detained detention promotion criteria",

    # Exams, Semesters & Backlogs
    r"\b(midsem|mid-sem|mis-exam|mid exam|mid-term|midterm)\b": "mid semester examination",
    r"\b(endsem|end-sem|sem exam|finals|semester exam)\b": "semester end examination",
    r"\b(supply|suppli|suplimentary|suplementary|supply exam)\b": "supplementary backlog examination",
    r"\b(backlog|backlogs|arrear|arrears)\b": "backlog courses failed F grade",
    r"\b(reval|reeval|re-eval|re-evaluation|revaluation|paper checking)\b": "revaluation answer script verification",
    r"\b(halltkt|hall ticket|hall-ticket|admit card|exam hall ticket)\b": "hall ticket examination admit card",
    r"\b(fail ayya|fail ayanu|failed)\b": "failed course backlog F grade",

    # Cheating / Malpractice / CPAM
    r"\b(chit|chits|slip|slips)\b": "slips chits unfair means malpractice invigilator CPAM",
    r"\b(cheating|copying|malpractise|malpractice)\b": "malpractice unfair means invigilator CPAM disciplinary action",
    r"\b(invigilater|invegilator|invigilator)\b": "invigilator seize answer script statement",

    # Hostels, Facilities & Campus
    r"\b(hostle|hotstel|hostel)\b": "hostel accommodation",
    r"\b(raging|ragin|ragging)\b": "ragging anti-ragging cell disciplinary action",
    r"\b(scholorship|schlrshp|scholarship|fe concession)\b": "scholarship fee concession",
    r"\b(lib|librari|libray)\b": "central library books",
    r"\b(trnsprt|colg bus|college bus|bus pass)\b": "transport bus pass registration",
    r"\b(dabbulu|entha fee|challan|tution fee)\b": "fee payment tuition fee",
    r"\b(id card|id-card|identy card|identity card)\b": "university identity card ID card duplicate",
    r"\b(wifi|wi-fi|net problem|internet down)\b": "wifi internet wireless network issue",

    # Curriculum & Electives
    r"\b(cg|cgpa|gpa|sg|sgpa)\b": "grade point average CGPA SGPA",
    r"\b(pe|prof elective|dept elective)\b": "professional elective",
    r"\b(oe|open elective|interdisciplinary elective)\b": "open elective",
}

COMPILED_TYPO_RULES = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in STUDENT_TYPO_MAP.items()
]


def normalize_student_text(text: str) -> str:
    """Normalizes student slang, shortcuts, and typos into standard handbook terminology."""
    if not text:
        return ""

    normalized = text.strip()
    for pattern, replacement in COMPILED_TYPO_RULES:
        normalized = pattern.sub(replacement, normalized)

    # Clean up multi-spaces created during replacements
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized

