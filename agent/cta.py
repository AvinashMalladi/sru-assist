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


def build_mail_draft(
    category: str,
    recipient_email: str,
    recipient_name: str,
    recipient_role: str,
    office_location: str,
    cc_email: str = "",
    profile: dict = None,
    issue_hint: str = "",
) -> dict:
    """Builds a structured formal email draft with student profile pre-filled."""
    prof = profile or {}
    roll_no = prof.get("roll_number") or "[Enter Roll Number (e.g. 2303A51001)]"
    degree = prof.get("degree") or "B.Tech"
    branch = prof.get("program") or prof.get("branch") or "Engineering"
    batch = prof.get("batch") or "Undergraduate"
    standing = prof.get("study_status") or prof.get("academic_standing") or "Active Student"
    regulation = prof.get("regulation") or "University Regulations"

    cat = (category or "").lower()
    subject_tag = "GENERAL"
    cc = cc_email.strip()
    salutation = f"Respected Sir/Madam,"
    body_lines = []

    if "hostel" in cat:
        subject_tag = "HOSTEL"
        if not cc:
            cc = "c.vinaykumarreddy@sru.edu.in"
        body_lines = [
            f"To:",
            f"The Hostel Management / Warden's Office,",
            f"{recipient_role}, {office_location}.",
            f"",
            f"{salutation}",
            f"",
            f"I am a resident student writing to formally request your assistance regarding: {issue_hint or 'a hostel maintenance / accommodation matter'}.",
            f"",
            f"Student Details:",
            f"- Student Roll / HT No: {roll_no}",
            f"- Degree & Branch: {degree} - {branch}",
            f"- Academic Batch: {batch} ({regulation})",
            f"- Hostel / Room No: [Enter Room & Block (e.g. BH-2 Room 304)]",
            f"",
            f"Issue Description:",
            f"{issue_hint or '[Briefly describe the specific concern, room number, or request here]'}",
            f"",
            f"I kindly request you to inspect the matter and initiate corrective action at your earliest convenience.",
            f"",
            f"Thank you.",
            f"",
            f"Yours sincerely,",
            f"{roll_no}",
        ]
    elif "certificate" in cat or "bonafide" in cat or "tc" in cat:
        subject_tag = "CERTIFICATES DESK"
        if not cc:
            cc = "dean.sw@sru.edu.in"
        cert_name = "Transfer Certificate (TC)" if re.search(r"\b(tc|transfer)\b", f"{cat} {issue_hint}".lower()) else "Bonafide / Study Certificate"
        body_lines = [
            f"To:",
            f"The Administrative In-Charge (Certificates Section),",
            f"Block-I, Room No. 1002, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to formally apply for the issuance of my {cert_name}.",
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
    elif "exam" in cat or "coe" in cat:
        subject_tag = "EXAM CELL"
        body_lines = [
            f"To:",
            f"The Controller of Examinations / Exam Branch,",
            f"SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to submit an official inquiry regarding: {issue_hint or 'examination / hall ticket / grade card records'}.",
            f"",
            f"Student Details:",
            f"- Roll Number: {roll_no}",
            f"- Program: {degree} - {branch}",
            f"- Batch: {batch}",
            f"- Course Code / Subject: [Enter Course Code & Subject Name]",
            f"- Semester: [Enter Semester (e.g. Semester IV)]",
            f"",
            f"Request Summary:",
            f"{issue_hint or '[Detail the exam discrepancy, revaluation verification, or hall ticket correction needed]'}",
            f"",
            f"Thank you for your guidance.",
            f"",
            f"Yours sincerely,",
            f"{roll_no}",
        ]
    elif "wifi" in cat or "network" in cat:
        subject_tag = "IT NETWORK"
        body_lines = [
            f"To:",
            f"IT & Campus Network Infrastructure,",
            f"Block-I, Room No. 1008, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to report a campus network / Wi-Fi authentication problem.",
            f"",
            f"Student Details:",
            f"- Roll Number: {roll_no}",
            f"- Device MAC Address: [Enter Wi-Fi MAC Address]",
            f"- Device Type: [Laptop / Android / iOS / Tablet]",
            f"- Campus Location: [Hostel Block / Academic Classroom / Library]",
            f"",
            f"Issue Observed:",
            f"{issue_hint or 'Unable to authenticate with university credentials or connection drops.'}",
            f"",
            f"Thank you,",
            f"{roll_no}",
        ]
    elif "sraap" in cat:
        subject_tag = "SRAAP PORTAL"
        body_lines = [
            f"To:",
            f"SRAAP Technical Help Desk,",
            f"Administrative Block-I, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to request technical assistance with my SRAAP student portal account.",
            f"",
            f"Account Details:",
            f"- Student Roll Number: {roll_no}",
            f"- Program & Branch: {degree} - {branch}",
            f"- Issue Type: [Password Reset / Account Locked / Timetable or Attendance Error]",
            f"",
            f"Kindly reset my credentials or guide me on resolving this login issue.",
            f"",
            f"Yours sincerely,",
            f"{roll_no}",
        ]
    elif "transport" in cat:
        subject_tag = "TRANSPORT"
        body_lines = [
            f"To:",
            f"Transport In-Charge / Bus Services,",
            f"Block-I, Room No. 1002, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing regarding university bus transport services / bus pass issuance.",
            f"",
            f"Student Details:",
            f"- Roll Number: {roll_no}",
            f"- Bus Route Number: [Enter Route No (e.g. Route 4 / Kazipet)]",
            f"- Boarding Point: [Enter Boarding Stop]",
            f"- Fee Receipt Number: [Enter Challan / Transaction ID]",
            f"",
            f"Thank you,",
            f"{roll_no}",
        ]
    elif "scholarship" in cat:
        subject_tag = "SCHOLARSHIP"
        body_lines = [
            f"To:",
            f"Scholarship Section (State ePASS & Merit Desk),",
            f"Block-I, Room No. 1002, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to request administrative verification for my scholarship application.",
            f"",
            f"Student Details:",
            f"- Student Roll Number: {roll_no}",
            f"- Degree & Branch: {degree} - {branch}",
            f"- ePASS / NSP Application ID: [Enter Application ID]",
            f"- Nature of Request: [Biometric Authentication / Document Verification / Renewal]",
            f"",
            f"Thank you,",
            f"{roll_no}",
        ]
    else:
        subject_tag = "STUDENT INQUIRY"
        if not cc:
            cc = "dean.sw@sru.edu.in"
        body_lines = [
            f"To:",
            f"{recipient_role},",
            f"{office_location}, SR University.",
            f"",
            f"{salutation}",
            f"",
            f"I am writing to formally submit a student inquiry regarding: {issue_hint or 'university administrative support'}.",
            f"",
            f"Student Details:",
            f"- Roll Number: {roll_no}",
            f"- Degree & Branch: {degree} - {branch}",
            f"- Academic Batch: {batch}",
            f"",
            f"Details:",
            f"{issue_hint or '[Enter specific details of your inquiry or request here]'}",
            f"",
            f"Thank you for your consideration.",
            f"",
            f"Yours sincerely,",
            f"{roll_no}",
        ]

    subject = f"[{subject_tag}] {issue_hint[:30] or recipient_role} - {roll_no} - {branch}"
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
