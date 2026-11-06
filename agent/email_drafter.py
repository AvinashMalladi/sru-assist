"""Smart Call-to-Action (CTA) and Email Draft Generation for SRU Assist.

Provides:
  1. Detection of email draft requests (e.g. "draft an email to HOD", "write an email regarding attendance",
     "help me send a complaint", "request permission", "give me an email draft").
  2. Generation of structured, professional email drafts with To, Subject, Body, Closing, and Signature.
  3. Grounding recipient addresses strictly in the SR University Student Handbook; if not available,
     places an explicit placeholder (e.g. `[Recipient Email Address]`) without fabricating details.
  4. Detection of phone numbers and email addresses in chatbot answers for Click-to-Call and Copy actions.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

# Official handbook contact registry (Student Handbook 2026-27 p.6, 7, 10, 20, 21, 54)
OFFICIAL_CONTACTS = {
    "examination": {
        "dept": "Examination Department / Exam Cell",
        "email": "examcell@sru.edu.in",
        "phone": None,
        "officer": "Controller of Examinations (COE) / Exam Branch",
        "location": "Block-I, Ground Floor",
        "cite": "Handbook 2026-27 p.6",
    },
    "attendance": {
        "dept": "Office of Student Welfare",
        "email": "dean.sw@sru.edu.in",
        "phone": None,
        "officer": "Dean, Student Welfare",
        "cite": "Handbook 2026-27 p.5",
    },
    "condonation": {
        "dept": "Office of Student Welfare & Examination Branch",
        "email": "dean.sw@sru.edu.in",
        "phone": None,
        "officer": "Dean, Student Welfare",
        "cite": "Handbook 2026-27 p.5, p.34",
    },
    "grievance": {
        "dept": "Student Grievance Redressal Cell",
        "email": "stu.grievance@sru.edu.in",
        "phone": None,
        "officer": "Grievance Redressal Committee",
        "cite": "Handbook 2026-27 p.6, p.10",
    },
    "antiragging": {
        "dept": "Anti-Ragging Committee",
        "email": "antiragging@sru.edu.in",
        "phone": "+91 9989221167",
        "officer": "Mr. P. Naresh Kumar",
        "cite": "Handbook 2026-27 p.6, p.10",
    },
    "sraap": {
        "dept": "SRAAP / Academic Portal Support",
        "email": "sraap@sru.edu.in",
        "phone": None,
        "officer": "Mr. D. Kishore",
        "location": "Block-I, Ground Floor",
        "cite": "Handbook 2026-27 p.6, p.8",
    },
    "transport": {
        "dept": "Transport Department",
        "email": "transport@sru.edu.in",
        "phone": None,
        "officer": "Transport In-charge",
        "cite": "Handbook 2026-27 p.6",
    },
    "library": {
        "dept": "University Library",
        "email": "libraian@sru.edu.in",
        "phone": "0870-2818384",
        "officer": "Mr. Sammi Reddy (Librarian)",
        "cite": "Handbook 2026-27 p.20",
    },
    "placement_cse": {
        "dept": "Placement & Career Development (SOCS)",
        "email": "pc.csai@sru.edu.in",
        "phone": None,
        "officer": "Placement Officer, CS & AI",
        "cite": "Handbook 2026-27 p.7",
    },
    "placement_soe": {
        "dept": "Placement & Career Development (SOE)",
        "email": "pc.soe@sru.edu.in",
        "phone": None,
        "officer": "Placement Officer, Engineering",
        "cite": "Handbook 2026-27 p.7",
    },
    "placement_general": {
        "dept": "Placement & Career Development Cell",
        "email": "pc.soe@sru.edu.in",
        "phone": None,
        "officer": "Placement Officer",
        "cite": "Handbook 2026-27 p.7",
    },
    "hostel_boys": {
        "dept": "Boys Hostel Administration",
        "email": "stu.boyshostel@sru.edu.in",
        "phone": "+91 9989671719",
        "officer": "Mr. A. Surender (Hostel Manager)",
        "cite": "Handbook 2026-27 p.7, p.21",
    },
    "hostel_girls": {
        "dept": "Girls Hostel Administration",
        "email": "stu.girlshostel@sru.edu.in",
        "phone": "+91 9701578799",
        "officer": "Ms. S. Shobha Rani (Hostel Manager)",
        "cite": "Handbook 2026-27 p.7, p.21",
    },
    "counseling_boys": {
        "dept": "Student Counseling (Boys)",
        "email": "stu.counseling@sru.edu.in",
        "phone": "+91 7207362300",
        "officer": "Mr. Benson (Counselor)",
        "cite": "Handbook 2026-27 p.7, p.18",
    },
    "counseling_girls": {
        "dept": "Student Counseling (Girls)",
        "email": "stu.counseling@sru.edu.in",
        "phone": "+91 720767230",
        "officer": "Ms. Swapna (Counselor)",
        "cite": "Handbook 2026-27 p.7, p.18",
    },
    # Department leadership / HODs from Handbook p.54
    "hod_cse": {
        "dept": "Computer Science & Artificial Intelligence (CS & AI, SOCS)",
        "email": "g.ranjith@sru.edu.in",
        "phone": "+91 9014432147",
        "officer": "Mr. G. Ranjith Kumar (Assistant Dean / Head)",
        "cite": "Handbook 2026-27 p.54",
    },
    "hod_civil": {
        "dept": "Civil Engineering (CE, SOE)",
        "email": "gaurav.tyagi@sru.edu.in",
        "phone": "+91 9717696258",
        "officer": "Dr. Gaurav Tyagi (Assistant Dean / Head)",
        "cite": "Handbook 2026-27 p.54",
    },
    "hod_eee": {
        "dept": "Electrical & Electronics Engineering (EEE, SOE)",
        "email": "b.sathyavani@sru.edu.in",
        "phone": "+91 9908760926",
        "officer": "Dr. B. Sathyavani (Assistant Dean / Head)",
        "cite": "Handbook 2026-27 p.54",
    },
    "hod_mech": {
        "dept": "Mechanical Engineering (ME, SOE)",
        "email": "vijay.reddy@sru.edu.in",
        "phone": "+91 7735983617",
        "officer": "Dr. M. Vijay Reddy (Assistant Dean / Head)",
        "cite": "Handbook 2026-27 p.54",
    },
    "hod_ece": {
        "dept": "Electronics & Communication Engineering (ECE, SOE)",
        "email": "rajkumar.k@sru.edu.in",
        "phone": "+91 9959026505",
        "officer": "Mr. K. Sagar (Assistant Dean / Head)",
        "cite": "Handbook 2026-27 p.54",
    },
    "hod_business": {
        "dept": "School of Business (SOB, BBA/MBA)",
        "email": "rameshbabu.d@sru.edu.in",
        "phone": "+91 9494613402",
        "officer": "Dr. D. Ramesh Babu (Assistant Dean / Head)",
        "cite": "Handbook 2026-27 p.54",
    },
    "hod_agriculture": {
        "dept": "School of Agriculture (SOA, B.Sc. Ag)",
        "email": "pandit.vaibhavbhagwan@sru.edu.in",
        "phone": "+91 9359179778",
        "officer": "Dr. Pandit Vaibhav Bhagwan (Assistant Dean / Head)",
        "cite": "Handbook 2026-27 p.54",
    },
    "innovation": {
        "dept": "Centre for Innovation & Startups (SRiX / NEST)",
        "email": "girirajan.b@sru.edu.in",
        "phone": "+91 8525002366",
        "officer": "Dr. B. Girirajan (Dean, Innovation)",
        "cite": "Handbook 2026-27 p.54",
    },
}

# Regex to detect an explicit request to draft/write an email, letter, or complaint
DRAFT_TRIGGER_RE = re.compile(
    r"\b(?:draft(?:\s+an?)?\s+email|"
    r"write(?:\s+an?)?\s+email|"
    r"give\s+me\s+an?\s+email\s+draft|"
    r"email\s+draft|"
    r"draft\s+a\s+letter|"
    r"write\s+a\s+letter|"
    r"help\s+me\s+send\s+a\s+complaint|"
    r"help\s+me\s+write\s+a\s+complaint|"
    r"draft\s+a\s+complaint|"
    r"write\s+(?:a\s+)?complaint|"
    r"send\s+a\s+complaint\s+email|"
    r"complain\s+about|"
    r"i\s+need\s+to\s+request\s+permission|"
    r"request\s+permission\s+email|"
    r"email\s+template|"
    r"sample\s+email|"
    r"application\s+letter|"
    r"email\s+to\s+(?:the\s+)?(?:hod|dean|examination|exam\s+cell|principal|warden))\b",
    re.I,
)

# Regex to detect phone numbers in text (Indian 10-digit mobile, STD landlines, and +91 formats)
PHONE_RE = re.compile(
    r"(?:\+91[\s-]?)?(?:0\d{2,4}[\s-]?)?[6-9]\d{4}[\s-]?\d{5}|\b0870[\s-]?\d{6,7}\b|\b\d{10}\b"
)

# Regex for email addresses
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def is_email_draft_request(question: str) -> bool:
    """Returns True if the user is asking to draft/write an email or complaint."""
    if not question:
        return False
    q = question.strip()
    return bool(DRAFT_TRIGGER_RE.search(q))


def _resolve_target_contact(query: str, history: Optional[List[Dict[str, Any]]] = None, profile: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
    """Determine the most relevant department contact based on query, conversation history, and profile."""
    q_all = query.lower()
    if history:
        for m in reversed(history[-4:]):
            if isinstance(m, dict) and m.get("content"):
                q_all += " " + str(m["content"]).lower()

    prof = profile or {}
    branch = str(prof.get("branch") or prof.get("stream") or "").lower()

    # 1. Attendance & Condonation
    if re.search(r"\b(condonation|medical\s+leave|shortage|duty\s+leave)\b", q_all):
        return "condonation", OFFICIAL_CONTACTS["condonation"]
    if re.search(r"\b(attendance)\b", q_all):
        return "attendance", OFFICIAL_CONTACTS["attendance"]

    # 2. Examination, Revaluation, Results, Hall Ticket
    if re.search(r"\b(revaluation|recounting|exam\s+schedule|hall\s+ticket|admit\s+card|supplementary|backlog\s+exam|grade\s+sheet|marks\s+card|f\s+grade|exam\s+cell|examination)\b", q_all):
        return "examination", OFFICIAL_CONTACTS["examination"]

    # 3. Complaint & Grievance
    if re.search(r"\b(complaint|grievance|unfair|harassment|ragging|ragged)\b", q_all):
        if "ragging" in q_all or "ragged" in q_all:
            return "antiragging", OFFICIAL_CONTACTS["antiragging"]
        return "grievance", OFFICIAL_CONTACTS["grievance"]

    # 4. Placement & Internship
    if re.search(r"\b(placement|internship|campus\s+interview|recruitment|job\s+offer)\b", q_all):
        if "cse" in branch or "cs" in q_all or "ai" in q_all:
            return "placement_cse", OFFICIAL_CONTACTS["placement_cse"]
        return "placement_soe", OFFICIAL_CONTACTS["placement_soe"]

    # 5. Hostels & Dining
    if re.search(r"\b(hostel|mess|room|warden)\b", q_all):
        if "girl" in q_all or "gh" in q_all:
            return "hostel_girls", OFFICIAL_CONTACTS["hostel_girls"]
        return "hostel_boys", OFFICIAL_CONTACTS["hostel_boys"]

    # 6. SRAAP Portal & Fees
    if re.search(r"\b(sraap|portal|login|fee\s+receipt|tuition\s+fee|fee\s+payment)\b", q_all):
        return "sraap", OFFICIAL_CONTACTS["sraap"]

    # 7. Department Leadership / HOD
    if re.search(r"\b(hod|head\s+of\s+department|assistant\s+dean|department|permission|leave|bonafide)\b", q_all):
        if any(k in q_all or k in branch for k in ("cse", "computer", "cs & ai", "csai", "software")):
            return "hod_cse", OFFICIAL_CONTACTS["hod_cse"]
        if any(k in q_all or k in branch for k in ("civil", "ce")):
            return "hod_civil", OFFICIAL_CONTACTS["hod_civil"]
        if any(k in q_all or k in branch for k in ("mech", "mechanical", "me")):
            return "hod_mech", OFFICIAL_CONTACTS["hod_mech"]
        if any(k in q_all or k in branch for k in ("eee", "electrical")):
            return "hod_eee", OFFICIAL_CONTACTS["hod_eee"]
        if any(k in q_all or k in branch for k in ("ece", "electronics")):
            return "hod_ece", OFFICIAL_CONTACTS["hod_ece"]
        if any(k in q_all or k in branch for k in ("bba", "mba", "business", "sob")):
            return "hod_business", OFFICIAL_CONTACTS["hod_business"]
        if any(k in q_all or k in branch for k in ("agri", "agriculture", "soa", "b.sc")):
            return "hod_agriculture", OFFICIAL_CONTACTS["hod_agriculture"]
        # Default to HOD CSE or generic if branch unspecified
        return "hod_cse", OFFICIAL_CONTACTS["hod_cse"]

    # Default fallback: Student Welfare Office
    return "attendance", OFFICIAL_CONTACTS["attendance"]


def generate_smart_email_draft(
    question: str,
    history: Optional[List[Dict[str, Any]]] = None,
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generates a structured, professional email draft with verified handbook contacts and action metadata."""
    prof = profile or {}
    roll_no = prof.get("roll_number") or "[Your Roll Number]"
    name = prof.get("name") or "[Student Name]"
    branch = prof.get("branch") or prof.get("stream") or prof.get("degree") or "[Your Branch / Degree]"
    regulation = prof.get("regulation") or prof.get("batch") or "Academic Regulations"

    key, contact = _resolve_target_contact(question, history, profile)
    to_email = contact.get("email") or "[Recipient Email Address]"
    officer_title = contact.get("officer") or "Respected Authority"
    dept_name = contact.get("dept") or "SR University"
    cite = contact.get("cite") or "Handbook 2026-27"

    q_lower = question.lower()

    # Determine topic-specific subject and body template
    if key in ("attendance", "condonation") or "attendance" in q_lower or "condon" in q_lower:
        subject = f"Application for Attendance Condonation / Clarification - {roll_no}"
        body = (
            f"Respected {officer_title},\n\n"
            f"I hope this email finds you well.\n\n"
            f"I am a student of {branch} at SR University, bearing Roll Number {roll_no}. "
            f"I am writing to respectfully bring to your kind notice my attendance status for the current semester.\n\n"
            f"Due to unavoidable medical circumstances / authorized academic commitments, my attendance has fallen slightly "
            f"below the mandatory 75% threshold, remaining within the condonable bracket (65%–75%) as stipulated under university regulations.\n\n"
            f"I have attached the requisite supporting medical certificates / relevant documentation for your kind verification. "
            f"I humbly request you to kindly consider my genuine situation and grant approval for attendance condonation so that I may be permitted to write the upcoming semester examinations.\n\n"
            f"Thank you for your valuable time and consideration.\n\n"
            f"Best regards,\n"
            f"{name}\n"
            f"Roll Number: {roll_no}\n"
            f"Branch: {branch}\n"
            f"Regulation: {regulation}"
        )
    elif key == "examination" or any(k in q_lower for k in ("exam", "revaluation", "grade", "marks")):
        subject = f"Request for Examination Clarification / Revaluation - {roll_no}"
        body = (
            f"Respected {officer_title},\n\n"
            f"I am writing to respectfully request clarification regarding the examination schedule / evaluation details for my semester courses.\n\n"
            f"Student Details:\n"
            f"- Name: {name}\n"
            f"- Roll Number: {roll_no}\n"
            f"- Degree & Branch: {branch}\n"
            f"- Applicable Regulation: {regulation}\n\n"
            f"Request / Grievance Details:\n"
            f"[Please specify your subject code, examination date, and concern regarding revaluation, recounting, or schedule discrepancy here]\n\n"
            f"Could you please guide me on the necessary administrative steps and fee payment procedures required through the SRAAP portal?\n\n"
            f"Thank you for your time and assistance.\n\n"
            f"Best regards,\n"
            f"{name}\n"
            f"Roll Number: {roll_no}"
        )
    elif key in ("grievance", "antiragging") or any(k in q_lower for k in ("complaint", "grievance")):
        subject = f"Formal Grievance Submission Regarding Academic / Campus Concern - {roll_no}"
        body = (
            f"Respected {officer_title},\n\n"
            f"I am submitting this formal communication to bring an important concern to the attention of the Grievance Redressal Committee.\n\n"
            f"Student Information:\n"
            f"- Name: {name}\n"
            f"- Roll Number: {roll_no}\n"
            f"- Branch: {branch}\n\n"
            f"Nature of Grievance:\n"
            f"[Please describe the specific issue, date of occurrence, location, and individuals involved in a clear and factual manner]\n\n"
            f"I request your kind intervention to review this matter impartially and advise on the appropriate resolution according to university policy.\n\n"
            f"Thank you for your prompt attention to this matter.\n\n"
            f"Sincerely,\n"
            f"{name}\n"
            f"Roll Number: {roll_no}"
        )
    elif "placement" in key or "placement" in q_lower or "internship" in q_lower:
        subject = f"Inquiry Regarding Placement Registration / Internship NOC - {roll_no}"
        body = (
            f"Respected {officer_title},\n\n"
            f"I hope you are having a productive day.\n\n"
            f"I am writing from the Department of {branch} (Roll No: {roll_no}) regarding campus recruitment and internship procedures for our batch.\n\n"
            f"[State your specific query: e.g., Requesting a No Objection Certificate (NOC) for an external internship, or seeking guidance on company placement criteria and registration]\n\n"
            f"I would greatly appreciate your guidance on the submission deadline and necessary portal approvals.\n\n"
            f"Thank you for your support and guidance,\n\n"
            f"Best regards,\n"
            f"{name}\n"
            f"Roll Number: {roll_no}"
        )
    else:
        # HOD / General Academic Permission
        subject = f"Request for Academic Permission / Consultation - {roll_no}"
        body = (
            f"Respected {officer_title},\n\n"
            f"I hope you are doing well.\n\n"
            f"I am a student of your department ({branch}), bearing Roll Number {roll_no}. "
            f"I am writing to respectfully request your guidance and permission regarding my academic matters for the ongoing semester.\n\n"
            f"[Please briefly explain the reason for your request, such as permission for leave, subject registration, lab clearance, or bonafide requirement]\n\n"
            f"I assure you that I will maintain my academic schedule and fulfill all coursework obligations diligently.\n\n"
            f"Thank you for your time and kind consideration.\n\n"
            f"Best regards,\n"
            f"{name}\n"
            f"Roll Number: {roll_no}\n"
            f"Department: {dept_name}"
        )

    # Note if email is placeholder or verified
    is_verified_email = bool(to_email and to_email != "[Recipient Email Address]")
    recipient_note = (
        f"Verified handbook contact: `{to_email}` ({dept_name})"
        if is_verified_email
        else "Recipient address not found in handbook. Please fill in the recipient email address."
    )

    phone_meta = []
    if contact.get("phone"):
        phone_meta.append({"number": contact["phone"], "tel": clean_phone_uri(contact["phone"])})

    markdown_answer = (
        f"Here is a professional email draft prepared for **{dept_name}**:\n\n"
        f"**To:** `{to_email}`\n"
        f"**Subject:** `{subject}`\n\n"
        f"```text\n{body}\n```\n\n"
        f"💡 **Tip:** Use the action buttons below to **Copy Email**, **Copy Subject**, **Open Directly in Gmail**, or **Edit Draft** before sending."
    )

    return {
        "answer": markdown_answer,
        "citations": [cite],
        "tool_calls": [],
        "mode": "email_draft",
        "email_draft": {
            "to": to_email,
            "subject": subject,
            "body": body,
            "recipient_name": officer_title,
            "dept": dept_name,
            "is_verified": is_verified_email,
        },
        "actions": {
            "calls": phone_meta,
            "emails": [to_email] if is_verified_email else [],
            "draft": True,
        },
    }


