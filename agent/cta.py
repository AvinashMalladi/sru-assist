"""Automated Call to Action (CTA) & Formal Mail Drafting Engine for AURA.

Generates pre-filled formal email drafts, native phone dialer links (tel:),
and copyable application letters mapped to SR University departments and desks.
"""
import re
import urllib.parse


def _clean_phone(phone_str: str) -> str:
    """Extracts first valid 10-digit phone number for native tel: dialer."""
    if not phone_str:
        return ""
    m = re.search(r"\b(\d{10})\b", phone_str)
    return m.group(1) if m else ""


def _extract_primary_email(email_str: str) -> str:
    """Extracts the first valid email address."""
    if not email_str:
        return ""
    m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", email_str)
    return m.group(0) if m else ""


def resolve_formal_topic(category: str, role: str, query: str) -> tuple[str, str, str]:
    """Resolves a standardized, formal Subject Tag, Topic Title, and Issue Summary.
    Prevents student typos, informal slang, and raw chat text from contaminating
    the formal subject line and official correspondence.
    
    Returns: (subject_tag, formal_title, issue_summary)
    """
    from .normalize import normalize_student_text
    q = normalize_student_text(query or "").lower().strip()
    cat = (category or "").lower().strip()
    r = (role or "").lower().strip()

    # 1. Wi-Fi & IT Network
    if any(k in q for k in ("wifi", "wi-fi", "internet", "network", "net problem", "connection")) or any(k in cat for k in ("wifi", "network", "it")) or "network" in r or "wi-fi" in r or "wifi" in r:
        return (
            "IT NETWORK",
            "Wi-Fi Connectivity & Network Access Request",
            "Facing persistent connection issues / unable to authenticate with student credentials on the university Wi-Fi network."
        )

    # 2. Hostel - Room Maintenance / Plumbing / Electricity / Mess Food
    if any(k in q for k in ("leak", "leakage", "water", "plumb", "light", "fan", "electric", "switch", "clean", "washroom", "bathroom", "mess", "food", "carpenter")) and ("hostel" in cat or "hostel" in r or "hostel" in q):
        return (
            "HOSTEL",
            "Hostel Room Maintenance & Repair Request",
            "Reporting a physical maintenance concern in the hostel (electrical / plumbing / cleanliness / fixtures) requiring inspection and repair."
        )

    # 3. Hostel - Curfew / Late Arrival / Out-Pass
    if any(k in q for k in ("curfew", "late", "out-pass", "outpass", "gate pass", "night out", "outing", "12 o clock", "timing")) and ("hostel" in cat or "hostel" in r or "hostel" in q):
        return (
            "HOSTEL",
            "Hostel Late Arrival & Permitted Out-Pass Request",
            "Requesting official permission and clarification regarding late return / out-pass guidelines."
        )

    # 4. Hostel - General Accommodation / Room Allocation
    if "hostel" in cat or "hostel" in r or "hostel" in q:
        return (
            "HOSTEL",
            "Hostel Accommodation & Services Inquiry",
            "Inquiry regarding hostel room allotment, facilities, or residential code of conduct."
        )

    # 5. Certificates - Transfer Certificate (TC)
    if re.search(r"\b(tc|transfer\s+certificate)\b", q) or "tc" in cat:
        return (
            "CERTIFICATES DESK",
            "Application for Transfer Certificate (TC)",
            "Formally requesting the issuance of original Transfer Certificate (TC) upon completion / withdrawal."
        )

    # 6. Certificates - Bonafide / Study Certificate
    if re.search(r"\b(bonafide|study\s+certificate)\b", q) or "bonafide" in cat:
        return (
            "CERTIFICATES DESK",
            "Application for Bonafide / Study Certificate",
            "Formally applying for the issuance of a Bonafide / Study Certificate for official and educational purposes."
        )

    # 7. Certificates - Migration / Custodian
    if re.search(r"\b(migration|custodian)\b", q) or any(k in cat for k in ("migration", "custodian")):
        cert = "Migration Certificate" if "migration" in q else "Custodian Certificate"
        return (
            "CERTIFICATES DESK",
            f"Application for {cert}",
            f"Formally requesting the issuance of {cert}."
        )

    # 8. Student Identity Card Reissue
    if any(k in q for k in ("id card", "identity card", "lost id", "reissue id")) or "id" in cat or "id card" in r:
        return (
            "ID CARD DESK",
            "Application for Student Identity Card Reissue",
            "Reporting a lost/damaged student identity card and requesting the issuance of a duplicate card."
        )

    # 9. Examination & Hall Ticket
    if any(k in q for k in ("hall ticket", "admit card")) or "hall ticket" in r:
        return (
            "EXAM CELL",
            "Hall Ticket Correction & Examination Admit Card Request",
            "Requesting correction or verification of examination hall ticket details."
        )
    if any(k in q for k in ("reval", "revaluation", "re-evaluation", "paper checking")):
        return (
            "EXAM CELL",
            "Application for Answer Script Revaluation",
            "Submitting an application for formal revaluation and answer script verification."
        )
    if "exam" in cat or "exam" in r or "coe" in r:
        return (
            "EXAM CELL",
            "Examination Records & Grade Inquiry",
            "Inquiry regarding semester examination evaluation, Continuous Internal Evaluation (CIE), or grade card."
        )

    # 10. SRAAP Student Portal
    if any(k in q for k in ("password", "reset", "login", "unlock")) or "login" in cat:
        return (
            "SRAAP PORTAL",
            "SRAAP Portal Account Password Reset Request",
            "Requesting technical assistance to reset portal password or unlock student account."
        )
    if any(k in q for k in ("profile", "parent number", "phone number", "update details")) or "sraap" in cat or "sraap" in r:
        return (
            "SRAAP PORTAL",
            "SRAAP Student Profile Data Correction Request",
            "Requesting administrative correction of contact or profile details in the SRAAP database."
        )

    # 11. Transport & Bus Pass
    if any(k in q for k in ("bus", "transport", "route", "bus pass")) or "transport" in cat or "transport" in r:
        return (
            "TRANSPORT",
            "University Bus Pass Registration & Route Inquiry",
            "Requesting bus pass registration, route confirmation, or transport fee verification."
        )

    # 12. Scholarships & State ePASS
    if any(k in q for k in ("scholarship", "epass", "reimbursement", "fee concession")) or "scholarship" in cat:
        return (
            "SCHOLARSHIP",
            "ePASS Scholarship Verification & Biometric Request",
            "Requesting institutional verification and biometric authentication for state/merit scholarship."
        )

    # 13. Dean Student Welfare / Grievances
    if any(k in q for k in ("dean sw", "welfare", "grievance", "complaint", "harassment")) or "welfare" in cat:
        return (
            "STUDENT WELFARE",
            "Student Grievance & Administrative Appeal",
            "Submitting a formal student grievance / appeal to the Office of the Dean of Student Welfare."
        )

    # 14. Academic Leadership & Deans
    if "dean" in r or "hod" in r or "academic leadership" in cat:
        clean_role = role.split("(")[0].strip()
        return (
            "ACADEMIC INQUIRY",
            f"Academic Consultation ({clean_role})",
            f"Requesting formal academic consultation regarding course electives, curriculum, or departmental guidance."
        )

    # Default fallback
    clean_role = role.split("(")[0].strip()
    return (
        "STUDENT INQUIRY",
        f"Student Inquiry regarding {clean_role}",
        f"Submitting a formal inquiry regarding {clean_role} services."
    )


