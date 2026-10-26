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
  - Digit 5:    Degree Code (e.g. "A" -> B.Tech)
  - Digits 6-7: Program Code (e.g. "51" -> Computer Science & Engineering)
  - Digits 8-10: Serial Number (e.g. "001")
"""
import re

ROLL_REGEX = re.compile(
    r"\b(?P<year>\d{2})(?P<school>\d{2})(?P<degree>[A-Za-z])(?P<program>\d{2})(?P<serial>\d{3})\b"
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
    "04": "Electronics and Communication Engineering (ECE)",
    "05": "Electronics & Communication Engineering",
    "06": "Mechanical Engineering",
    # Business / Agriculture / Science Streams
    "11": "General Management (BBA)",
    "12": "Business Analytics",
    "71": "Agricultural Sciences",
    "72": "B.Sc. (Hons.) Agriculture",
}


def parse_roll_number(text: str):
    """Extracts and decodes an SRU 10-digit enrollment number from text.

    Returns:
        dict with decoded metadata if found, or None if no valid roll number matches.
    """
    if not text:
        return None

    match = ROLL_REGEX.search(text)
    if not match:
        return None

    raw_roll = match.group(0).upper()
    yr_digits = match.group("year")
    school_code = match.group("school")
    degree_code = match.group("degree").upper()
    prog_code = match.group("program")
    serial_str = match.group("serial")

    # Decode Year of Admission & Regulation
    admission_year = int("20" + yr_digits)
    # Batches <= 2023 follow R23 regulations; 2024+ follow latest 2024/2026-27 regulations
    if admission_year <= 2023:
        regulation = "R23"
        handbook_doc = "R23 Handbook"
    else:
        regulation = f"R{yr_digits} / 2026-27"
        handbook_doc = "Handbook 2026-27"

    school_name = SCHOOL_MAP.get(school_code, f"School Code {school_code}")
    degree_name = DEGREE_MAP.get(degree_code, f"Degree Code {degree_code}")
    program_name = PROGRAM_MAP.get(prog_code, f"Program Code {prog_code}")

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
        "batch": f"{admission_year}–{str(admission_year + 4)[-2:]}",
        "regulation": regulation,
        "handbook_doc": handbook_doc,
        "school": school_name,
        "school_code": school_code,
        "degree": degree_name,
        "degree_code": degree_code,
        "program": program_name,
        "program_code": prog_code,
        "stream": stream_short,
        "serial": serial_str,
    }


def format_student_badge(profile: dict) -> str:
    """Formats a concise student identity banner."""
    if not profile:
        return ""
    deg = profile.get("degree", "Student")
    stream = profile.get("stream", "")
    reg = profile.get("regulation", "")
    roll = profile.get("roll_number", "")
    return f"{deg} {stream} ({reg}) · Roll {roll}"