def clean_phone_uri(phone_str: str) -> str:
    """Converts a raw phone string into a clean tel: URI."""
    digits = re.sub(r"[^\d+]", "", phone_str)
    if digits.startswith("+"):
        return f"tel:{digits}"
    if len(digits) == 10:
        return f"tel:+91{digits}"
    return f"tel:{digits}"


def extract_contact_actions(text: str) -> Dict[str, Any]:
    """Scans text for valid phone numbers and email addresses and generates CTA action objects."""
    if not text:
        return {"calls": [], "emails": []}

    calls = []
    seen_phones = set()

    # Search for phone numbers
    for m in PHONE_RE.finditer(text):
        raw = m.group(0).strip()
        clean_digits = re.sub(r"[^\d]", "", raw)
        # Avoid false positives on 4-digit years or roll numbers (must be 10 digits or start with 0870)
        if len(clean_digits) == 10 and clean_digits[0] in "6789":
            display = f"+91 {clean_digits[:5]} {clean_digits[5:]}"
            if clean_digits not in seen_phones:
                seen_phones.add(clean_digits)
                calls.append({"number": display, "tel": f"tel:+91{clean_digits}"})
        elif clean_digits.startswith("0870") and len(clean_digits) in (10, 11):
            if clean_digits not in seen_phones:
                seen_phones.add(clean_digits)
                calls.append({"number": raw, "tel": f"tel:{clean_digits}"})

    emails = []
    seen_emails = set()
    for m in EMAIL_RE.finditer(text):
        em = m.group(0).strip()
        if em.lower() not in seen_emails and not em.endswith(".png") and not em.endswith(".jpg"):
            seen_emails.add(em.lower())
            emails.append(em)

    return {"calls": calls, "emails": emails}