def build_mail_draft(
    category: str,
    recipient_email: str,
    recipient_name: str,
    recipient_role: str,
    office_location: str,
    cc_email: str = "",
    profile: dict = None,
    issue_hint: str = "",
    query: str = "",
) -> dict:
    """Builds a structured formal email draft with student profile pre-filled."""
    prof = profile or {}
    roll_no = prof.get("roll_number") or "[Enter Roll Number (e.g. 2303A51001)]"
    degree = prof.get("degree") or "B.Tech"
    branch = prof.get("program") or prof.get("branch") or "Engineering"
    batch = prof.get("batch") or "Undergraduate"
    standing = prof.get("study_status") or prof.get("academic_standing") or "Active Student"
    regulation = prof.get("regulation") or "University Regulations"

    subject_tag, formal_title, issue_summary = resolve_formal_topic(category, recipient_role, query or issue_hint)
    cc = cc_email.strip()
    salutation = f"Respected Sir/Madam,"
    body_lines = []

    if subject_tag == "HOSTEL":
        if not cc:
            cc = "c.vinaykumarreddy@sru.edu.in"
        body_lines = [
            f"To:",
            f"The Hostel Management / Warden's Office,",
            f"{recipient_role}, {office_location}.",
            f"",
            f"{salutation}",
            f"",
            f"I am a resident student writing to formally request your assistance regarding: {formal_title}.",
            f"",
            f"Student Details:",
            f"- Student Roll / HT No: {roll_no}",
            f"- Degree & Branch: {degree} - {branch}",
            f"- Academic Batch: {batch} ({regulation})",
            f"- Hostel / Room No: [Enter Room & Block (e.g. BH-2 Room 304)]",
            f"",
            f"Issue Summary:",
            f"{issue_summary}",
            f"",
            f"Specific Details:",
            f"[Please specify any additional details, dates, or assistance needed here]",
            f"",
            f"I kindly request you to inspect the matter and initiate corrective action at your earliest convenience.",
            f"",
            f"Thank you.",
            f"",
            f"Yours sincerely,",
            f"{roll_no}",
        ]
    elif subject_tag == "CERTIFICATES DESK":
        if not cc:
            cc = "dean.sw@sru.edu.in"
        body_lines = [
            f"To:",
            f"The Administrative In-Charge (Certificates Section),",
            f"Block-I, Room No. 1002, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to formally apply for the issuance of my {formal_title.replace('Application for ', '')}.",
            f"",
            f"Student Identification Details:",
            f"- Enrollment / Roll Number: {roll_no}",
            f"- Degree & Program: {degree} - {branch}",
            f"- Batch & Regulation: {batch} ({regulation})",
            f"- Academic Standing: {standing}",
            f"",
            f"Purpose of Request:",
            f"[Please specify purpose: Higher Studies / Passport / Education Loan / Employment]",
            f"",
            f"I have cleared all applicable university dues and will produce my identity card for verification upon collection.",
            f"",
            f"Yours respectfully,",
            f"{roll_no}",
        ]
    elif subject_tag == "EXAM CELL":
        body_lines = [
            f"To:",
            f"The Controller of Examinations / Exam Branch,",
            f"SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to submit an official inquiry regarding: {formal_title}.",
            f"",
            f"Student Details:",
            f"- Roll Number: {roll_no}",
            f"- Program: {degree} - {branch}",
            f"- Batch: {batch}",
            f"- Course Code / Subject: [Enter Course Code & Subject Name]",
            f"- Semester: [Enter Semester (e.g. Semester IV)]",
            f"",
            f"Request Details:",
            f"{issue_summary}",
            f"",
            f"Thank you for your guidance.",
            f"",
            f"Yours sincerely,",
            f"{roll_no}",
        ]
    elif subject_tag == "IT NETWORK":
        body_lines = [
            f"To:",
            f"IT & Campus Network Infrastructure ({recipient_name}),",
            f"Block-I, Room No. 1008, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to formally report an issue regarding: {formal_title}.",
            f"",
            f"Student Details:",
            f"- Student Roll / HT No: {roll_no}",
            f"- Degree & Branch: {degree} - {branch}",
            f"- Academic Batch: {batch} ({regulation})",
            f"",
            f"Technical Details for Network Support:",
            f"- Device Type: [Laptop / Android / iOS / Tablet]",
            f"- Device MAC Address: [Enter Wi-Fi MAC Address]",
            f"- Campus / Hostel Location: [Enter Location (e.g. BH-2 Room 304 / SOCS Block)]",
            f"",
            f"Issue Observed:",
            f"{issue_summary}",
            f"",
            f"Kindly assist me with resolving this connection issue or registering my device on the university network.",
            f"",
            f"Thank you,",
            f"{roll_no}",
        ]
    elif subject_tag == "SRAAP PORTAL":
        body_lines = [
            f"To:",
            f"SRAAP Technical Help Desk,",
            f"Administrative Block-I, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to request technical assistance regarding: {formal_title}.",
            f"",
            f"Account Details:",
            f"- Student Roll Number: {roll_no}",
            f"- Program & Branch: {degree} - {branch}",
            f"- Academic Batch: {batch}",
            f"",
            f"Request Description:",
            f"{issue_summary}",
            f"",
            f"Kindly reset my credentials or guide me on resolving this issue.",
            f"",
            f"Yours sincerely,",
            f"{roll_no}",
        ]
    elif subject_tag == "TRANSPORT":
        body_lines = [
            f"To:",
            f"Transport In-Charge / Bus Services,",
            f"Block-I, Room No. 1002, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing regarding: {formal_title}.",
            f"",
            f"Student Details:",
            f"- Roll Number: {roll_no}",
            f"- Degree & Branch: {degree} - {branch}",
            f"- Bus Route Number: [Enter Route No (e.g. Route 4 / Kazipet)]",
            f"- Boarding Point: [Enter Boarding Stop]",
            f"- Fee Receipt Number: [Enter Challan / Transaction ID]",
            f"",
            f"Request Details:",
            f"{issue_summary}",
            f"",
            f"Thank you,",
            f"{roll_no}",
        ]
    elif subject_tag == "SCHOLARSHIP":
        body_lines = [
            f"To:",
            f"Scholarship Section (State ePASS & Merit Desk),",
            f"Block-I, Room No. 1002, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing regarding: {formal_title}.",
            f"",
            f"Student Details:",
            f"- Student Roll Number: {roll_no}",
            f"- Degree & Branch: {degree} - {branch}",
            f"- ePASS / NSP Application ID: [Enter Application ID]",
            f"",
            f"Nature of Request:",
            f"{issue_summary}",
            f"",
            f"Thank you,",
            f"{roll_no}",
        ]
    elif subject_tag == "ID CARD DESK":
        body_lines = [
            f"To:",
            f"Student ID Card Counter (Mr. B. Ramesh),",
            f"Block-I, Room No. 1002, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to formally apply for the reissue of my student identity card.",
            f"",
            f"Student Details:",
            f"- Student Roll Number: {roll_no}",
            f"- Degree & Branch: {degree} - {branch}",
            f"- Batch: {batch}",
            f"- Reason for Reissue: [Lost / Damaged / Details Correction]",
            f"",
            f"I have cleared the duplicate ID card fee and will produce the payment receipt at Room 1002.",
            f"",
            f"Yours respectfully,",
            f"{roll_no}",
        ]
    else:
        if not cc:
            cc = "dean.sw@sru.edu.in"
        body_lines = [
            f"To:",
            f"{recipient_role},",
            f"{office_location}, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to formally submit a student inquiry regarding: {formal_title}.",
            f"",
            f"Student Details:",
            f"- Roll Number: {roll_no}",
            f"- Degree & Branch: {degree} - {branch}",
            f"- Academic Batch: {batch}",
            f"",
            f"Details:",
            f"{issue_summary}",
            f"",
            f"Thank you for your consideration.",
            f"",
            f"Yours sincerely,",
            f"{roll_no}",
        ]

    subject = f"[{subject_tag}] {formal_title} - {roll_no} - {branch}"
    body = "\n".join(body_lines)

    # Pre-generate RFC 3986 compliant mailto URL
    query_params = {"subject": subject, "body": body}
    if cc:
        query_params["cc"] = cc
    mailto_url = f"mailto:{recipient_email}?{urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)}"

    return {
        "recipient": recipient_email,
        "recipient_name": recipient_name,
        "recipient_role": recipient_role,
        "cc": cc,
        "subject": subject,
        "body": body,
        "mailto_url": mailto_url,
    }


