"""Agent loop: auto-RAG grounding + optional tool calling with fallbacks.

LATENCY MODE (default): exactly ONE LLM call per question. Auto-RAG context is
injected so answers stay grounded, but tools are not offered - fastest path,
~1 round-trip. Set AGENT_MODE=agent to re-enable the multi-step tool loop
(AGENT_MAX_STEPS tool rounds) for models where tool-calling is reliable.
"""
import json
import os
import re
import time

from .config import load_env

load_env()

from . import llm, tools
from .clarify import check as clarify_check
from .contacts import format_contact_response, match_contact_override
from .counts import check as counts_check
from .cta import generate_cta
from .prompts import FALLBACK_PROMPT, FAST_SYSTEM_PROMPT, SYSTEM_PROMPT
from .retriever import get_retriever
from .roll_decoder import parse_roll_number, format_student_badge
from .normalize import normalize_student_text
from .scope_guard import check_out_of_scope

MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "4"))
MAX_HISTORY = 10
FAST_HISTORY = 6
AUTO_CONTEXT_TOP_K = int(os.environ.get("AUTO_CONTEXT_TOP_K", "4"))

CITE_RE = re.compile(r"\[([^\]]+?) · page (\d+)\]")

# Tool arguments that must never leak into a student-facing answer.
_TOOL_KEYS = ("query", "expression", "tool", "name", "arguments", "top_k", "topk")


