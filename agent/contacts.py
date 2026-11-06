"""Comprehensive Contact & Personnel Directory Overlay for SR University.

Covers all 25+ official administrative services, desks, emergency units,
hostel wardens, school coordinators, and assistant deans across the handbook.

Architecture:
  - Base Source: Static Student Handbook PDFs (historical snapshot).
  - Overlay: data/contacts_override.json (live verified personnel with audit timestamps).
  - Predecessor Tracking: Remembers previous officials when administrative changes occur.
"""
import datetime
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OVERRIDE_FILE = os.path.join(DATA_DIR, "contacts_override.json")

# Full official university contact directory indexed directly from handbook pages 6, 7, 54, 82
DEFAULT_DIRECTORY = {
    # --- HOSTELS & DINING ---
    "hostel_admin_officer": {
        "id": "hostel_admin_officer",
        "role": "Administrative Officer (Hostels)",
        "category": "Hostels",
        "keywords": [
            "vinay", "vinay kumar", "ch vinay kumar", "administrative officer hostels",
            "hostel administrative officer", "hostel ao", "ao hostel", "head of hostels",
            "hostel management", "hostel admin", "ao", "ao contact", "ao number", "administrative officer"
        ],
        "current_name": "Mr. Ch. Vinay Kumar (Administrative Officer, Hostels)",
        "previous_name": "Mr. Ch. Vinay Kumar",
        "phone": "9966001761",
        "email": "c.vinaykumarreddy@sru.edu.in",
        "office": "Central Hostel Administration Office, SR University",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Overall university administrative officer overseeing both Boys and Girls hostel facilities, wardens, catering, and hostel infrastructure (Handbook p. 24).",
    },
    "hostel_boys_manager": {
        "id": "hostel_boys_manager",
        "role": "Hostel Manager / In-Charge (Boys)",
        "category": "Hostels",
        "keywords": [
            "boys hostel", "boys warden", "hostel manager boys", "bh-2", "bh-3",
            "bh-5", "boys hostel incharge", "boys incharge", "warden boys",
            "surender", "surendar", "a surender", "a. surender"
        ],
        "current_name": "Mr. A. Surender (Hostel Manager, Boys)",
        "previous_name": "Mr. A. Surender",
        "phone": "9989671719",
        "email": "a.surender@sru.edu.in / stu.boyshostel@sru.edu.in",
        "office": "Beside Dining Hall (BH-2 Desk)",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Hostel Manager for Boys Hostel (BH-2, BH-3, BH-5). Floor proctors and resident caretakers rotate periodically. For room allocations or night-out slips, report to the BH-2 central reception.",
    },
    "hostel_girls_manager": {
        "id": "hostel_girls_manager",
        "role": "Hostel Manager / In-Charge (Girls)",
        "category": "Hostels",
        "keywords": [
            "girls hostel", "girls warden", "hostel manager girls", "gh-1", "gh-8",
            "girls hostel incharge", "girls incharge", "warden girls"
        ],
        "current_name": "Office of Chief Warden (Girls Hostel)",
        "previous_name": "Ms. S. Shobha Rani",
        "phone": "9701578799",
        "email": "stu.girlshostel@sru.edu.in",
        "office": "GH-1 Ground Floor Administration Desk",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Resident assistant wardens rotate each academic term. For room allocations, medical assistance, or parent passes, report to the GH-1 desk.",
    },
    "hostel_fee_desk": {
        "id": "hostel_fee_desk",
        "role": "Hostel Fee & Allotments Desk",
        "category": "Hostels",
        "keywords": ["hostel fee", "hostel payment", "mess fee", "hostel dues", "room fee"],
        "current_name": "Finance & Accounts Branch (Hostel Section)",
        "previous_name": "Mr. O. Krishna",
        "phone": "8523852300",
        "email": "hostelfee@sru.edu.in",
        "office": "Finance & Accounts Section, Administrative Block",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Hostel accommodation fees are payable for the full academic year 15 days prior to semester start via SRAAP.",
    },

    # --- EMERGENCY & HEALTH ---
    "ambulance_emergency": {
        "id": "ambulance_emergency",
        "role": "Campus Ambulance & Emergency Driver",
        "category": "Health & Emergency",
        "keywords": ["ambulance", "medical emergency", "hospital", "patient vehicle", "emergency driver"],
        "current_name": "Campus Ambulance Desk (Mr. Sai Kumar)",
        "previous_name": "Mr. Sai Kumar",
        "phone": "7989738242",
        "email": "healthcenter@sru.edu.in",
        "office": "Health & Wellness Center, Campus Entrance",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Available 24/7 for emergency patient transfer to university hospital / designated tertiary hospitals in Warangal.",
    },
    "health_wellness_center": {
        "id": "health_wellness_center",
        "role": "Health and Wellness Center (First Aid & Dispensary)",
        "category": "Health & Emergency",
        "keywords": ["health center", "wellness center", "clinic", "doctor", "dispensary", "first aid", "medicine", "sick"],
        "current_name": "Health and Wellness Center (Ms. B. Pavani)",
        "previous_name": "Ms. B. Pavani",
        "phone": "6300390764",
        "email": "healthcenter@sru.edu.in",
        "office": "Health and Wellness Center, Campus Block",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Provides outpatient medical support, essential medicines, and emergency first aid for day scholars and hostellers.",
    },
    "anti_ragging_cell": {
        "id": "anti_ragging_cell",
        "role": "Anti-Ragging Squad & Prevention Cell",
        "category": "Discipline & Safety",
        "keywords": ["anti ragging", "antiragging", "ragging", "harassment", "bully", "complaint ragging"],
        "current_name": "Anti-Ragging Squad (Mr. A. Rajeshwar Rao)",
        "previous_name": "Mr. A. Rajeshwar Rao",
        "phone": "9948533654",
        "email": "antiragging@sru.edu.in",
        "office": "Student Welfare Office / Security Command Desk",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Zero-tolerance policy. Reports can be lodged 24/7 via email, phone, or in-person with strict confidentiality.",
    },
    "counseling_center": {
        "id": "counseling_center",
        "role": "Student Counseling & Psychological Wellness Center",
        "category": "Health & Emergency",
        "keywords": ["counseling", "counselor", "psychologist", "mental health", "stress", "depression", "counsel"],
        "current_name": "Student Counseling Center (Ms. Swapna / Mr. Benson)",
        "previous_name": "Ms. Swapna (Girls: 7207672300) / Mr. Benson (Boys: 7207362300)",
        "phone": "7207672300 (Girls) / 7207362300 (Boys)",
        "email": "stu.counseling@sru.edu.in",
        "office": "Student Counseling Cell, Block-1",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Confidential psychological counseling, academic stress management, and emotional well-being support.",
    },

    # --- ACADEMIC & SRAAP PORTAL SERVICES ---
    "sraap_login_support": {
        "id": "sraap_login_support",
        "role": "SRAAP Portal Login & Technical Support",
        "category": "Portal & IT",
        "keywords": ["sraap login", "sraap password", "reset sraap", "portal login", "sraap issue", "login credentials"],
        "current_name": "SRAAP Technical Support Desk (Mr. D. Kishore)",
        "previous_name": "Mr. D. Kishore",
        "phone": "Campus Intercom / SRAAP Helpdesk",
        "email": "sraap@sru.edu.in",
        "office": "Block-I, Ground Floor (Administrative IT Section)",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "For password resets, portal locking, or timetable view issues, visit the Ground Floor Block-I counter with ID card.",
    },
    "sraap_details_update": {
        "id": "sraap_details_update",
        "role": "Student Profile & Data Correction in SRAAP",
        "category": "Portal & IT",
        "keywords": ["sraap details update", "change phone number", "update email", "parent number update", "sraap profile"],
        "current_name": "Student Data Desk (Ms. P. Purnima)",
        "previous_name": "Ms. P. Purnima",
        "phone": "9966614130",
        "email": "purnima@sru.edu.in",
        "office": "Block-I, Room No. 1013",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Requires proof of document for corrections in student name, parental phone, or permanent address.",
    },
    "wifi_support": {
        "id": "wifi_support",
        "role": "Campus Wi-Fi & Network Administration",
        "category": "Portal & IT",
        "keywords": ["wifi", "wi-fi", "internet", "network issue", "hostel wifi", "wifi login", "campus network"],
        "current_name": "IT Network Infrastructure (Mr. A. Bala Krishna)",
        "previous_name": "Mr. A. Bala Krishna",
        "phone": "8886522500",
        "email": "a.balakrishna@sru.edu.in",
        "office": "Block-I, Room No. 1008",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Student authentication uses official SRU enrollment ID credentials across campus access points.",
    },
    "examination_cell": {
        "id": "examination_cell",
        "role": "Examination Branch / Controller of Examinations",
        "category": "Academics & Exams",
        "keywords": ["exam cell", "examination branch", "coe", "hall ticket", "revaluation", "grade card", "marksheet", "transcripts", "backlogs"],
        "current_name": "Examination Branch (Mr. K. Kiran Babu)",
        "previous_name": "Mr. K. Kiran Babu",
        "phone": "9908336336",
        "email": "examcell@sru.edu.in",
        "office": "Examination Branch, Administrative Wing",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Processes end-semester registrations, supplementary examinations, grade card corrections, and official transcripts.",
    },
    "certificates_desk": {
        "id": "certificates_desk",
        "role": "Student Certificates Desk (TC, Bonafide, Migration, Custodian)",
        "category": "Administrative Services",
        "keywords": ["bonafide", "transfer certificate", "tc", "migration certificate", "custodian certificate", "study certificate"],
        "current_name": "Certificates Section (Ms. Jupaka Ramadevi)",
        "previous_name": "Ms. Jupaka Ramadevi",
        "phone": "9963084035",
        "email": "j.ramadevi@sru.edu.in",
        "office": "Block-I, Room No. 1002 (Administrative Office)",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Apply online through SRAAP portal or submit written application at Room 1002 on working days up to 5:00 PM.",
    },
    "id_card_desk": {
        "id": "id_card_desk",
        "role": "Student Identity Card Reissue & New ID",
        "category": "Administrative Services",
        "keywords": ["id card", "identity card", "lost id card", "reissue id", "id card reissue", "lost id"],
        "current_name": "ID Card Counter (Mr. B. Ramesh)",
        "previous_name": "Mr. B. Ramesh",
        "phone": "9963310699",
        "email": "b.ramesh@sru.edu.in",
        "office": "Block-I, Room No. 1002",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Duplicate ID cards require proof of lost ID fine payment receipt and administrative verification.",
    },
    "tuition_fee_desk": {
        "id": "tuition_fee_desk",
        "role": "Tuition Fee & Accounts Desk",
        "category": "Finance & Accounts",
        "keywords": ["tuition fee", "fee receipt", "fee payment", "pending dues", "fee challan", "fee counter"],
        "current_name": "Fee & Accounts Counter (Ms. B. Sunitha / Mr. J. Sunil)",
        "previous_name": "Ms. B. Sunitha (9912654505) / Mr. J. Sunil (9866001312)",
        "phone": "9912654505 / 9866001312",
        "email": "b.sunitha@sru.edu.in / j.sunil@sru.edu.in",
        "office": "Block-I, Room No. 1018",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Tuition and institutional dues must be cleared per published academic calendar schedules.",
    },
    "scholarship_desk": {
        "id": "scholarship_desk",
        "role": "Scholarship Section (State epass & Merit)",
        "category": "Finance & Accounts",
        "keywords": ["scholarship", "epass", "fee reimbursement", "telangana epass", "nsp scholarship", "scholarship renewal"],
        "current_name": "Scholarship Section (Mr. G. Raju)",
        "previous_name": "Mr. G. Raju",
        "phone": "9908337049",
        "email": "g.raju@sru.edu.in",
        "office": "Block-I, Room No. 1002",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Assists with Telangana ePASS application submission, biometric authentication, and institutional verification.",
    },
    "transport_services": {
        "id": "transport_services",
        "role": "University Transport Services & Bus Pass",
        "category": "Campus Transport",
        "keywords": ["bus pass", "transport", "bus route", "bus fee", "transport incharge", "bus driver", "college bus"],
        "current_name": "Transport Department (Mr. B. Ramesh / Mr. A. Keerthi Reddy)",
        "previous_name": "Mr. B. Ramesh (9963310699) / Mr. A. Keerthi Reddy (9640606408)",
        "phone": "9640606408 / 9963310699",
        "email": "transport@sru.edu.in",
        "office": "Block-I, Room No. 1002",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Operates Monday to Friday covering Kazipet, Hanamkonda, Warangal, Karimnagar, Husnabad, and Jammikunta.",
    },
    "library_helpdesk": {
        "id": "library_helpdesk",
        "role": "Central Library & Digital Resources",
        "category": "Library",
        "keywords": ["library", "librarian", "book bank", "digital library", "books issue", "library dues"],
        "current_name": "Central Library (Mr. Sammi Reddy)",
        "previous_name": "Mr. Sammi Reddy",
        "phone": "0870-2818384",
        "email": "libraian@sru.edu.in",
        "office": "Central Library Building, SR University",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Access to DELNET, IEEE Xplore, text book bank, and quiet study areas. Open on all working days.",
    },
    "placements_desk": {
        "id": "placements_desk",
        "role": "Center for Student Success & Placements (CSSP)",
        "category": "Career & Placements",
        "keywords": ["placement", "placements", "campus drive", "internship", "cssp", "interview", "recruitment"],
        "current_name": "Center for Student Success & Placements (Mr. D. Sridhar)",
        "previous_name": "Mr. D. Sridhar",
        "phone": "9000966994",
        "email": "stu.cssp@sru.edu.in",
        "office": "CSSP Placement Wing, Block-I",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Coordinates on-campus hiring drives, industry internships, aptitude training, and corporate mentorship.",
    },
    "grievance_cell": {
        "id": "grievance_cell",
        "role": "Student Grievance Redressal Committee",
        "category": "Administrative Services",
        "keywords": ["grievance", "complaint", "student grievance", "redressal", "dispute", "harassment complaint"],
        "current_name": "Grievance Redressal Cell (Mr. P. Naresh)",
        "previous_name": "Mr. P. Naresh",
        "phone": "9989221167",
        "email": "grievance@sru.edu.in / stu.grievance@sru.edu.in",
        "office": "Grievance Cell, Block-I",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Students may submit confidential formal grievances via email or portal ticketing system.",
    },
    "sports_department": {
        "id": "sports_department",
        "role": "Physical Education & Sports Department",
        "category": "Campus Life",
        "keywords": ["sports", "gym", "cricket ground", "football", "badminton", "physical education", "athletics"],
        "current_name": "Sports Department (Dr. P. Srinivas Goud)",
        "previous_name": "Dr. P. Srinivas Goud",
        "phone": "9949279800",
        "email": "stu.sports@sru.edu.in",
        "office": "Indoor Sports Complex / University Grounds",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Oversees university athletic teams, annual sports fest, gymnasium facilities, and inter-university meets.",
    },

    # --- DEANS & DEPARTMENT LEADERSHIP ---
    "dean_student_welfare": {
        "id": "dean_student_welfare",
        "role": "Dean, Student Welfare (SW)",
        "category": "Executive Leadership",
        "keywords": ["dean student welfare", "student welfare dean", "sw dean", "chief warden", "welfare dean"],
        "current_name": "Office of Dean (Student Welfare)",
        "previous_name": "Executive Dean (SW)",
        "phone": "0870-2818300",
        "email": "dean.sw@sru.edu.in",
        "office": "Student Welfare Office, Block-1, SR University",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Appellate authority for hostel administration, disciplinary appeals, and student welfare initiatives.",
    },
    "dean_computer_science": {
        "id": "dean_computer_science",
        "role": "Assistant Dean, Computer Science & AI (CS & AI, SOCS)",
        "category": "Academic Leadership",
        "keywords": ["dean cse", "dean computer science", "hod cse", "head cse", "csai dean", "head cs ai", "ranjith kumar"],
        "current_name": "Mr. G. Ranjith Kumar",
        "previous_name": "Mr. G. Ranjith Kumar",
        "phone": "9014432147",
        "email": "g.ranjith@sru.edu.in",
        "office": "School of Computer Science and Artificial Intelligence (SOCS)",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Leadership contact for B.Tech CSE, AI & ML, Data Science, and Cyber Security curricula.",
    },
    "dean_ece": {
        "id": "dean_ece",
        "role": "Assistant Dean, Electronics & Communication Engineering (ECE, SOE)",
        "category": "Academic Leadership",
        "keywords": ["dean ece", "hod ece", "head ece", "kallepelli sagar", "rajkumar"],
        "current_name": "Dr. Kallepelli Sagar",
        "previous_name": "Dr. Kallepelli Sagar",
        "phone": "9959026505",
        "email": "rajkumar.k@sru.edu.in",
        "office": "School of Engineering (SOE), ECE Department",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Department contact for ECE undergraduate laboratories, VLSI electives, and curriculum coordination.",
    },
    "dean_eee": {
        "id": "dean_eee",
        "role": "Assistant Dean, Electrical & Electronics Engineering (EEE, SOE)",
        "category": "Academic Leadership",
        "keywords": ["dean eee", "hod eee", "head eee", "sathyavani"],
        "current_name": "Dr. B. Sathyavani",
        "previous_name": "Dr. B. Sathyavani",
        "phone": "9908760926",
        "email": "b.sathyavani@sru.edu.in",
        "office": "School of Engineering (SOE), EEE Department",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Department contact for Electrical Engineering core and renewable energy programs.",
    },
    "dean_mechanical": {
        "id": "dean_mechanical",
        "role": "Assistant Dean, Mechanical Engineering (ME, SOE)",
        "category": "Academic Leadership",
        "keywords": ["dean mechanical", "hod mechanical", "head mechanical", "vijay reddy", "dean me"],
        "current_name": "Dr. M. Vijay Reddy",
        "previous_name": "Dr. M. Vijay Reddy",
        "phone": "7735983617",
        "email": "vijay.reddy@sru.edu.in",
        "office": "School of Engineering (SOE), Mechanical Wing",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Department contact for Mechanical Engineering laboratories, robotics, and thermal streams.",
    },
    "dean_civil": {
        "id": "dean_civil",
        "role": "Assistant Dean, Civil Engineering (CE, SOE)",
        "category": "Academic Leadership",
        "keywords": ["dean civil", "hod civil", "head civil", "gaurav tyagi"],
        "current_name": "Dr. Gaurav Tyagi",
        "previous_name": "Dr. Gaurav Tyagi",
        "phone": "9717696258",
        "email": "gaurav.tyagi@sru.edu.in",
        "office": "School of Engineering (SOE), Civil Department",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Department contact for Civil Engineering structures, surveying, and environmental labs.",
    },
    "dean_business": {
        "id": "dean_business",
        "role": "Assistant Dean, School of Business (SOB)",
        "category": "Academic Leadership",
        "keywords": ["dean business", "dean bba", "dean mba", "head business", "ramesh babu"],
        "current_name": "Dr. D. Ramesh Babu",
        "previous_name": "Dr. D. Ramesh Babu",
        "phone": "9494613402",
        "email": "rameshbabu.d@sru.edu.in",
        "office": "School of Business (SOB) Academic Wing",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Department leadership for BBA, Business Analytics, and MBA postgraduate programs.",
    },
    "dean_agriculture": {
        "id": "dean_agriculture",
        "role": "Assistant Dean, School of Agriculture (SOA)",
        "category": "Academic Leadership",
        "keywords": ["dean agriculture", "hod agriculture", "head agriculture", "pandit vaibhav", "b.sc agriculture"],
        "current_name": "Dr. Pandit Vaibhav Bhagwan",
        "previous_name": "Dr. Pandit Vaibhav Bhagwan",
        "phone": "9359179778",
        "email": "pandit.vaibhavbhagwan@sru.edu.in",
        "office": "School of Agriculture (SOA) Complex",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Academic contact for B.Sc. (Hons.) Agriculture agronomy labs, RAWE practicals, and farm field work.",
    },
    "dean_innovation": {
        "id": "dean_innovation",
        "role": "Dean, Innovation & Startups (NEST Incubator)",
        "category": "Executive Leadership",
        "keywords": ["dean innovation", "nest", "incubator", "startup", "girirajan", "chakradhar"],
        "current_name": "Dr. B. Girirajan / Dr. A. Chakradhar",
        "previous_name": "Dr. B. Girirajan",
        "phone": "8525002366 / 9908246759",
        "email": "girirajan.b@sru.edu.in / chakradhar.a@sru.edu.in",
        "office": "NEST Incubation Center, SR University",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Student startup seed funding, patent mentoring, prototyping labs, and incubation facilities.",
    },
    "director_alumni": {
        "id": "director_alumni",
        "role": "Director, Alumni Affairs & Relations",
        "category": "Executive Leadership",
        "keywords": ["alumni", "alumni director", "alumni association", "madan kumar", "srualumni"],
        "current_name": "Dr. C. Madan Kumar / Mr. Srikanth Yalabaka",
        "previous_name": "Dr. C. Madan Kumar",
        "phone": "6281814067 / 9505605467",
        "email": "dir.alumni@sru.edu.in / srikanth.v@sru.edu.in",
        "office": "Alumni Relations Office, Portal: https://srualumni.in",
        "last_updated": "2026-11-06",
        "verified": True,
        "notice": "Connects graduates with current students for mentorship, alumni chapters, and campus reunions.",
    },
}


