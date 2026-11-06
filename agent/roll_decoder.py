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

Dynamic Formula & Validation:
  - Academic batch is calculated dynamically: Admission Year to (Admission Year + Degree Duration).
    e.g., B.Tech 4-yr: 2023 -> Batch 2023–2027 (R23).
  - Degree Duration: B.Tech (4 yrs), Lateral Entry (3 yrs), BBA/BCA (3 yrs), M.Tech/MBA (2 yrs).
  - Minimum Valid Admission Year: 2020 (Year SR University was established).
  - Current Academic Year: Dynamically determined from university calendar.
  - Future admission cohorts without published regulations are declined gracefully.
"""
import datetime
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

MIN_VALID_YEAR = 2020

# Standard degree duration in academic years
DEGREE_DURATION_MAP = {
    "A": 4,  # B.Tech
    "L": 3,  # B.Tech Lateral Entry
    "B": 3,  # BBA
    "C": 3,  # BCA
    "S": 4,  # B.Sc. (Hons.) Agriculture
    "D": 4,  # B.Des
    "M": 2,  # M.Tech / MBA / M.Sc.
    "P": 4,  # Ph.D.
}


def get_current_academic_year() -> int:
    """Returns the current university academic calendar reference year (minimum 2026)."""
    now = datetime.datetime.now()
    return max(2026, now.year)

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
    current_academic_year = get_current_academic_year()

    # 1. Detect Lateral Entry Status
    # Lateral Entry criteria:
    #   a) Degree code explicitly 'L' (e.g. 2403L51001)
    #   b) TS ECET pattern with '5' indicator (e.g. 24035A0501)
    #   c) Serial in lateral entry ranges (500-599, 800-899, L01-L99)
    is_lateral = (
        degree_code == "L"
        or is_ecet_format
        or serial_str.startswith(("5", "8", "L"))
    )

    # 2. Dynamic Degree & Batch Calculation Formula
    # Base duration for degree
    base_degree_duration = 4 if degree_code in ("A", "L", "S", "D") else DEGREE_DURATION_MAP.get(degree_code, 4)
    # If lateral entry, student joins 2nd year (exempt from 1st year), so remaining duration is base - 1
    duration_years = (base_degree_duration - 1) if is_lateral else base_degree_duration
    graduation_year = admission_year + duration_years
    batch_str = f"{admission_year}–{str(graduation_year)[-2:]}"
    batch_full = f"{admission_year}–{graduation_year}"

    # Calculate Academic Study Standing / Year
    if admission_year > current_academic_year:
        study_status = "Prospective / Future Cohort"
        study_year = None
        is_alumnus = False
    elif current_academic_year > graduation_year:
        study_status = f"Alumni (Graduated Batch {batch_str})"
        study_year = None
        is_alumnus = True
    else:
        # Academic year of study in program (e.g. 2nd year admitted for lateral entry)
        max_program_year = base_degree_duration
        computed_yr = (current_academic_year - admission_year) + (2 if is_lateral else 1)
        computed_yr = min(computed_yr, max_program_year)
        study_year = computed_yr
        ordinal_map = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}
        study_status = f"{ordinal_map.get(computed_yr, str(computed_yr))} Year"
        is_alumnus = False

    # 3. Validate Admission Year Bounds & Future Cohort Availability
    is_valid = True
    validation_status = "VALID"
    validation_error = None

    if admission_year < MIN_VALID_YEAR:
        is_valid = False
        validation_status = "PRE_UNIVERSITY_YEAR"
        validation_error = (
            f"Roll number indicates admission year {admission_year}. SR University degree enrollment "
            f"numbers began in {MIN_VALID_YEAR}. Earlier batches follow legacy autonomous college regulations not indexed in AURA."
        )
    elif admission_year > current_academic_year:
        # Check if an official handbook exists for this future regulation (e.g. R27, R28)
        future_reg_code = f"R{yr_digits}"
        if not _check_corpus_for_regulation(future_reg_code):
            is_valid = False
            validation_status = "FUTURE_YEAR"
            validation_error = (
                f"Roll number indicates admission year {admission_year} (Regulation {future_reg_code}, Batch {batch_full}), which is in the future. "
                f"Official academic regulations and curriculum for the {admission_year} cohort have not yet been released "
                f"by SR University. AURA's indexed regulations currently cover active cohorts up to {current_academic_year} (R26)."
            )

    # 4. Validate School and Degree Codes
    if is_valid:
        if school_code not in SCHOOL_MAP:
            is_valid = False
            validation_status = "UNKNOWN_SCHOOL"
            validation_error = f"School code '{school_code}' is not an active SR University school identifier."
        elif degree_code not in DEGREE_MAP:
            is_valid = False
            validation_status = "UNKNOWN_DEGREE"
            validation_error = f"Degree code '{degree_code}' is not a recognized SR University degree code."

    base_deg_name = DEGREE_MAP.get(degree_code, f"Degree Code {degree_code}")
    if is_lateral:
        entry_type = "Lateral Entry"
        if degree_code in ("A", "L"):
            degree_name = "B.Tech (Lateral Entry)"
            prescribed_credits = "110–130 credits (exempt from 1st-year 30–40 credits; Handbook 2026-27 p. 19 / R23 p. 59, 91)"
        elif degree_code in ("B", "C"):
            degree_name = f"{base_deg_name} (Lateral Entry)"
            prescribed_credits = "80–90 credits (exempt from 1st-year ~30 credits; 2-year lateral progression)"
        elif degree_code == "D":
            degree_name = "B.Des (Lateral Entry)"
            prescribed_credits = "110–130 credits (exempt from 1st-year 30–40 credits; 3-year lateral progression)"
        else:
            degree_name = f"{base_deg_name} (Lateral Entry)"
            prescribed_credits = "Lateral Entry curriculum credit requirements (exempt from 1st-year credits)"

        normal_duration = f"{duration_years} years ({duration_years * 2} semesters)"
        max_duration = f"{duration_years * 2} years ({duration_years * 4} semesters)"
        promotion_summary = (
            "Admitted directly into Semester III (2nd Year). 1st-to-2nd year promotion does not apply; "
            "governed by 2nd year onwards promotion criteria."
        )
    else:
        entry_type = "Regular"
        degree_name = base_deg_name
        normal_duration = f"{duration_years} years ({duration_years * 2} semesters)"
        max_duration = f"{duration_years * 2} years ({duration_years * 4} semesters)"
        if degree_code in ("A", "S", "D"):
            prescribed_credits = "160 credits (Handbook 2026-27 p. 19 / R23 p. 59)"
        elif degree_code in ("B", "C"):
            prescribed_credits = "120 credits (3-year degree curriculum)"
        elif degree_code == "M":
            prescribed_credits = "80 credits (2-year postgraduate curriculum)"
        else:
            prescribed_credits = "Prescribed degree curriculum credits"

        promotion_summary = f"Standard {duration_years}-year progression with annual promotion credit checkpoints."

    school_name = SCHOOL_MAP.get(school_code, f"School Code {school_code}")
    program_name = PROGRAM_MAP.get(prog_code, f"Program Code {prog_code}")

    # 5. Resolve Regulation Cohort & Check Handbook Existence in Corpus
    # CRITICAL: Lateral Entry students join directly into Year 2 (Semester III).
    # Therefore, they study under the regulation of the cohort admitted 1 year earlier!
    # e.g., A lateral student admitted in 2024 (2403L...) joins the 2023 cohort and studies under R23.
    cohort_year = (admission_year - 1) if is_lateral else admission_year

    disclaimer = None
    if 2020 <= cohort_year <= 2022:
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
                "Note: Your cohort corresponds to the 2020–2022 regulation framework (R20). "
                "Core academic regulations (attendance, condonation, grading scale) are answered using the approved baseline framework. "
                "For legacy R20 curriculum backlog clearance and specific course equivalences, please verify on SRAAP portal."
            )
    elif cohort_year in (2023, 2024):
        # 2023 and 2024 batches share the R23/R24 framework
        has_r24_pdf = _check_corpus_for_regulation("R24")
        if cohort_year == 2024 and has_r24_pdf:
            regulation = "R24"
            handbook_doc = "R24 Handbook"
            has_dedicated_handbook = True
            disclaimer = None
        else:
            regulation = "R23" if cohort_year == 2023 else "R24 (R23 Framework)"
            handbook_doc = "R23 Handbook"
            has_dedicated_handbook = True
            disclaimer = None
    elif cohort_year == 2025:
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
        "batch": batch_str,
        "batch_full": batch_full,
        "duration_years": duration_years,
        "graduation_year": graduation_year,
        "study_status": study_status,
        "study_year": study_year,
        "is_alumnus": is_alumnus,
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
    status = f" · {profile['study_status']}" if profile.get("study_status") and not profile.get("study_status").startswith("Prospective") else ""
    return f"{deg} {stream}{entry} ({reg}){status} · Roll {roll}"
