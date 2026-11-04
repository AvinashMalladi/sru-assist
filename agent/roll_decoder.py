"""SR University 10-digit Enrollment / Roll Number Decoder.

Official Handbook Reference:
  SR University Student Handbook 2026-27, Section 2.1 "Student Registration
  and University Identity - Enrollment Number Framework" (Page 8):

  "Each student is allotted a unique 10-digit Enrollment Number representing
  the Year of Admission, School Code, Degree Code, Program Code, and serial number.
  Example: For B.Tech CSE -> 2 3 0 3 A 5 1 0 0 1"

Component Breakdown:
  - Digits 1-2: Year of Admission (e.g. "23" -> 2023)
  - Digits 3-4: School Code (e.g. "03" -> School of Computer Science & AI)
  - Digit 5:    Degree Code (e.g. "A" -> B.Tech, "L" -> B.Tech Lateral Entry)
  - Digits 6-7: Program Code (e.g. "51" -> Computer Science & Engineering)
  - Digits 8-10: Serial Number (e.g. "001", "501" for Lateral Entry)

Validation & Bounds:
  - Minimum Valid Admission Year: 2020 (Year SR University was established)
  - Current Academic Year: 2026
  - Maximum Valid Admission Year: 2027 (Upcoming admission cycle)
  - Out-of-bounds years (e.g., 2031) are detected and flagged as FUTURE_YEAR.
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

MIN_VALID_YEAR = 2020
CURRENT_ACADEMIC_YEAR = 2026
MAX_VALID_YEAR = 2027

# Primary SRU 10-digit enrollment pattern (e.g., 2303A51001 or 2403L51001)
ROLL_REGEX_STANDARD = re.compile(
    r"\b(?P<year>\d{2})(?P<school>\d{2})(?P<degree>[A-Za-z])(?P<program>\d{2})(?P<serial>[A-Za-z0-9]{3})\b"
)

# TS ECET / Lateral Entry standard variant (e.g., 24035A0501 where '5' marks Lateral Entry)
ROLL_REGEX_ECET = re.compile(
    r"\b(?P<year>\d{2})(?P<school>\d{2})5(?P<degree>[A-Za-z])(?P<program>\d{2})(?P<serial>[A-Za-z0-9]{2,3})\b"
)

# University Schools as designated in Handbook Section 1.1 (Page 5)
SCHOOL_MAP = {
    "01": "School of Engineering",
    "02": "School of Business",
    "03": "School of Computer Science and Artificial Intelligence",
    "04": "School of Agriculture",
    "05": "School of Sciences and Humanities",
    "06": "School of Design",
}

# Degree Types across SRU Academic Programs
DEGREE_MAP = {
    "A": "B.Tech",
    "L": "B.Tech (Lateral Entry)",
    "B": "BBA",
    "C": "BCA",
    "S": "B.Sc. (Hons.) Agriculture",
    "D": "B.Des",
    "M": "M.Tech / MBA / M.Sc.",
    "P": "Ph.D.",
}

# Program / Stream Identifiers
PROGRAM_MAP = {
    # Engineering / CSAI Streams
    "51": "Computer Science and Engineering (CSE)",
    "52": "Computer Science & AI / ML",
    "53": "Data Science",
    "54": "Cyber Security",
    "01": "Civil Engineering",
    "02": "Electrical and Electronics Engineering (EEE)",
    "03": "Electrical Engineering",
    "04": "Electronics and Communication Engineering (ECE)",
    "05": "Electronics & Communication Engineering",
    "06": "Mechanical Engineering",
    # Business / Agriculture / Science Streams
    "11": "General Management (BBA)",
    "12": "Business Analytics",
    "71": "Agricultural Sciences",
    "72": "B.Sc. (Hons.) Agriculture",
}


def _check_corpus_for_regulation(reg_name: str) -> bool:
    """Check if a dedicated PDF exists in data/ for this regulation cohort (e.g. R24, R25)."""
    if not os.path.exists(DATA_DIR):
        return False
    pattern = os.path.join(DATA_DIR, f"*{reg_name.lower()}*.pdf")
    return len(glob.glob(pattern)) > 0


def parse_roll_number(text: str):
    """Extracts, decodes, and validates an SRU enrollment number from text.

    Returns:
        dict with decoded metadata and validation flags, or None if no roll number is found.
    """
    if not text:
        return None

    is_ecet_format = False
    match = ROLL_REGEX_STANDARD.search(text)
    if not match:
        match = ROLL_REGEX_ECET.search(text)
        if match:
            is_ecet_format = True
        else:
            return None

    raw_roll = match.group(0).upper()
    yr_digits = match.group("year")
    school_code = match.group("school")
    degree_code = match.group("degree").upper()
    prog_code = match.group("program")
    serial_str = match.group("serial").upper()

    admission_year = int("20" + yr_digits)

    # 1. Validate Admission Year Bounds
    is_valid = True
    validation_status = "VALID"
    validation_error = None

    if admission_year > MAX_VALID_YEAR:
        is_valid = False
        validation_status = "FUTURE_YEAR"
        validation_error = (
            f"Roll number indicates admission year {admission_year}, which is in the future. "
            f"Active student cohorts are currently between {MIN_VALID_YEAR} and {CURRENT_ACADEMIC_YEAR}."
        )
    elif admission_year < MIN_VALID_YEAR:
        is_valid = False
        validation_status = "PRE_UNIVERSITY_YEAR"
        validation_error = (
            f"Roll number indicates admission year {admission_year}. SR University degree enrollment "
            f"numbers began in {MIN_VALID_YEAR}. Earlier batches follow legacy autonomous college regulations not indexed in AURA."
        )

    # 2. Validate School and Degree Codes
    if is_valid:
        if school_code not in SCHOOL_MAP:
            is_valid = False
            validation_status = "UNKNOWN_SCHOOL"
            validation_error = f"School code '{school_code}' is not an active SR University school identifier."
        elif degree_code not in DEGREE_MAP:
            is_valid = False
            validation_status = "UNKNOWN_DEGREE"
            validation_error = f"Degree code '{degree_code}' is not a recognized SR University degree code."

    # 3. Detect Lateral Entry Status
    # Lateral Entry criteria:
    #   a) Degree code explicitly 'L' (e.g. 2403L51001)
    #   b) TS ECET pattern with '5' indicator (e.g. 24035A0501)
    #   c) Serial in lateral entry ranges (500-599, 800-899, L01-L99)
    is_lateral = (
        degree_code == "L"
        or is_ecet_format
        or serial_str.startswith(("5", "8", "L"))
    )

    if is_lateral:
        entry_type = "Lateral Entry"
        degree_name = "B.Tech (Lateral Entry)" if degree_code in ("A", "L") else f"{DEGREE_MAP.get(degree_code, 'Degree')} (Lateral Entry)"
        normal_duration = "3 years (6 semesters)"
        max_duration = "6 years (12 semesters)"
        prescribed_credits = "110–130 credits (exempt from 1st-year 30–40 credits; Handbook 2026-27 p. 19 / R23 p. 59, 91)"
        promotion_summary = "Admitted directly into Semester III (2nd Year). 1st-to-2nd year promotion does not apply; governed by Clause (b) criteria from 2nd year onwards."
    else:
        entry_type = "Regular"
        degree_name = DEGREE_MAP.get(degree_code, f"Degree Code {degree_code}")
        normal_duration = "4 years (8 semesters)"
        max_duration = "8 years (16 semesters)"
        prescribed_credits = "160 credits (Handbook 2026-27 p. 19 / R23 p. 59)"
        promotion_summary = "Standard 4-year progression with 1st-year, 2nd-year, and 3rd-year promotion credit checkpoints."

    school_name = SCHOOL_MAP.get(school_code, f"School Code {school_code}")
    program_name = PROGRAM_MAP.get(prog_code, f"Program Code {prog_code}")

    # 4. Resolve Regulation Cohort & Check Handbook Existence in Corpus
    disclaimer = None
    if 2020 <= admission_year <= 2022:
        # Pre-R23 batches (R20 regulation cohort)
        has_r20_pdf = _check_corpus_for_regulation("R20")
        if has_r20_pdf:
            regulation = "R20"
            handbook_doc = "R20 Handbook"
            has_dedicated_handbook = True
        else:
            regulation = "R20 (2020–2022 Cohort)"
            handbook_doc = "R23 Handbook"
            has_dedicated_handbook = False
            disclaimer = (
                "Note: Your roll number corresponds to the 2020–2022 cohort (R20 regulation). "
                "Core academic regulations (attendance, condonation, grading scale) are answered using the approved baseline framework. "
                "For legacy R20 curriculum backlog clearance and specific course equivalences, please verify on SRAAP portal."
            )
    elif admission_year in (2023, 2024):
        # 2023 and 2024 batches share the exact same R23 academic regulations
        regulation = "R23" if admission_year == 2023 else "R24 (R23 Framework)"
        handbook_doc = "R23 Handbook"
        has_dedicated_handbook = True
        disclaimer = None
    elif admission_year == 2025:
        # 2025 batch: check for R25 handbook
        has_r25_pdf = _check_corpus_for_regulation("R25")
        if has_r25_pdf:
            regulation = "R25"
            handbook_doc = "R25 Handbook"
            has_dedicated_handbook = True
            disclaimer = None
        else:
            regulation = "R25 (Governed by University Academic Framework / 2026-27)"
            handbook_doc = "Handbook 2026-27"
            has_dedicated_handbook = False
            disclaimer = (
                "Note: The standalone R25 syllabus booklet is not yet indexed in AURA. "
                "Answers are provided based on the approved University Academic Framework (Handbook 2026-27)."
            )
    else:
        regulation = "2026-27 Regulation"
        handbook_doc = "Handbook 2026-27"
        has_dedicated_handbook = True
        disclaimer = None

    # Friendly branch shorthand
    if "CSE" in program_name or prog_code in ("51", "52", "53", "54"):
        stream_short = "CSE"
    elif "ECE" in program_name or prog_code in ("04", "05"):
        stream_short = "ECE"
    elif "EEE" in program_name or prog_code in ("02", "03"):
        stream_short = "EEE"
    elif "Civil" in program_name or prog_code == "01":
        stream_short = "Civil"
    elif "Mechanical" in program_name or prog_code == "06":
        stream_short = "Mechanical"
    elif "Agriculture" in program_name or degree_code == "S" or school_code == "04":
        stream_short = "Agriculture"
    elif degree_code == "B":
        stream_short = "BBA"
    elif degree_code == "C":
        stream_short = "BCA"
    else:
        stream_short = program_name

    return {
        "roll_number": raw_roll,
        "year": str(admission_year),
        "admission_year": admission_year,
        "batch": f"{admission_year}–{str(admission_year + (3 if is_lateral else 4))[-2:]}",
        "entry_type": entry_type,
        "is_lateral_entry": is_lateral,
        "is_valid": is_valid,
        "validation_status": validation_status,
        "validation_error": validation_error,
        "regulation": regulation,
        "handbook_doc": handbook_doc,
        "has_dedicated_handbook": has_dedicated_handbook,
        "regulation_disclaimer": disclaimer,
        "school": school_name,
        "school_code": school_code,
        "degree": degree_name,
        "degree_code": degree_code,
        "program": program_name,
        "program_code": prog_code,
        "stream": stream_short,
        "serial": serial_str,
        "normal_duration": normal_duration,
        "max_duration": max_duration,
        "prescribed_credits": prescribed_credits,
        "promotion_summary": promotion_summary,
    }


def format_student_badge(profile: dict) -> str:
    """Formats a concise student identity banner."""
    if not profile:
        return ""
    deg = profile.get("degree", "Student")
    stream = profile.get("stream", "")
    reg = profile.get("regulation", "")
    roll = profile.get("roll_number", "")
    entry = " [Lateral Entry]" if profile.get("is_lateral_entry") else ""
    return f"{deg} {stream}{entry} ({reg}) · Roll {roll}"