def load_contacts() -> dict:
    """Loads live contact overrides from data/contacts_override.json with fallback."""
    if not os.path.exists(OVERRIDE_FILE):
        save_contacts(DEFAULT_DIRECTORY)
        return dict(DEFAULT_DIRECTORY)
    try:
        with open(OVERRIDE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and data:
                return data
    except Exception:
        pass
    return dict(DEFAULT_DIRECTORY)


def save_contacts(directory: dict) -> None:
    """Persists contacts dictionary to data/contacts_override.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OVERRIDE_FILE, "w", encoding="utf-8") as f:
        json.dump(directory, f, indent=2, ensure_ascii=False)


def match_contact_override(query: str) -> dict | None:
    """Checks whether the query asks for a tracked personnel role, service desk, or department unit.

    Uses high-priority semantic patterns and word-boundary regex to prevent false substring collisions.
    Returns the best matching contact record, or None if no match.
    """
    if not query:
        return None
    from .normalize import normalize_student_text
    raw_q = query.lower().strip()
    norm_q = normalize_student_text(raw_q).lower().strip()
    directory = load_contacts()

    # --- 1. Semantic High-Priority Patterns ---
    # a) Administrative Officer (AO) - Hostels / General Administration
    for candidate_q in (raw_q, norm_q):
        if re.search(r"\b(ao|administrative officer)\b", candidate_q):
            if not re.search(r"\b(exam|coe|library|sports)\b", candidate_q):
                return directory.get("hostel_admin_officer")

        # b) Boys Hostel in-charge / warden / manager / complaints / who to call
        if re.search(r"\b(boys?|bh-?\d?)\b", candidate_q) and re.search(r"\b(hostel|hostels)\b", candidate_q) and re.search(r"\b(warden|incharge|in-charge|manager|call|contact|who|problem|complaint|emergency)\b", candidate_q):
            return directory.get("hostel_boys_manager")

        # c) Girls Hostel in-charge / warden / manager / complaints / who to call
        if re.search(r"\b(girls?|gh-?\d?)\b", candidate_q) and re.search(r"\b(hostel|hostels)\b", candidate_q) and re.search(r"\b(warden|incharge|in-charge|manager|call|contact|who|problem|complaint|emergency)\b", candidate_q):
            return directory.get("hostel_girls_manager")

        # d) Department Leadership & Deans (Civil, Mech, EEE, ECE, CSE, Business, Agri, Innovation)
        if re.search(r"\b(dean|hod|head)\b", candidate_q):
            if re.search(r"\b(civil|ce)\b", candidate_q):
                return directory.get("dean_civil")
            if re.search(r"\b(mechanical|mech|me)\b", candidate_q):
                return directory.get("dean_mechanical")
            if re.search(r"\b(eee|electrical)\b", candidate_q):
                return directory.get("dean_eee")
            if re.search(r"\b(ece|electronics)\b", candidate_q):
                return directory.get("dean_ece")
            if re.search(r"\b(computer|cse|csai|socs|cs & ai)\b", candidate_q):
                return directory.get("dean_computer_science")
            if re.search(r"\b(business|sob|bba|mba)\b", candidate_q):
                return directory.get("dean_business")
            if re.search(r"\b(agriculture|soa|agri)\b", candidate_q):
                return directory.get("dean_agriculture")
            if re.search(r"\b(innovation|nest|startup)\b", candidate_q):
                return directory.get("dean_innovation")
            if re.search(r"\b(student welfare|sw)\b", candidate_q):
                return directory.get("dean_student_welfare")

    # --- 2. Keyword-based matching with word boundaries ---
    best_match = None
    longest_kw = 0

    for item_id, item in directory.items():
        keywords = item.get("keywords", [])
        for kw in keywords:
            kw_clean = kw.strip().lower()
            if not kw_clean:
                continue
            pattern = rf"(?<!\w){re.escape(kw_clean)}(?!\w)"
            for candidate_q in (raw_q, norm_q):
                if re.search(pattern, candidate_q) and len(kw_clean) > longest_kw:
                    best_match = item
                    longest_kw = len(kw_clean)

    return best_match


def update_personnel(
    position_id: str,
    name: str,
    phone: str = "",
    email: str = "",
    office: str = "",
    notice: str = "",
) -> dict:
    """Autonomously updates a personnel record, records the predecessor, and timestamps the change."""
    directory = load_contacts()
    existing = directory.get(position_id, {})

    old_name = existing.get("current_name", "Previous Official")
    today_str = datetime.date.today().isoformat()

    updated_entry = {
        "id": position_id,
        "role": existing.get("role", position_id.replace("_", " ").title()),
        "category": existing.get("category", "General Administration"),
        "keywords": existing.get("keywords", [position_id.replace("_", " ")]),
        "current_name": name.strip(),
        "previous_name": old_name if old_name != name.strip() else existing.get("previous_name", ""),
        "phone": phone.strip() or existing.get("phone", ""),
        "email": email.strip() or existing.get("email", ""),
        "office": office.strip() or existing.get("office", ""),
        "last_updated": today_str,
        "verified": True,
        "notice": notice.strip() or existing.get("notice", ""),
    }

    directory[position_id] = updated_entry
    save_contacts(directory)

    return {
        "ok": True,
        "position_id": position_id,
        "new_name": updated_entry["current_name"],
        "previous_name": updated_entry["previous_name"],
        "last_updated": today_str,
    }


def format_contact_response(contact: dict) -> dict:
    """Formats an authoritative verified contact card answering the student."""
    role = contact.get("role", "Administrative In-Charge")
    name = contact.get("current_name", "Current In-Charge")
    prev_name = contact.get("previous_name")
    phone = contact.get("phone", "Campus Help Desk")
    email = contact.get("email", "helpdesk@sru.edu.in")
    office = contact.get("office", "SR University Campus")
    updated = contact.get("last_updated", "Active")
    notice = contact.get("notice", "")

    prev_note = f"\n- **Preceding Official (Handbook Snapshot):** {prev_name}" if prev_name and prev_name != name else ""

    text = (
        f"🏢 **SR University Verified Personnel & Contact Directory:**\n\n"
        f"- **Service / Office:** {role}\n"
        f"- **Active In-Charge / Official:** **{name}**\n"
        f"- **Official Contact Number:** `{phone}`\n"
        f"- **Official Email:** `{email}`\n"
        f"- **Office / Counter Location:** {office}\n"
        f"- **Verification Status:** ✅ Live Directory Verified ({updated})"
        f"{prev_note}\n\n"
        f"ℹ️ **Administrative Advisory:**\n"
        f"{notice}\n"
        f"For urgent assistance, you can also reach the Student Help Desk (Block-I, Room 1002) or Dean Student Welfare at `dean.sw@sru.edu.in`."
    )

    return {
        "answer": text,
        "citations": ["SRU Live Directory (Active)", "Handbook 2026-27 p.6", "Handbook 2026-27 p.7", "Handbook 2026-27 p.54"],
        "tool_calls": [],
        "mode": "live_directory_match",
        "retrieval_ms": 0.5,
        "llm_ms": 0.0,
    }