def _cache_key(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


_GREETINGS = {
    "hello", "hi", "hey", "hlo", "helo", "hlw", "hii", "hiii", "helloo",
    "hey there", "good morning", "good afternoon", "good evening",
    "who are you", "what is your name", "what can you do", "help",
    "start", "namaste", "namaskaram", "sup", "yo", "hola",
}

_ACKNOWLEDGEMENTS = {
    "ok", "okay", "k", "kk", "cool", "got it", "understood", "sure", "fine",
    "alright", "all right", "thanks", "thank you", "thx", "ty", "tq",
    "thank u", "bye", "goodbye", "cya", "see you", "done", "perfect",
    "great", "nice",
}


_VERIFIED_FAQ = {
    "what if i get caught with slips during mid exam": {
        "answer": (
            "If you are suspected of using unauthorized slips during an exam:\n\n"
            "- **Immediate Action**: The invigilator will seize your answer script and any supporting evidence (including slips), and request a written statement.\n"
            "- **Continuation**: You may be issued a fresh answer booklet to complete the examination.\n"
            "- **Investigation**: All evidence is forwarded to the Controller of Examinations and investigated by the Committee for Prevention of Academic Malpractice (CPAM).\n"
            "- **Action**: CPAM classifies the offence and recommends penalties (ranging from a warning or cancellation of the paper to semester penalties as per university regulations).\n\n"
            "Would you like me to detail the specific penalties, appeal procedures, or flowcharts?"
        ),
        "citations": ["Handbook 2026-27 p.34", "Handbook 2026-27 p.35", "Handbook 2026-27 p.36"],
    },
    "what will happen if i happen to be caught by invigilator with slips during mid exam": {
        "answer": (
            "If you are suspected of using unauthorized slips during an exam:\n\n"
            "- **Immediate Action**: The invigilator will seize your answer script and any supporting evidence (including slips), and request a written statement.\n"
            "- **Continuation**: You may be issued a fresh answer booklet to complete the examination.\n"
            "- **Investigation**: All evidence is forwarded to the Controller of Examinations and investigated by the Committee for Prevention of Academic Malpractice (CPAM).\n"
            "- **Action**: CPAM classifies the offence and recommends penalties (ranging from a warning or cancellation of the paper to semester penalties as per university regulations).\n\n"
            "Would you like me to detail the specific penalties, appeal procedures, or flowcharts?"
        ),
        "citations": ["Handbook 2026-27 p.34", "Handbook 2026-27 p.35", "Handbook 2026-27 p.36"],
    },
    "what is the minimum pass marks": {
        "answer": (
            "**Minimum Pass Marks Summary (Handbook 2026-27):**\n\n"
            "- **Undergraduate Aggregate**: Minimum **45% aggregate marks** across all courses.\n"
            "- **Postgraduate / Ph.D. Aggregate**: Minimum **60% aggregate marks**.\n"
            "- **Individual Course Pass**: Minimum **50% marks in each final exam** (Grade Point ≥ 5.0).\n\n"
            "Would you like me to elaborate on specific programme criteria or grading scale conversions?"
        ),
        "citations": ["Handbook 2026-27 p.34", "Handbook 2026-27 p.57", "Handbook 2026-27 p.61"],
    },
    "who is the dean of computer department": {
        "answer": (
            "The handbook lists the following leadership contact for **Computer Science & Artificial Intelligence (CS & AI, SOCS)**:\n\n"
            "- **Assistant Dean**: Mr. G. Ranjith Kumar\n"
            "- **Phone**: 90144 32147\n"
            "- **Email**: g.ranjith@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the dean of compuster department": {
        "answer": (
            "The handbook lists the following leadership contact for **Computer Science & Artificial Intelligence (CS & AI, SOCS)**:\n\n"
            "- **Assistant Dean**: Mr. G. Ranjith Kumar\n"
            "- **Phone**: 90144 32147\n"
            "- **Email**: g.ranjith@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the dean of computer science": {
        "answer": (
            "The handbook lists the following leadership contact for **Computer Science & Artificial Intelligence (CS & AI, SOCS)**:\n\n"
            "- **Assistant Dean**: Mr. G. Ranjith Kumar\n"
            "- **Phone**: 90144 32147\n"
            "- **Email**: g.ranjith@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the dean of mechanical engineering": {
        "answer": (
            "The handbook lists the following leadership contact for **Mechanical Engineering (ME, SOE)**:\n\n"
            "- **Assistant Dean**: Dr. M. Vijay Reddy\n"
            "- **Phone**: 7735983617\n"
            "- **Email**: vijay.reddy@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the hod of mechanical engineering": {
        "answer": (
            "The handbook lists the following leadership contact for **Mechanical Engineering (ME, SOE)**:\n\n"
            "- **Assistant Dean**: Dr. M. Vijay Reddy\n"
            "- **Phone**: 7735983617\n"
            "- **Email**: vijay.reddy@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the dean of civil engineering": {
        "answer": (
            "The handbook lists the following leadership contact for **Civil Engineering (CE, SOE)**:\n\n"
            "- **Assistant Dean**: Dr. Gaurav Tyagi\n"
            "- **Phone**: 9717696258\n"
            "- **Email**: gaurav.tyagi@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the head of civil engineering": {
        "answer": (
            "The handbook lists the following leadership contact for **Civil Engineering (CE, SOE)**:\n\n"
            "- **Assistant Dean**: Dr. Gaurav Tyagi\n"
            "- **Phone**: 9717696258\n"
            "- **Email**: gaurav.tyagi@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the dean of ece": {
        "answer": (
            "The handbook lists the following leadership contact for **Electronics & Communication Engineering (ECE, SOE)**:\n\n"
            "- **Assistant Dean**: Dr. Kallepelli Sagar\n"
            "- **Phone**: 99590 26505\n"
            "- **Email**: rajkumar.k@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the hod of ece": {
        "answer": (
            "The handbook lists the following leadership contact for **Electronics & Communication Engineering (ECE, SOE)**:\n\n"
            "- **Assistant Dean**: Dr. Kallepelli Sagar\n"
            "- **Phone**: 99590 26505\n"
            "- **Email**: rajkumar.k@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the dean of eee": {
        "answer": (
            "The handbook lists the following leadership contact for **Electrical & Electronics Engineering (EEE, SOE)**:\n\n"
            "- **Assistant Dean**: Dr. B. Sathyavani\n"
            "- **Phone**: 99087 60926\n"
            "- **Email**: b.sathyavani@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the dean of business": {
        "answer": (
            "The handbook lists the following leadership contact for the **School of Business (SOB)**:\n\n"
            "- **Assistant Dean**: Dr. D. Ramesh Babu\n"
            "- **Phone**: 94946 13402\n"
            "- **Email**: rameshbabu.d@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the dean of agriculture": {
        "answer": (
            "The handbook lists the following leadership contact for the **School of Agriculture (SOA)**:\n\n"
            "- **Assistant Dean**: Dr. Pandit Vaibhav Bhagwan\n"
            "- **Phone**: 9359179778\n"
            "- **Email**: pandit.vaibhavbhagwan@sru.edu.in\n\n"
            "The handbook lists department and assistant dean contacts rather than a separate full Dean's name. For university-wide leadership, check the official directory at `sru.edu.in`.\n\n"
            "Would you like the contact details for other departments or student welfare?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the dean of innovation": {
        "answer": (
            "The handbook lists the following leadership contacts for **Innovation and Startups (NEST)**:\n\n"
            "- **Dean, Innovation and Startups**: Dr. B. Girirajan (Phone: 8525002366, Email: girirajan.b@sru.edu.in)\n"
            "- **Associate Dean**: Dr. A. Chakradhar (Phone: 9908246759, Email: chakradhar.a@sru.edu.in)\n\n"
            "Would you like information on incubation programs at NEST or student startup funding?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "who is the dean of student welfare": {
        "answer": (
            "The **Office of the Dean of Student Welfare (SW)** oversees student welfare, campus engagement, hostel concerns, and grievances:\n\n"
            "- **Official Email**: `dean.sw@sru.edu.in`\n"
            "- **Appeals**: Decisions of the Associate Dean (SW) may be appealed to the Dean (SW), and further to the Vice-Chancellor.\n\n"
            "Would you like details on the grievance redressal procedure or student council representatives?"
        ),
        "citations": ["Handbook 2026-27 p.52"],
    },
    "who is the director of alumni": {
        "answer": (
            "The handbook lists the following leadership contacts for **Alumni Affairs**:\n\n"
            "- **Director**: Dr. C. Madan Kumar (Phone: 6281814067, Email: dir.alumni@sru.edu.in)\n"
            "- **Associate Director**: Mr. Srikanth Yalabaka (Phone: 95056 05467, Email: srikanth.v@sru.edu.in)\n"
            "- **Portal**: `https://srualumni.in`\n\n"
            "Would you like information on alumni chapter events or student mentorship programs?"
        ),
        "citations": ["Handbook 2026-27 p.54"],
    },
    "what are the anti ragging rules": {
        "answer": (
            "SR University enforces a **zero-tolerance policy** against ragging:\n\n"
            "- **Definition**: Any act of physical abuse, mental harassment, teasing, or humiliation against any student is strictly classified as ragging.\n"
            "- **Penalties**: Students found guilty face immediate suspension, debarment from examinations, withholding of results, cancellation of admission, or permanent expulsion.\n"
            "- **Reporting**: Incidents can be reported directly to the **Anti-Ragging Committee**, the Office of Dean Student Welfare (`dean.sw@sru.edu.in`), or campus security.\n\n"
            "Would you like contact details for the Anti-Ragging squad or the grievance appeal procedure?"
        ),
        "citations": ["Handbook 2026-27 p.7", "Handbook 2026-27 p.82", "Handbook 2026-27 p.85"],
    },
    "what are the anti ragging rules here": {
        "answer": (
            "SR University enforces a **zero-tolerance policy** against ragging:\n\n"
            "- **Definition**: Any act of physical abuse, mental harassment, teasing, or humiliation against any student is strictly classified as ragging.\n"
            "- **Penalties**: Students found guilty face immediate suspension, debarment from examinations, withholding of results, cancellation of admission, or permanent expulsion.\n"
            "- **Reporting**: Incidents can be reported directly to the **Anti-Ragging Committee**, the Office of Dean Student Welfare (`dean.sw@sru.edu.in`), or campus security.\n\n"
            "Would you like contact details for the Anti-Ragging squad or the grievance appeal procedure?"
        ),
        "citations": ["Handbook 2026-27 p.7", "Handbook 2026-27 p.82", "Handbook 2026-27 p.85"],
    },
    "anti ragging rules": {
        "answer": (
            "SR University enforces a **zero-tolerance policy** against ragging:\n\n"
            "- **Definition**: Any act of physical abuse, mental harassment, teasing, or humiliation against any student is strictly classified as ragging.\n"
            "- **Penalties**: Students found guilty face immediate suspension, debarment from examinations, withholding of results, cancellation of admission, or permanent expulsion.\n"
            "- **Reporting**: Incidents can be reported directly to the **Anti-Ragging Committee**, the Office of Dean Student Welfare (`dean.sw@sru.edu.in`), or campus security.\n\n"
            "Would you like contact details for the Anti-Ragging squad or the grievance appeal procedure?"
        ),
        "citations": ["Handbook 2026-27 p.7", "Handbook 2026-27 p.82", "Handbook 2026-27 p.85"],
    },
    "what is the minimum pass marks for b tech courses": {
        "answer": (
            "For undergraduate (B.Tech) courses under R23 regulations (pp. 72, 77):\n\n"
            "- **Course Pass Requirement**: A student must secure a minimum **grade point of 5.0** (corresponding to **50% marks** in the course/end-term assessment) to pass the course.\n"
            "- **Aggregate D Grade**: A minimum of **40% pass marks in aggregate** is required for awarding a D grade to an undergraduate student.\n"
            "- **Re-examination**: Students securing less than 50% in the end-term theory or practical examination must appear for re-examination.\n\n"
            "*(Citing R23 Handbook p. 72, p. 77)*"
        ),
        "citations": ["R23 Handbook p.72", "R23 Handbook p.77"],
    },
    "how many total credits are required to graduate in regular b tech": {
        "answer": (
            "According to the official university regulations (R23 Handbook p. 59):\n\n"
            "- **Regular B.Tech Duration**: 4 academic years (8 regular semesters).\n"
            "- **Prescribed Graduation Credits**: A student must earn a total of **160 credits** to graduate and receive the B.Tech degree.\n\n"
            "*(Citing R23 Handbook p. 59)*"
        ),
        "citations": ["R23 Handbook p.59"],
    },
    "how many credits are required for lateral entry b tech students": {
        "answer": (
            "For Lateral Entry B.Tech students (admitted directly into the 2nd year / 3rd semester):\n\n"
            "- **Prescribed Graduation Credits**: Lateral entry students must earn **120 credits** under R23 regulations (p. 59) or between **110 and 130 credits** under Handbook 2026-27 (p. 19).\n"
            "- **First-Year Exemption**: Lateral entry students are not required to complete the 160 credits prescribed for regular 4-year students.\n\n"
            "*(Citing R23 Handbook p. 59, Handbook 2026-27 p. 19)*"
        ),
        "citations": ["R23 Handbook p.59", "Handbook 2026-27 p.19"],
    },
    "what happens if a student secures a grade point below 5 0": {
        "answer": (
            "Under university regulations (R23 Handbook p. 77 / Handbook 2026-27 p. 30):\n\n"
            "- **Grade Awarded**: Securing a grade point below 5.0 results in an **'F' (Fail) grade**.\n"
            "- **Consequences**: The student fails that course and cannot earn credits for it.\n"
            "- **Academic Recovery**: The student must register and appear for the immediate **supplementary examination** or repeat the course during summer/winter term to clear the backlog.\n\n"
            "*(Citing R23 Handbook p. 77, Handbook 2026-27 p. 30)*"
        ),
        "citations": ["R23 Handbook p.77", "Handbook 2026-27 p.30"],
    },
    "what is the minimum pass marks for postgraduate programs": {
        "answer": (
            "For postgraduate (PG) and Ph.D. programs:\n\n"
            "- **Passing Threshold**: A student must secure a minimum of **50% to 60% aggregate marks** across continuous evaluation and semester examinations.\n"
            "- **Minimum Grade Point**: A minimum grade point of **6.0** is required to pass postgraduate courses.\n\n"
            "*(Citing Handbook 2026-27 p. 34, p. 57, R23 Handbook p. 69)*"
        ),
        "citations": ["Handbook 2026-27 p.34", "Handbook 2026-27 p.57", "R23 Handbook p.69"],
    },
    "how is sgpa calculated at sr university": {
        "answer": (
            "The Semester Grade Point Average (SGPA) is calculated for each semester using the official university formula (Handbook 2026-27 p. 31 / R23 p. 61):\n\n"
            "$$\\text{SGPA} = \\frac{\\sum (C_i \\times G_i)}{\\sum C_i}$$\n\n"
            "- **$C_i$**: Number of credits assigned to course $i$.\n"
            "- **$G_i$**: Grade point equivalent to the letter grade obtained by the student in course $i$.\n"
            "- **Interpretation**: SGPA represents the credit-weighted average of grade points earned in all courses registered during that semester.\n\n"
            "*(Citing Handbook 2026-27 p. 31, R23 Handbook p. 61)*"
        ),
        "citations": ["Handbook 2026-27 p.31", "R23 Handbook p.61"],
    },
    "what are the academic promotion criteria to move to the 2nd and 3rd year in b tech": {
        "answer": (
            "Academic promotion criteria for B.Tech students (R23 Handbook p. 78 / Handbook 2026-27 p. 81):\n\n"
            "- **Promotion to 2nd Year**: A candidate is automatically promoted to the second year irrespective of courses failed in the first year (or with minimum 40% credits / CGPA ≥ 4.50 under 2026-27 regulations).\n"
            "- **Promotion to 3rd Year**: A candidate must pass all first-year courses compulsorily without backlogs and register for all second-year courses (or earn at least 50% credits / CGPA ≥ 5.00).\n\n"
            "*(Citing R23 Handbook p. 78, Handbook 2026-27 p. 81)*"
        ),
        "citations": ["R23 Handbook p.78", "Handbook 2026-27 p.81"],
    },
    "what is the minimum attendance percentage required to appear for semester end exams": {
        "answer": (
            "According to official attendance regulations (Handbook 2026-27 p. 29, p. 81 / R23 Handbook p. 65):\n\n"
            "- **Minimum Attendance**: A student must maintain a minimum of **75% attendance** in each course (theory and practical separately) during the semester.\n"
            "- **Exam Eligibility**: Maintaining 75% attendance is mandatory to be eligible to appear for the End Semester Examination (ESE).\n\n"
            "*(Citing Handbook 2026-27 p. 29, Handbook 2026-27 p. 81, R23 Handbook p. 65)*"
        ),
        "citations": ["Handbook 2026-27 p.29", "Handbook 2026-27 p.81", "R23 Handbook p.65"],
    },
    "can a student get condonation if attendance is 68": {
        "answer": (
            "Yes, a student with 68% attendance is eligible to apply for attendance condonation (Handbook 2026-27 p. 56, p. 81 / R23 p. 65, p. 66):\n\n"
            "- **Eligibility Band**: Condonation of attendance shortage up to 10% is permissible for attendance between **65% and 75%**.\n"
            "- **Requirements**: Condonation is granted on genuine **medical grounds** upon submitting valid medical certificates and paying the prescribed condonation fee.\n\n"
            "*(Citing Handbook 2026-27 p. 56, Handbook 2026-27 p. 81, R23 Handbook p. 66)*"
        ),
        "citations": ["Handbook 2026-27 p.56", "Handbook 2026-27 p.81", "R23 Handbook p.66"],
    },
    "what happens if my attendance is below 65": {
        "answer": (
            "If your attendance falls below 65% in any course (Handbook 2026-27 p. 30, p. 56 / R23 p. 66):\n\n"
            "- **No Condonation**: Attendance shortage below 65% cannot be condoned under any circumstances.\n"
            "- **Detention**: The student is deemed **detained** in that course and awarded an **'R' (Repeat) grade**.\n"
            "- **Repetition**: The student is not eligible to take the End Semester Examination for that course and must repeat the course during summer/winter or subsequent regular offerings.\n\n"
            "*(Citing Handbook 2026-27 p. 30, Handbook 2026-27 p. 56, R23 Handbook p. 66)*"
        ),
        "citations": ["Handbook 2026-27 p.30", "Handbook 2026-27 p.56", "R23 Handbook p.66"],
    },
    "what is the fee for attendance condonation and where must medical certificates be submitted": {
        "answer": (
            "For attendance condonation (Handbook 2026-27 p. 56 / R23 Handbook p. 66):\n\n"
            "- **Condonation Fee**: The prescribed condonation fee is **Rs. 1,000** (levied in proportion to condonation as per regulations).\n"
            "- **Submission**: Genuine medical certificates and supporting leave documents must be submitted to the **Head of Department (HOD)** or **Dean** within the notified timeline.\n\n"
            "*(Citing R23 Handbook p. 66, Handbook 2026-27 p. 56)*"
        ),
        "citations": ["R23 Handbook p.66", "Handbook 2026-27 p.56"],
    },
    "how is attendance recorded for students participating in university sports or technical events": {
        "answer": (
            "For students representing SR University in official events (Handbook 2026-27 p. 29, p. 81 / R23 p. 65):\n\n"
            "- **Duty Attendance**: Students officially participating in inter-university sports tournaments, hackathons, technical paper presentations, or cultural competitions are granted **duty attendance** / leave of absence.\n"
            "- **Approval**: Prior formal approval from the faculty in-charge and the **Dean / Head of Department** must be obtained and submitted to the attendance office.\n\n"
            "*(Citing Handbook 2026-27 p. 29, Handbook 2026-27 p. 81, R23 Handbook p. 65)*"
        ),
        "citations": ["Handbook 2026-27 p.29", "Handbook 2026-27 p.81", "R23 Handbook p.65"],
    },
    "what is the procedure for answer script revaluation": {
        "answer": (
            "The procedure for answer script review and re-evaluation is as follows (Handbook 2026-27 pp. 32-33 / R23 p. 72):\n\n"
            "1. **Answer Script Review**: Students are provided a scheduled session by their department to review evaluated answer booklets and discuss discrepancies directly with the course instructor.\n"
            "2. **Re-evaluation Application**: Students dissatisfied after the review or who missed the session may apply for formal re-evaluation by submitting an application to the **Examination Branch** within the prescribed deadline.\n"
            "3. **Fee & Finality**: The prescribed re-evaluation fee must be paid. The outcome of re-evaluation is final and binding.\n\n"
            "*(Citing Handbook 2026-27 p. 32, Handbook 2026-27 p. 33, R23 Handbook p. 72)*"
        ),
        "citations": ["Handbook 2026-27 p.32", "Handbook 2026-27 p.33", "R23 Handbook p.72"],
    },
    "what is the minimum pass marks required in end term theory exam": {
        "answer": (
            "For the end-semester (external) theory examination (Handbook 2026-27 p. 34, p. 57 / R23 p. 72, p. 77):\n\n"
            "- **Qualifying Passing Marks**: A student must secure a minimum of **50% marks** (or 40% aggregate in R23 for D grade) in the end-term theory examination to pass the course.\n"
            "- **Grade Point 5.0**: Securing at least 50% marks corresponds to Grade Point 5.0 (Grade C or P), which is the minimum pass threshold.\n\n"
            "*(Citing Handbook 2026-27 p. 34, Handbook 2026-27 p. 57, R23 Handbook p. 77)*"
        ),
        "citations": ["Handbook 2026-27 p.34", "Handbook 2026-27 p.57", "R23 Handbook p.77"],
    },
    "when can a student register for supplementary examinations if they fail a course": {
        "answer": (
            "According to university regulations (Handbook 2026-27 p. 34 / R23 p. 71):\n\n"
            "- **Eligibility**: Students awarded an **'F' (Fail) grade** may register for the immediate **Supplementary Examination**.\n"
            "- **Attempts**: Only **one supplementary attempt** is permitted per course.\n"
            "- **Exam Format**: The supplementary examination is conducted for 100 marks.\n"
            "- **Grade Capping**: The maximum grade that may be awarded through a supplementary examination is **'C'**.\n\n"
            "*(Citing Handbook 2026-27 p. 34, R23 Handbook p. 71)*"
        ),
        "citations": ["Handbook 2026-27 p.34", "R23 Handbook p.71"],
    },
    "what penalties does the committee for prevention of academic malpractice cpam impose for exam misconduct": {
        "answer": (
            "The Committee for Prevention of Academic Malpractice (CPAM) investigates examination misconduct and imposes graded penalties (Handbook 2026-27 pp. 34-35 / R23 pp. 82-85):\n\n"
            "- **Category 1 (Possession of unauthorized material / chits)**: Cancellation of performance in that specific paper.\n"
            "- **Category 2 (Copying / aiding copying)**: Cancellation of all examinations of that semester and debarment from supplementary exams.\n"
            "- **Severe Offences (Impersonation / violence / leakage)**: Debarment from examinations for 1–2 years, cancellation of admission, or permanent expulsion from the university.\n\n"
            "*(Citing Handbook 2026-27 p. 34, Handbook 2026-27 p. 35, R23 Handbook p. 82)*"
        ),
        "citations": ["Handbook 2026-27 p.34", "Handbook 2026-27 p.35", "R23 Handbook p.82"],
    },
    "what are the entry timings and curfew for girls hostel": {
        "answer": (
            "For the Girls Hostel at SR University (Handbook 2026-27 pp. 20, 23, 84-86):\n\n"
            "- **Curfew / Entry Cutoff**: Students must return to the hostel by **6:00 PM** (or 6:30 PM / 7:00 PM with special permission).\n"
            "- **Outings**: Residents are permitted two local outings per week; Sunday outing is permitted up to 6:00 PM.\n"
            "- **Biometric Roll Call**: Mandatory night biometric attendance is conducted between 8:30 PM and 9:30 PM.\n"
            "- **In-Charge**: Ms. S. Shobha Rani (Phone: 9701578799, GH-1 Desk).\n\n"
            "*(Citing Handbook 2026-27 p. 20, Handbook 2026-27 p. 84, Handbook 2026-27 p. 86)*"
        ),
        "citations": ["Handbook 2026-27 p.20", "Handbook 2026-27 p.84", "Handbook 2026-27 p.86"],
    },
    "what is the fine for arriving late to hostel or missing biometric roll call for girls hostel": {
        "answer": (
            "Hostel regulations regarding biometric roll call and punctuality (Handbook 2026-27 pp. 23, 84, 86):\n\n"
            "- **Biometric Attendance**: Roll call is strictly recorded between 8:30 PM and 9:30 PM daily.\n"
            "- **Disciplinary Action**: Arriving late or missing biometric roll call without prior approved leave attracts a disciplinary fine (ranging from **Rs. 100 to Rs. 500**), written warnings, and notification to parents.\n"
            "- **Hostel In-Charge**: Ms. S. Shobha Rani (GH-1 Desk, 9701578799).\n\n"
            "*(Citing Handbook 2026-27 p. 20, Handbook 2026-27 p. 84, Handbook 2026-27 p. 86)*"
        ),
        "citations": ["Handbook 2026-27 p.20", "Handbook 2026-27 p.84", "Handbook 2026-27 p.86"],
    },
    "how do hostel residents apply for an out pass in girls hostel": {
        "answer": (
            "To apply for an out-pass in the Girls Hostel (Handbook 2026-27 pp. 20, 48, 84):\n\n"
            "- **Application**: Residents must submit an out-pass request through the **SRAAP mobile app / portal** or submit a written application to the Hostel In-Charge.\n"
            "- **Parent Verification**: Prior consent or confirmation from the registered parent/guardian is mandatory before the gate pass is approved.\n"
            "- **Hostel Desk**: Ms. S. Shobha Rani (Phone: 9701578799, GH-1 Desk).\n\n"
            "*(Citing Handbook 2026-27 p. 20, Handbook 2026-27 p. 48, Handbook 2026-27 p. 84)*"
        ),
        "citations": ["Handbook 2026-27 p.20", "Handbook 2026-27 p.48", "Handbook 2026-27 p.84"],
    },
    "who manages technical support and help desk for sraap portal": {
        "answer": (
            "For technical support and help desk inquiries regarding the SRAAP ERP portal (Handbook 2026-27 p. 25, p. 54):\n\n"
            "- **SRAAP Support Lead**: Mr. D. Kishore (Email: `sraap@sru.edu.in`)\n"
            "- **IT / ERP Technical Team**: Mr. B. Kiran Babu (Phone: 9849206771, Email: `kiranbabu.b@sru.edu.in`) at IT/ERP Centre.\n\n"
            "*(Citing Handbook 2026-27 p. 25, Handbook 2026-27 p. 54)*"
        ),
        "citations": ["Handbook 2026-27 p.25", "Handbook 2026-27 p.54"],
    },
    "what can students do on the sraap portal": {
        "answer": (
            "The SR Academic and Administration Portal (SRAAP) provides comprehensive digital student services (Handbook 2026-27 pp. 3, 6, 9, 25):\n\n"
            "- **Attendance Tracking**: View daily subject-wise attendance and attendance percentage in real time.\n"
            "- **Marks & Results**: Check internal continuous evaluation marks, midterm scores, and semester end grades.\n"
            "- **Course Registration**: Complete semester course registration and select electives.\n"
            "- **Fee Payments**: Pay tuition and examination fees online and download official fee receipts.\n"
            "- **Academic Timetable**: View weekly class schedules, room allocations, and syllabus.\n\n"
            "*(Citing Handbook 2026-27 p. 3, Handbook 2026-27 p. 6, Handbook 2026-27 p. 25)*"
        ),
        "citations": ["Handbook 2026-27 p.3", "Handbook 2026-27 p.6", "Handbook 2026-27 p.25"],
    },
    "what are the official university working timings": {
        "answer": (
            "Official university working timings (Handbook 2026-27 p. 5, p. 21, p. 54):\n\n"
            "- **Academic & Instruction Hours**: **9:00 AM to 4:45 PM** (or 5:00 PM for administrative offices), Monday through Saturday (excluding declared holidays).\n"
            "- **Central Library**: Open Monday to Friday **8:00 AM to 8:00 PM**, Saturday/Sunday **10:00 AM to 4:00 PM**, with Reading Hall accessible until 10:00 PM.\n\n"
            "*(Citing Handbook 2026-27 p. 5, Handbook 2026-27 p. 21, Handbook 2026-27 p. 54)*"
        ),
        "citations": ["Handbook 2026-27 p.5", "Handbook 2026-27 p.21", "Handbook 2026-27 p.54"],
    },
    "what are the central library working hours and borrowing limits for undergraduate students": {
        "answer": (
            "Central Library details from Handbook 2026-27 (pp. 21-22):\n\n"
            "- **Working Hours**: Monday to Friday **8:00 AM to 8:00 PM**; Saturday and Sunday **10:00 AM to 4:00 PM**; Reading Hall open daily until **10:00 PM**.\n"
            "- **Circulation Counter**: Weekdays **9:30 AM to 6:00 PM**.\n"
            "- **UG Borrowing Privilege**: Undergraduate students can borrow up to **4 books** for a period of **1 month**.\n"
            "- **Overdue Charges**: Re. 1/- per day per book.\n"
            "- **Librarian**: Mr. Sammi Reddy (Phone: 0870-2818384, Email: `librarian@sru.edu.in`).\n\n"
            "*(Citing Handbook 2026-27 p. 21, Handbook 2026-27 p. 22)*"
        ),
        "citations": ["Handbook 2026-27 p.21", "Handbook 2026-27 p.22"],
    },
    "what is sr university s policy on anti ragging and what are the penalties for violations": {
        "answer": (
            "SR University enforces a **zero-tolerance policy** against ragging under UGC Regulations 2009 (Handbook 2026-27 pp. 7, 82, 85):\n\n"
            "- **Definition**: Any act of physical abuse, mental harassment, teasing, or humiliation against any student is strictly classified as ragging.\n"
            "- **Penalties**: Penalties imposed by the Anti-Ragging Committee include suspension from classes or hostel, withholding of scholarships and results, debarment from examinations, and permanent rustication or expulsion.\n"
            "- **Reporting**: Report directly to the Anti-Ragging Committee or Dean of Student Welfare (`dean.sw@sru.edu.in`).\n\n"
            "*(Citing Handbook 2026-27 p. 7, Handbook 2026-27 p. 82, Handbook 2026-27 p. 85)*"
        ),
        "citations": ["Handbook 2026-27 p.7", "Handbook 2026-27 p.82", "Handbook 2026-27 p.85"],
    },
    "what happens if a student is caught with slips or chits during exam": {
        "answer": (
            "If you are suspected of using unauthorized slips or chits during an examination (Handbook 2026-27 pp. 24, 62):\n\n"
            "- **Immediate Action**: The invigilator will seize your answer script and any supporting evidence (including slips), and request a written statement.\n"
            "- **Continuation**: You may be issued a fresh answer booklet to complete the examination.\n"
            "- **Investigation**: The Committee for Prevention of Academic Malpractice (CPAM) reviews all evidence and conducts a hearing.\n"
            "- **Penalties**: Based on severity, CPAM may cancel your performance in that course or all semester courses, and may recommend suspension or expulsion.\n\n"
            "*(Citing Handbook 2026-27 p. 24, Handbook 2026-27 p. 62)*"
        ),
        "citations": ["Handbook 2026-27 p.24", "Handbook 2026-27 p.62"],
    },
    "who should i contact for campus wi fi network connection issues": {
        "answer": (
            "For campus Wi-Fi network connection and IT access support at SR University (Handbook 2026-27 pp. 19, 23, 54):\n\n"
            "- **IT In-Charge**: Mr. A. Bala Krishna (Phone: `8886522500`, Email: `a.balakrishna@sru.edu.in`)\n"
            "- **IT Support**: Mr. E. Manikanta (Phone: `8008917297`, Email: `e.maikantayadav@sru.edu.in`)\n"
            "- **Office / Location**: IT Services Cell / Computer Center Desk.\n\n"
            "*(Citing Handbook 2026-27 p. 19, Handbook 2026-27 p. 23, Handbook 2026-27 p. 54)*"
        ),
        "citations": ["Handbook 2026-27 p.19", "Handbook 2026-27 p.23", "Handbook 2026-27 p.54"],
    },
    "who manages university bus passes and transport routes": {
        "answer": (
            "University bus transport registration, routes, and bus passes are managed by the Transport Department at SR University (Handbook 2026-27 pp. 7, 20, 54):\n\n"
            "- **Transport In-Charge**: Mr. B. Ramesh (Phone: `9963310699`) / Mr. A. Keerthi Reddy (Phone: `9640606408`)\n"
            "- **Office Location**: Block-I, Room No. 1002\n"
            "- **Routes Covered**: Warangal, Kazipet, Hanamkonda, Karimnagar, Husnabad, and Jammikunta.\n\n"
            "*(Citing Handbook 2026-27 p. 7, Handbook 2026-27 p. 20, Handbook 2026-27 p. 54)*"
        ),
        "citations": ["Handbook 2026-27 p.7", "Handbook 2026-27 p.20", "Handbook 2026-27 p.54"],
    },
    "what is the contact number for administrative officer ao inquiries": {
        "answer": (
            "For Administrative Officer (AO) inquiries regarding campus administrative coordination and hostel operations at SR University (Handbook 2026-27 pp. 20, 23, 54):\n\n"
            "- **Administrative Officer (AO)**: Mr. Ch. Vinay Kumar\n"
            "- **Official Contact Number**: `9966001761`\n"
            "- **Official Email**: `c.vinaykumarreddy@sru.edu.in`\n"
            "- **Location**: Administrative Office / Hostel Administrative Desk\n\n"
            "*(Citing Handbook 2026-27 p. 20, Handbook 2026-27 p. 23, Handbook 2026-27 p. 54)*"
        ),
        "citations": ["Handbook 2026-27 p.20", "Handbook 2026-27 p.23", "Handbook 2026-27 p.54"],
    },
    "who oversees student welfare and grievance appeals at sr university": {
        "answer": (
            "Student welfare, campus grievance redressal, student council activities, and appeals are overseen by the Office of the Dean of Student Welfare at SR University (Handbook 2026-27 pp. 52, 54):\n\n"
            "- **Office**: Dean of Student Welfare (DSW)\n"
            "- **Official Email**: `dean.sw@sru.edu.in`\n"
            "- **Appeals**: Students with unresolved grievances may submit appeals to the Vice-Chancellor.\n\n"
            "*(Citing Handbook 2026-27 p. 52, Handbook 2026-27 p. 54)*"
        ),
        "citations": ["Handbook 2026-27 p.52", "Handbook 2026-27 p.54"],
    },
    "where can i apply for my transfer certificate tc and bonafide certificate": {
        "answer": (
            "Student certificates including Transfer Certificate (TC), Bonafide Certificate, Study Certificate, and Custodian at SR University (Handbook 2026-27 pp. 6, 20, 54):\n\n"
            "- **Service / Counter**: Student Help Desk & Certificate Section\n"
            "- **In-Charge**: Ms. Jupaka Ramadevi (Phone: `9963084035`, Email: `j.ramadevi@sru.edu.in`)\n"
            "- **Office Location**: Block-I, Room No. 1002\n"
            "- **Timings**: Up to 5:00 PM on official working days.\n\n"
            "*(Citing Handbook 2026-27 p. 6, Handbook 2026-27 p. 20, Handbook 2026-27 p. 54)*"
        ),
        "citations": ["Handbook 2026-27 p.6", "Handbook 2026-27 p.20", "Handbook 2026-27 p.54"],
    },
}

_CACHE = dict(_VERIFIED_FAQ)


def _normalize_question(question):
    """If a student pastes a tool-call-shaped JSON string, unwrap it to the
    real question. e.g. '{"query": "promotion policy", "topk": 5}' -> the
    text inside query (ignoring numeric args). Anything else is returned
    unchanged."""
    q = (question or "").strip()
    if not q.startswith("{"):
        return q
    try:
        obj = json.loads(q)
        if isinstance(obj, dict):
            inner = obj.get("query") or obj.get("question") or obj.get("message")
            if isinstance(inner, str) and inner.strip():
                return inner.strip()
    except Exception:  # noqa: BLE001 - not JSON -> treat as plain text
        pass
    return q


def _strip_fences(text):
    """Remove a surrounding ```json / ``` code fence if present."""
    s = (text or "").strip()
    lines = s.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _looks_like_tool_call(text):
    """True when the entire reply is a raw tool-call payload (the failure mode
    where the model echoes {"query": ...} instead of answering)."""
    t = _strip_fences(text)
    if not t:
        return False
    if re.search(r"(?:search_handbook|calculator|search_web)\s*\(", t):
        return True
    if not t.startswith("{"):
        return False
    try:
        obj = json.loads(t)
    except Exception:  # noqa: BLE001 - not clean JSON
        return False
    if isinstance(obj, dict) and any(k in obj for k in _TOOL_KEYS):
        return True
    return False


def _cleanup_answer(raw):
    """Strip stray tool-call JSON fragments that slipped into an otherwise
    good answer (e.g. '{"query": "..."}' inline). Empty result signals the
    caller to regenerate."""
    t = _strip_fences(raw or "").strip()
    if not t:
        return ""
    # Remove quoted tool args embedded in the text.
    t = re.sub(
        r"\{\s*\"(?:query|expression)\"\s*:\s*\"[^\"]*\""
        r"(?:\s*,\s*\"(?:top_k|topk|k)\"\s*:\s*\d+\s*)?\}",
        "",
        t,
    )
    # Remove function-call spellings like search_handbook({"query": ...}).
    t = re.sub(r"(?:search_handbook|calculator|search_web|function_call)\s*\([^)]*\)", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    # Remove dangling incomplete bullet/list lines at the end of generation
    t = re.sub(r"\n\s*[-*•]\s*(?:\*\*)?[A-Za-z0-9\s]{0,35}$", "", t).strip()
    if t.count("**") % 2 == 1:
        t += "**"
    return t


def _cites_from(text):
    """Extract '<label> p.N' citation strings from retrieved text blocks."""
    return {f"{label.strip()} p.{page}" for label, page in CITE_RE.findall(text or "")}


def _contextual_search_query(question, history):
    """If the student's question is a short conversational clarification or batch
    statement (e.g. '2023-24 batch', 'R23', '23-24', 'yes tell me more', 'what about cse?'),
    combine it with the previous substantive question so the retriever finds the actual
    subject in the right regulation."""
    q = (question or "").strip()
    ckey = _cache_key(q)
    if ckey in _GREETINGS or ckey in _ACKNOWLEDGEMENTS:
        return q
    if re.search(r"\bp(?:age|\.)\s*\d+\b", q, re.I):
        return q
    words = q.split()
    if len(words) <= 5 and history:
        for m in reversed(history):
            if isinstance(m, dict) and m.get("role") == "user":
                prev = (m.get("content") or "").strip()
                prev_ckey = _cache_key(prev)
                if prev_ckey in _GREETINGS or prev_ckey in _ACKNOWLEDGEMENTS:
                    continue
                if prev and prev.lower() != q.lower():
                    return f"{prev} {q}"
    return q


def _auto_context(question, history=None, profile=None):
    """Always retrieve for the newest question; guarantees grounded answers
    even when the model chooses not to call tools. Uses conversational reformulation
    so follow-ups ('2023-24 batch') retrieve the prior topic from the intended regulation."""
    retriever = get_retriever()
    search_q = _contextual_search_query(question, history)
    text, cites = retriever.format_hits(search_q, top_k=AUTO_CONTEXT_TOP_K, history=history, profile=profile)
    if not cites:
        return None

    # Live personnel overlay reminder for hostel / curfew / administrative personnel
    combined_q = f"{question} {history[-1].get('content', '') if history else ''}".lower()
    overlay_note = ""
    if re.search(r"\b(hostel|warden|curfew|late|out-?pass|gate\s*pass|night\s*out|bh-?\d?|gh-?\d?)\b", combined_q):
        overlay_note = (
            "\n\n[AUTHORITATIVE DIRECTORY OVERRIDE: Active Girls Hostel In-Charge is Ms. S. Shobha Rani (Phone: 9701578799, GH-1 Desk); "
            "Active Boys Hostel Manager is Mr. A. Surender (Phone: 9989671719, BH-2 Desk); "
            "Administrative Officer (Hostels) is Mr. Ch. Vinay Kumar (Phone: 9966001761). "
            "Under no circumstances quote obsolete 2023 names like Ms. Anitha GP or Dr. Rupesh Mishra.]"
        )
    elif re.search(r"\b(tc|transfer\s+certificate|bonafide|study\s+certificate|migration|custodian|help\s+desk|id\s+card)\b", combined_q):
        overlay_note = (
            "\n\n[AUTHORITATIVE DIRECTORY OVERRIDE: Student Certificates (TC, Bonafide, Migration, Custodian) are issued by "
            "Ms. Jupaka Ramadevi (Phone: 9963084035, Email: j.ramadevi@sru.edu.in) at Block-I, Room No. 1002 (Student Help Desk) up to 5:00 PM on working days.]"
        )

    return (
        f"Auto-retrieved handbook context for the student's question "
        f"(pages {', '.join(cites)}):\n\n{text}{overlay_note}\n\n"
        "Use this context first; you may still call search_handbook for more."
    )


def _trim_history(history, keep=MAX_HISTORY):
    clean = []
    for m in history[-keep:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            clean.append({"role": role, "content": content})
    return clean


PROFILE_KEYS = ("programme", "branch", "stream", "degree", "entry_type", "year", "semester", "batch", "regulation", "roll_number")


def _profile_block(profile):
    if not isinstance(profile, dict):
        return "\n\nSTUDENT PROFILE: unknown"
    parts = []
    for k in PROFILE_KEYS:
        v = str(profile.get(k, "") or "").strip()
        if v:
            parts.append(f"{k}={v[:40]}")
    if not parts:
        return "\n\nSTUDENT PROFILE: unknown"
    block = "\n\nSTUDENT PROFILE: " + "; ".join(parts)
    if profile.get("is_lateral_entry"):
        block += "\n[LATERAL ENTRY CANDIDATE: Admitted directly into 2nd year (Semester III). Prescribed graduation credits: 110–130 credits (Handbook 2026-27 p. 19 / R23 p. 59, 91), NEVER 160 credits. 1st-year promotion checks are not applicable.]"
    if profile.get("regulation_disclaimer"):
        block += f"\n[REGULATION STATUS: {profile['regulation_disclaimer']}]"
    return block


def run_agent(question, history=None, profile=None):
    """Returns {"answer", "citations", "tool_calls", "mode"}.

    A deterministic clarify pre-pass (zero LLM cost) fires first for ambiguous
    questions (Boys/Girls hostel, programme/branch) so the model never guesses
    and serves the wrong side's info. A deterministic count pre-pass fires next
    for "how many clubs" style questions so exact numbers never depend on the
    model's arithmetic.
    """
    # 0. Scope & Jailbreak boundary check
    out_of_scope = check_out_of_scope(question)
    if out_of_scope:
        return out_of_scope

    # Normalize student slang & shortcuts
    raw_question = _normalize_question(question)
    raw_ckey = _cache_key(raw_question)
    question = normalize_student_text(raw_question)
    ckey = _cache_key(question)

    # 1. Roll Number Extraction & Identification pass
    detected_roll = parse_roll_number(question)
    if detected_roll:
        # Check validation bounds
        if not detected_roll.get("is_valid", True):
            return {
                "answer": (
                    f"⚠️ **Enrollment Number Verification Notice:**\n\n"
                    f"The roll number `{detected_roll['roll_number']}` could not be validated:\n"
                    f"- **Reason:** {detected_roll['validation_error']}\n\n"
                    f"**Suggestions:**\n"
                    f"- Please verify your 10-digit roll number format (e.g., `2303A51001` or `2403L51001`).\n"
                    f"- If you are a prospective, guest, or alumni student, feel free to ask your academic or campus questions directly without a roll number!"
                ),
                "citations": ["Handbook 2026-27 p.8"],
                "tool_calls": [],
                "mode": "invalid_roll_number",
                "profile": profile,
                "retrieval_ms": 0.0,
                "llm_ms": 0.0,
            }

        active_profile = dict(profile or {})
        active_profile.update(detected_roll)
        badge = format_student_badge(detected_roll)
        
        # If the query was purely declaring the roll number
        cleaned_no_roll = re.sub(r"(?i)\b(my\s+(roll\s*(no|number)|htno|id)\s*(is)?|roll\s*(no|number)|enrollment\s*number|htno|i\s*am|my\s*id\s*is|is|am|here\s*is)\b", "", question).strip()
        cleaned_no_roll = re.sub(r"\b" + re.escape(detected_roll["roll_number"]) + r"\b", "", cleaned_no_roll, flags=re.I).strip()
        cleaned_no_roll = re.sub(r"[^a-zA-Z0-9]+", "", cleaned_no_roll).strip()
        
        if not cleaned_no_roll or len(cleaned_no_roll) <= 3:
            disclaimer_part = f"\n\nℹ️ **Notice:** {detected_roll['regulation_disclaimer']}" if detected_roll.get("regulation_disclaimer") else ""
            
            if detected_roll.get("is_lateral_entry"):
                msg = (
                    f"🎓 **Lateral Entry Student Profile Identified:**\n\n"
                    f"- **Roll / Enrollment Number:** `{detected_roll['roll_number']}`\n"
                    f"- **Entry Pathway:** Lateral Entry (Admitted directly to Semester III / 2nd Year)\n"
                    f"- **Degree & Branch:** {detected_roll['degree']} · {detected_roll['program']}\n"
                    f"- **School:** {detected_roll['school']}\n"
                    f"- **Batch & Regulation:** {detected_roll['batch']} ({detected_roll['regulation']})\n"
                    f"- **Academic Standing:** {detected_roll.get('study_status', 'Active Student')}\n"
                    f"- **Prescribed Graduation Credits:** {detected_roll['prescribed_credits']}\n"
                    f"- **Academic Promotion:** {detected_roll['promotion_summary']}"
                    f"{disclaimer_part}\n\n"
                    f"Welcome! I have tailored my knowledge specifically to your lateral entry curriculum and regulation criteria. "
                    f"What would you like to check regarding your required credits, pass marks, attendance, or promotion rules?"
                )
            else:
                msg = (
                    f"🎓 **Student Profile Identified:**\n\n"
                    f"- **Roll / Enrollment Number:** `{detected_roll['roll_number']}`\n"
                    f"- **Degree:** {detected_roll['degree']}\n"
                    f"- **Branch / Stream:** {detected_roll['program']}\n"
                    f"- **School:** {detected_roll['school']}\n"
                    f"- **Batch & Regulation:** {detected_roll['batch']} ({detected_roll['regulation']}, citing {detected_roll['handbook_doc']})\n"
                    f"- **Academic Standing:** {detected_roll.get('study_status', 'Active Student')}\n"
                    f"- **Prescribed Graduation Credits:** {detected_roll['prescribed_credits']}"
                    f"{disclaimer_part}\n\n"
                    f"Welcome! I have tailored my knowledge to your specific regulations. "
                    f"What would you like to check regarding your curriculum, pass marks, attendance, or promotion rules?"
                )

            return {
                "answer": msg,
                "citations": [f"{detected_roll['handbook_doc']} p.8"],
                "tool_calls": [],
                "mode": "profile_identified",
                "profile": active_profile,
                "retrieval_ms": 0.0,
                "llm_ms": 0.0,
            }
        else:
            # The student provided a question alongside their roll number: update profile and continue!
            profile = active_profile

    # Check if query explicitly declares lateral entry without a roll number
    if re.search(r"\b(lateral entry|lateral student|diploma entry|ecet)\b", question, re.I):
        if not isinstance(profile, dict):
            profile = {}
        profile["is_lateral_entry"] = True
        profile["entry_type"] = "Lateral Entry"
        if not profile.get("degree"):
            profile["degree"] = "B.Tech (Lateral Entry)"

    if ckey in _GREETINGS:
        has_roll = isinstance(profile, dict) and profile.get("roll_number")
        roll_prompt = (
            f"You are currently identified as **{format_student_badge(profile)}**."
            if has_roll else
            "💡 **Tip:** Share your **10-digit Roll Number** (e.g., `2303A51001`) anytime so I can automatically apply the exact rules for your branch and batch!"
        )
        return {
            "answer": (
                "Hello! 👋 I'm **AURA** (Autonomous University RAG Agent), your official student handbook assistant.\n\n"
                f"{roll_prompt}\n\n"
                "I can help you with:\n"
                "- **Academics**: Promotion rules, grading scale, SGPA/CGPA calculation, and pass marks\n"
                "- **Examinations**: Mid/End-sem rules, revaluation, condonation, and malpractice policies\n"
                "- **Campus Life**: Hostels, Wi-Fi, dress code, scholarships, clubs, and department contacts\n\n"
                "What would you like to know today?"
            ),
            "citations": [],
            "tool_calls": [],
            "mode": "greeting",
        }

    if ckey in _ACKNOWLEDGEMENTS:
        return {
            "answer": (
                "You're welcome! Feel free to ask anytime if you need help with university regulations, "
                "attendance, grading, hostel policies, or official department contacts."
            ),
            "citations": [],
            "tool_calls": [],
            "mode": "acknowledgement",
        }

    # Fast path: Check verified FAQ / handbook cache first
    active_cache_key = raw_ckey if (raw_ckey in _CACHE) else (ckey if ckey in _CACHE else None)
    if not history and active_cache_key:
        hit = _CACHE[active_cache_key]
        return {
            "answer": hit["answer"],
            "citations": hit["citations"],
            "tool_calls": [],
            "mode": "cached",
            "retrieval_ms": 0.0,
            "llm_ms": 0.0,
        }

    # Live Personnel Directory Override (Named Officials, Wardens, Deans)
    contact_hit = match_contact_override(question)

    CONTACT_INTENT_RE = re.compile(
        r"\b(who|whom|incharge|in-charge|warden|manager|contact|phone|mobile|number|email|mail|reach|where is|office of|desk|counter|person|in charge|ao|head)\b",
        re.I,
    )
    NAMED_OFFICIAL_RE = re.compile(
        r"\b(vinay|surender|surendar|shobha|sagar|ranjith|tyagi|sathyavani|vijay reddy|ramesh babu|vaibhav|girirajan|madan kumar|sai kumar|pavani|benson|swapna|kishore|purnima|bala krishna|kiran babu|sammi reddy|sridhar|rajeshwar)\b",
        re.I,
    )
    is_seeking_contact = bool(
        CONTACT_INTENT_RE.search(question)
        or NAMED_OFFICIAL_RE.search(question)
        or (history and any(CONTACT_INTENT_RE.search(m.get("content", "")) for m in history[-2:] if isinstance(m, dict) and m.get("role") == "user"))
    )

    if not contact_hit and history and is_seeking_contact:
        user_msgs = [m.get("content", "") for m in history if isinstance(m, dict) and m.get("role") == "user"]
        if user_msgs:
            contact_hit = match_contact_override(f"{question} {user_msgs[-1]}")

    is_general_policy_query = bool(
        re.search(r"\b(how much|what is the fee|fee amount|fine|fines|penalty|penalties|structure|refund|rules|policy|curfew|allowed|timings|attendance|pass mark|credits|detention|out-pass|outpass|leave|ragging|biometric|slips|misconduct|revaluation)\b", question, re.I)
    )

    if contact_hit and is_seeking_contact and not is_general_policy_query:
        contact_res = format_contact_response(contact_hit)
        contact_res["cta"] = generate_cta(question, contact_record=contact_hit, profile=profile)
        if isinstance(profile, dict) and "roll_number" in profile:
            contact_res["profile"] = profile
        return contact_res

    clarify = clarify_check(question, history, profile)
    if clarify:
        return clarify
    counts = counts_check(question, history, profile)
    if counts:
        return counts

    if not history and ckey in _CACHE:
        hit = _CACHE[ckey]
        return {
            "answer": hit["answer"],
            "citations": hit["citations"],
            "tool_calls": [],
            "mode": "cached",
        }

    if _fast_mode():
        result = _fast_answer(question, history, profile)
    else:
        result = _agentic_answer(question, history, profile)

    # Attach contextual CTA only if query indicates actionable grievance / contact
    active_contact = contact_hit if is_seeking_contact else None
    cta_payload = generate_cta(question, contact_record=active_contact, profile=profile, answer_text=result.get("answer", ""))
    if cta_payload:
        result["cta"] = cta_payload

    # Attach profile if updated
    if isinstance(profile, dict) and "roll_number" in profile:
        result["profile"] = profile

    if not history and result.get("mode") in ("fast", "agent") and "experiencing high network demand" not in result.get("answer", ""):
        _CACHE[ckey] = result

    result.setdefault("retrieval_ms", 0.0)
    result.setdefault("llm_ms", 0.0)
    return result


def _fast_mode():
    """Default is fast (single call). AGENT_MODE=agent re-enables the loop."""
    return os.environ.get("AGENT_MODE", "fast").lower() != "agent"


def _fast_answer(question, history, profile):
    """One LLM call, no tools, tool-free system prompt. Grounded purely by
    auto-retrieved context; tricked into echoing {"query":...} it regenerates
    a grounded answer instead."""
    history = _trim_history(history or [], keep=FAST_HISTORY)
    citations = set()
    profile_line = _profile_block(profile)

    messages = [{"role": "system", "content": FAST_SYSTEM_PROMPT + profile_line}]
    messages.extend(history)

    t_ret_0 = time.perf_counter()
    ctx = _auto_context(question, history=history, profile=profile)
    retrieval_ms = round((time.perf_counter() - t_ret_0) * 1000, 2)

    user_msg = question if not ctx else f"{question}\n\n[system note] {ctx}"
    messages.append({"role": "user", "content": user_msg})

    t_llm_0 = time.perf_counter()
    try:
        reply = llm.chat(messages, tools=None, max_tokens=_max_tokens())
        llm_ms = round((time.perf_counter() - t_llm_0) * 1000, 2)
    except Exception:
        llm_ms = round((time.perf_counter() - t_llm_0) * 1000, 2)
        answer = _finalize_answer("", messages, question)
        citations |= _cites_from(ctx or "")
        return {
            "answer": answer,
            "citations": sorted(citations),
            "tool_calls": [],
            "mode": "fast-fallback",
            "retrieval_ms": retrieval_ms,
            "llm_ms": llm_ms,
        }

    answer = _finalize_answer(reply.content, messages, question)
    citations |= _cites_from(ctx or "")

    return {
        "answer": answer,
        "citations": sorted(citations),
        "tool_calls": [],
        "mode": "fast",
        "retrieval_ms": retrieval_ms,
        "llm_ms": llm_ms,
    }


def _finalize_answer(raw, messages, question):
    """Turn a raw model reply into a usable answer. If the model echoed a
    tool-call JSON or produced nothing, regenerate a grounded answer."""
    if _looks_like_tool_call(raw):
        raw = ""
    clean = _cleanup_answer(raw)
    if not clean:
        return _grounded_answer(messages, question)
    return clean


def _agentic_answer(question, history, profile):
    """Full agentic loop with tools (AGENT_MODE=agent)."""
    history = _trim_history(history or [])
    citations = set()
    used_tools = []
    profile_line = _profile_block(profile)

    messages = [{"role": "system", "content": SYSTEM_PROMPT + profile_line}]
    messages.extend(history)

    t_ret_0 = time.perf_counter()
    ctx = _auto_context(question, history=history, profile=profile)
    retrieval_ms = round((time.perf_counter() - t_ret_0) * 1000, 2)

    user_msg = question if not ctx else f"{question}\n\n[system note] {ctx}"
    messages.append({"role": "user", "content": user_msg})

    specs = tools.tool_specs(enable_web=bool(_web_enabled()))

    llm_ms_total = 0.0
    t_llm_0 = time.perf_counter()
    try:
        reply = llm.chat(messages, tools=specs, max_tokens=_max_tokens())
        llm_ms_total += (time.perf_counter() - t_llm_0) * 1000
    except Exception:
        llm_ms_total += (time.perf_counter() - t_llm_0) * 1000
        # Model/provider rejected tools -> plain grounded answer path.
        answer = _grounded_answer(messages, question)
        return {
            "answer": answer,
            "citations": sorted(citations),
            "tool_calls": used_tools,
            "mode": "rag-fallback",
            "retrieval_ms": retrieval_ms,
            "llm_ms": round(llm_ms_total, 2),
        }

    step = 0
    while getattr(reply, "tool_calls", None) and step < MAX_STEPS:
        step += 1
        messages.append(
            {
                "role": "assistant",
                "content": reply.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in reply.tool_calls
                ],
            }
        )
        for tc in reply.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = tools.execute(name, args)
            used_tools.append({"tool": name, "args": args})
            if name == "search_handbook":
                citations |= _cites_from(result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result[:6000],
                }
            )

        t_llm_step = time.perf_counter()
        try:
            reply = llm.chat(messages, tools=specs, max_tokens=_max_tokens())
            llm_ms_total += (time.perf_counter() - t_llm_step) * 1000
        except Exception:
            llm_ms_total += (time.perf_counter() - t_llm_step) * 1000
            answer = _grounded_answer(messages, question)
            return {
                "answer": answer,
                "citations": sorted(citations),
                "tool_calls": used_tools,
                "mode": "rag-fallback-midloop",
                "retrieval_ms": retrieval_ms,
                "llm_ms": round(llm_ms_total, 2),
            }

    answer = _finalize_answer(reply.content, messages, question)

    # Merge pages the model saw via auto-context into citations.
    citations |= _cites_from(ctx or "")

    return {
        "answer": answer,
        "citations": sorted(citations),
        "tool_calls": used_tools,
        "mode": "agent",
        "retrieval_ms": retrieval_ms,
        "llm_ms": round(llm_ms_total, 2),
    }


def _max_tokens():
    try:
        return int(os.environ.get("MAX_TOKENS", "4096"))
    except ValueError:
        return 4096


def _grounded_answer(messages, question):
    """No-tool safety net: last 6 retrieved chunks + direct instruction."""
    text, cites = get_retriever().format_hits(question, top_k=6)
    trimmed = [m for m in messages if m["role"] in ("user", "assistant")]
    msgs = [
        {"role": "system", "content": FALLBACK_PROMPT},
        *trimmed[-6:],
        {"role": "user", "content": f"HANDBOOK CONTEXT:\n{text}\n\nQUESTION: {question}"},
    ]
    try:
        reply = llm.chat(msgs, tools=None)
        clean = _cleanup_answer(reply.content or "")
        if _looks_like_tool_call(clean):
            return "I couldn't retrieve a clear answer from the handbook for that question. Please contact the Student Help Desk."
        return clean or "I couldn't find that in the handbook. Please contact the Student Help Desk."
    except Exception:
        if cites and text:
            raw_blocks = re.split(r"(?:---|===== PAGE \d+ =====)", text)
            cleaned_paras = []
            for block in raw_blocks:
                cleaned = re.sub(r"\[.*?page \d+\]", "", block).strip()
                lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
                joined = []
                for ln in lines:
                    if not joined:
                        joined.append(ln)
                    elif ln.startswith(("-", "*", "•")) or (len(ln) > 2 and ln[0].isdigit() and ln[1] in ".)"):
                        joined.append("\n- " + ln.lstrip("-*• 0123456789.)").strip())
                    elif joined[-1].endswith((".", ":", ";", "?", "!")):
                        joined.append("\n" + ln)
                    else:
                        joined[-1] += " " + ln
                para = "\n".join(joined).strip()
                if len(para) > 40:
                    cleaned_paras.append(para[:350])
            snippet = "\n\n".join(cleaned_paras[:2])
            if snippet:
                return (
                    f"**Handbook Policy Excerpt:**\n\n"
                    f"{snippet}\n\n"
                    f"*(Citing {', '.join(cites[:3])})*\n\n"
                    f"Would you like me to elaborate on any specific section?"
                )
        return "The handbook assistant is currently experiencing high network demand. Please try again in a moment or contact the Student Help Desk."



def _web_enabled():
    import os

    return os.environ.get("ENABLE_WEB_SEARCH", "true").lower() != "false"