def generate_cta(
    question: str,
    contact_record: dict = None,
    profile: dict = None,
    answer_text: str = "",
) -> dict | None:
    """Evaluates question, contact hit, and student profile to produce an actionable CTA payload."""
    if not contact_record and not question:
        return None

    q = (question or "").lower()
    rec = contact_record or {}
    role = rec.get("role", "Administrative In-Charge")
    name = rec.get("current_name", "Concerned Official")
    phone = _clean_phone(rec.get("phone", ""))
    email = _extract_primary_email(rec.get("email", ""))
    office = rec.get("office", "SR University Campus")
    category = rec.get("category", "General Administration")

    # If no contact record matched, see if query strongly indicates a specific desk
    if not email:
        if re.search(r"\b(tc|bonafide|migration|custodian|study cert)\b", q):
            category = "certificates"
            role = "Student Certificates Desk"
            name = "Ms. Jupaka Ramadevi"
            phone = "9963084035"
            email = "j.ramadevi@sru.edu.in"
            office = "Block-I, Room No. 1002"
        elif re.search(r"\b(girls?\s*hostel|gh-?\d?|curfew.*girls?)\b", q):
            category = "hostel"
            role = "Girls Hostel Management"
            name = "Ms. S. Shobha Rani"
            phone = "9701578799"
            email = "stu.girlshostel@sru.edu.in"
            office = "GH-1 Administration Desk"
        elif re.search(r"\b(boys?\s*hostel|bh-?\d?|curfew.*boys?)\b", q):
            category = "hostel"
            role = "Boys Hostel Management"
            name = "Mr. A. Surender"
            phone = "9989671719"
            email = "stu.boyshostel@sru.edu.in"
            office = "BH-2 Reception"
        elif re.search(r"\b(wifi|internet|network)\b", q):
            category = "wifi"
            role = "IT Network Administration"
            name = "Mr. A. Bala Krishna"
            phone = "8886522500"
            email = "a.balakrishna@sru.edu.in"
            office = "Block-I, Room No. 1008"
        elif re.search(r"\b(bus pass|transport|bus route)\b", q):
            category = "transport"
            role = "Transport Department"
            name = "Mr. A. Keerthi Reddy"
            phone = "9640606408"
            email = "transport@sru.edu.in"
            office = "Block-I, Room No. 1002"
        elif re.search(r"\b(exam|hall ticket|revaluation|grade card)\b", q):
            category = "exam_cell"
            role = "Examination Branch"
            name = "Mr. K. Kiran Babu"
            phone = "9908336336"
            email = "examcell@sru.edu.in"
            office = "Examination Branch, Administrative Wing"
        else:
            return None

    # Derive short issue hint from student question
    clean_q = re.sub(r"(?i)\b(who|whom|contact|number|phone|undaaa|unda|is there|available|tell me|please|how to|where to|apply|my|can i|call|administrative officer|ao)\b", "", question).strip()
    clean_q = re.sub(r"\s+", " ", clean_q).strip()
    issue_hint = clean_q[:40].strip() or role

    mail_draft = build_mail_draft(
        category=category,
        recipient_email=email,
        recipient_name=name,
        recipient_role=role,
        office_location=office,
        profile=profile,
        issue_hint=issue_hint,
        query=question,
    )

    action_label = f"Contact {role.split('(')[0].strip()}"
    if len(action_label) > 32:
        action_label = f"Contact {role.split(' ')[0]}"

    return {
        "action_label": action_label,
        "phone": phone,
        "email": email,
        "office": office,
        "category": category,
        "mail_draft": mail_draft,
    }
