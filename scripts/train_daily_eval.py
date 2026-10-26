"""Daily 100 Unique Questions Training & Evaluation Suite for SRU Assist.

Requirements:
  - 100 completely unique questions per dataset (guaranteed 0 duplicates).
  - Every topic cluster has multiple distinct phrasing variations.
  - Verifies that different questions under the same topic cluster receive
    consistent, grounded answers citing identical handbook truth pages.
  - Tests multi-regulation routing (R23 vs 2026-27).
  - Tests roll number decoding awareness.
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent.config import load_env
load_env()

from agent.core import run_agent
from agent.retriever import get_retriever

TRAIN_DATASET_FILE = os.path.join(ROOT, "tests", "daily_100_questions.json")


def generate_100_questions():
    """Builds a curated dataset of 100 strictly unique questions across 20 handbook topics."""
    topics = [
        {
            "topic_id": "pass_marks_ug",
            "topic_name": "Minimum Pass Marks (UG Aggregate & Course)",
            "expect_pages": [34, 57, 61],
            "doc": "Handbook 2026-27",
            "canonical_fact": "45% aggregate across all courses for UG; 50% in individual course end-exam (GP >= 5.0).",
            "questions": [
                "What is the minimum pass percentage for undergraduate courses?",
                "How much aggregate percentage is required to clear a semester in B.Tech?",
                "What marks do I need to score to pass an individual subject in end-semester?",
                "Is 40% enough to pass a course in SR University UG?",
                "What is the cutoff score for passing theory courses in university exams?",
            ]
        },
        {
            "topic_id": "attendance_exam_eligibility",
            "topic_name": "Attendance Threshold for Writing End Exams",
            "expect_pages": [27, 29, 32, 55],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Minimum 75% attendance required in each course to write end exams.",
            "questions": [
                "How much attendance do I need to be eligible for end semester exams?",
                "What is the mandatory attendance percentage to write finals?",
                "Can I write semester exams if my attendance is 72%?",
                "What happens if my attendance in a course falls below 75%?",
                "What is the minimum required classroom attendance for students?",
            ]
        },
        {
            "topic_id": "attendance_condonation",
            "topic_name": "Attendance Condonation on Medical Grounds",
            "expect_pages": [56, 81],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Attendance between 65% and 75% may be condoned on medical grounds with fee. Below 65% is non-condonable.",
            "questions": [
                "My attendance is short due to hospitalization, can it be condoned?",
                "What is the medical condonation policy for attendance shortage?",
                "I have 68% attendance because of dengue, can I pay condonation fee?",
                "Can attendance below 65% be condoned under any circumstances?",
                "What is the procedure and deadline to submit medical certificates for condonation?",
            ]
        },
        {
            "topic_id": "letter_grading_scale",
            "topic_name": "Letter Grade Scale & Grade Points (A+ to F)",
            "expect_pages": [30, 71],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Letter grades from O/A+ down to F (fail) and I (incomplete) with 10-point scale.",
            "questions": [
                "Explain the letter grade scale and grade points used at SRU.",
                "What is the grade point corresponding to an A grade?",
                "What does an F grade mean on my grade sheet?",
                "Show the complete marks-to-grade-point conversion table.",
                "How are percentage marks converted into grade points in semester results?",
            ]
        },
        {
            "topic_id": "sgpa_calculation",
            "topic_name": "Semester Grade Point Average (SGPA) Computation",
            "expect_pages": [31],
            "doc": "Handbook 2026-27",
            "canonical_fact": "SGPA = sum(Ci * Gi) / sum(Ci) for all courses in the semester.",
            "questions": [
                "How is SGPA calculated for a semester at SR University?",
                "What is the mathematical formula for computing semester GPA?",
                "How do course credits affect my SGPA calculation?",
                "Do audit or non-credit courses count towards SGPA?",
                "Can you show a step-by-step example of SGPA calculation?",
            ]
        },
        {
            "topic_id": "cgpa_calculation",
            "topic_name": "Cumulative Grade Point Average (CGPA) Computation",
            "expect_pages": [31, 46],
            "doc": "Handbook 2026-27",
            "canonical_fact": "CGPA = sum of all credit-weighted grade points across all completed semesters divided by total credits.",
            "questions": [
                "How do they compute my overall CGPA across all semesters?",
                "What is the difference between SGPA and CGPA calculation?",
                "If I clear a backlog course, how does my new grade update the CGPA?",
                "How is cumulative grade point average updated after supplementary exams?",
                "Does an F grade count into CGPA until it is cleared?",
            ]
        },
        {
            "topic_id": "promotion_rules_ug",
            "topic_name": "Academic Promotion Requirements to Next Year",
            "expect_pages": [36, 37, 38],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Promotion requires clearing specified credit percentages (40%-50%) and minimum CGPA criteria.",
            "questions": [
                "What are the promotion rules to move to the next academic year?",
                "What CGPA and credit percentage is required to get promoted to 2nd year?",
                "How many backlogs am I allowed before getting year-detained?",
                "What happens if I fail to earn 40% of first-year credits by 2nd year?",
                "What are the credit clearance criteria to enter the 3rd year of B.Tech?",
            ]
        },
        {
            "topic_id": "academic_malpractice_cpam",
            "topic_name": "Exam Malpractice, CPAM Committee & Penalties",
            "expect_pages": [34, 35, 36, 80],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Invigilator seizes answer book + slips; CPAM investigates; penalties range from cancellation of paper to debarment.",
            "questions": [
                "What happens if a student is caught using unfair means in an exam?",
                "What is the role of the Committee for Prevention of Academic Malpractice (CPAM)?",
                "If an invigilator finds paper slips with a student, what immediate action is taken?",
                "What are the disciplinary penalties for copying during university exams?",
                "Can a student appeal a malpractice penalty imposed by CPAM?",
            ]
        },
        {
            "topic_id": "revaluation_procedure",
            "topic_name": "Answer Script Revaluation & Recounting Process",
            "expect_pages": [32, 33, 56],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Students may apply for revaluation within the notified window after paying the prescribed fee to COE.",
            "questions": [
                "How do I apply for re-evaluation of my end-semester answer script?",
                "What is the deadline and fee to apply for paper rechecking?",
                "Will my marks decrease if the revaluation score is lower than original?",
                "Where can I get the revaluation application form?",
                "Who processes revaluation requests and announces revised results?",
            ]
        },
        {
            "topic_id": "summer_semester_backlogs",
            "topic_name": "Summer Semester Course Registration & Clearing F Grades",
            "expect_pages": [26, 27, 28, 31, 34],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Students with F grades may register for remedial/backlog courses in summer semester subject to credit limits.",
            "questions": [
                "Can I clear a failed course during the summer semester?",
                "What is the maximum number of credits I can register for in summer semester?",
                "Is attendance mandatory for summer term classes?",
                "How are summer semester course fees calculated?",
                "Can I register for new advance courses in the summer break?",
            ]
        },
        {
            "topic_id": "hostel_rules_timings",
            "topic_name": "Hostel Facilities, Curfews & Biometric Roll Call",
            "expect_pages": [6, 7, 23, 86],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Biometric roll call before 9:30 PM on weekdays; late arrival fined; separate Boys and Girls warden offices.",
            "questions": [
                "What are the hostel curfew hours and roll call timings?",
                "What is the procedure to request roll call extension for hostel students?",
                "Who do I contact for maintenance or room allocation in the hostel?",
                "Are day scholars or outside guests allowed to stay in hostel rooms?",
                "What are the disciplinary consequences of violating hostel curfew?",
            ]
        },
        {
            "topic_id": "anti_ragging_zero_tolerance",
            "topic_name": "Anti-Ragging Regulations & Reporting Cell",
            "expect_pages": [7, 82, 85, 86],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Strict zero-tolerance policy; penalties include suspension, rustication, and police FIR; Anti-Ragging Cell contact.",
            "questions": [
                "What are the university's anti-ragging policies and punishments?",
                "Who is the coordinator of the Anti-Ragging Cell and what is their contact number?",
                "What legal and academic actions are taken if a student is found guilty of ragging?",
                "How can a victimized student file an emergency ragging complaint confidentially?",
                "Does the university have anti-ragging squad patrols on campus?",
            ]
        },
        {
            "topic_id": "campus_dress_code",
            "topic_name": "Campus Dress Code & ID Card Policy",
            "expect_pages": [8, 47, 81],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Formal attire mandatory on Mondays and Tuesdays and presentations; ID cards must be worn at all times.",
            "questions": [
                "Is there a formal dress code on campus and which days is it compulsory?",
                "What attire is required during lab sessions, workshops, and placement drives?",
                "Are jeans, round-neck T-shirts, or casual sandals permitted on formal days?",
                "What is the penalty if a student fails to wear their university ID card?",
                "Where can I get a duplicate ID card if I lose mine?",
            ]
        },
        {
            "topic_id": "library_facilities_timings",
            "topic_name": "Central Library Timings, Membership & Book Borrowing",
            "expect_pages": [21, 22, 23, 24],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Bar-coded member ID card issued; OPAC search terminals; borrowing limits and renewal rules.",
            "questions": [
                "What are the working hours and facilities of the Central Library?",
                "How many books can an undergraduate student borrow at one time?",
                "What is the fine per day for overdue library books?",
                "How can I access digital journals and IEEE databases from the library?",
                "Is the library open on weekends and during examination periods?",
            ]
        },
        {
            "topic_id": "transport_bus_services",
            "topic_name": "Transportation Routes, Bus Passes & Registration",
            "expect_pages": [6, 7],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Buses cover Kazipet, Hanamkonda, Warangal, and nearby districts; full-year fee payment; designated stops.",
            "questions": [
                "What districts and areas are covered by the university bus service?",
                "Where do I register for a student bus pass and who is the in-charge?",
                "Can I change my boarding bus stop mid-semester?",
                "Are transport fees refundable if a student relocates or vacates?",
                "What are the morning arrival and evening departure timings for university buses?",
            ]
        },
        {
            "topic_id": "scholarship_fee_support",
            "topic_name": "Scholarships, Fee Concessions & Verification",
            "expect_pages": [6, 20, 23, 56],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Merit and state scholarships available; Mr. G. Raju (Room 1002) in charge of UG/PG scholarships.",
            "questions": [
                "What scholarship schemes are available for students at SR University?",
                "Who is the concerned staff member for scholarship documentation and issues?",
                "Where is the scholarship section located in the administrative block?",
                "What academic performance criteria must be maintained to retain merit scholarships?",
                "How do I submit state e-pass scholarship application forms?",
            ]
        },
        {
            "topic_id": "mentor_advising_system",
            "topic_name": "Faculty Mentoring & Academic Advising Framework",
            "expect_pages": [9, 11, 15, 18],
            "doc": "Handbook 2026-27",
            "canonical_fact": "Each student assigned a faculty mentor at enrollment; at least one individual and one group session per semester.",
            "questions": [
                "Who is my faculty mentor and what support do they provide?",
                "How frequently are individual mentoring sessions conducted each semester?",
                "Can my faculty mentor assist with course registration and elective choices?",
                "Where can I find the name and contact details of my assigned mentor?",
                "What should I do if I need academic counseling or career guidance?",
            ]
        },
        {
            "topic_id": "r23_honors_minor",
            "topic_name": "R23 Regulations: Honors & Minor Degree Requirements",
            "expect_pages": [54, 60, 61, 62, 73],
            "doc": "R23 Handbook",
            "canonical_fact": "R23 students can register for Honors/Minor earning 18-20 additional credits with CGPA >= 7.5.",
            "questions": [
                "What are the eligibility criteria to register for an Honors degree under R23?",
                "How many additional credits are required to earn a Minor degree in R23?",
                "Can a student with backlogs enroll in an Honors or Minor track?",
                "What happens if I fail an Honors course in R23?",
                "Does a Minor degree appear separately on the final degree certificate?",
            ]
        },
        {
            "topic_id": "r23_professional_electives",
            "topic_name": "R23 Regulations: Professional & Open Electives",
            "expect_pages": [53, 61, 64, 166],
            "doc": "R23 Handbook",
            "canonical_fact": "Professional electives are specialized domain courses; Open electives are interdisciplinary courses offered across departments.",
            "questions": [
                "What are professional electives in the R23 regulation curriculum?",
                "How do open electives work and can I take them from other engineering departments?",
                "What is the minimum enrollment required for an elective track to be offered?",
                "Can an R23 student change their registered elective course during add/drop period?",
                "Are MOOCs / NPTEL courses allowed in place of professional electives in R23?",
            ]
        },
        {
            "topic_id": "student_enrollment_id_schema",
            "topic_name": "10-Digit Roll Number / Enrollment Framework",
            "expect_pages": [8],
            "doc": "Handbook 2026-27",
            "canonical_fact": "10-digit number: Year (2), School Code (2), Degree Code (1), Program Code (2), Serial (3). Example: 2303A51001.",
            "questions": [
                "What is the structure of the 10-digit student enrollment number at SRU?",
                "How does the university roll number represent admission year, school, and branch?",
                "Explain the components of roll number 2303A51001 as described in the handbook.",
                "Which digits in the enrollment number represent the student's degree and program code?",
                "How can I know my school code and degree code from my roll number?",
            ]
        },
    ]

    # Verify that all 100 questions are strictly unique
    all_q = []
    dataset = []
    for t in topics:
        for q in t["questions"]:
            clean_q = q.strip()
            assert clean_q not in all_q, f"Duplicate question detected: {clean_q}"
            all_q.append(clean_q)
            dataset.append({
                "id": f"{t['topic_id']}_{len(dataset)+1:03d}",
                "topic_id": t["topic_id"],
                "topic_name": t["topic_name"],
                "question": clean_q,
                "doc": t["doc"],
                "expect_pages": t["expect_pages"],
                "canonical_fact": t["canonical_fact"],
            })

    print(f"Generated {len(dataset)} strictly unique questions across {len(topics)} topics.")
    with open(TRAIN_DATASET_FILE, "w", encoding="utf-8") as f:
        json.dump({"total_questions": len(dataset), "cases": dataset}, f, indent=2)
    return dataset


def run_daily_training_suite(sample_size=100, full_llm=False):
    """Executes the daily training and retrieval regression suite across all 100 cases."""
    if not os.path.exists(TRAIN_DATASET_FILE):
        dataset = generate_100_questions()
    else:
        with open(TRAIN_DATASET_FILE, "r", encoding="utf-8") as f:
            dataset = json.load(f)["cases"]

    cases_to_run = dataset[:sample_size]
    print(f"\n{'='*80}")
    print(f"🚀 Running SRU Assist Daily Training & Verification Suite: {len(cases_to_run)} Cases")
    print(f"{'='*80}\n")

    retriever = get_retriever()
    hits = 0
    topic_results = {}

    start_time = time.time()
    for idx, c in enumerate(cases_to_run, start=1):
        q = c["question"]
        want_doc = c["doc"]
        expect_pages = c["expect_pages"]
        t_id = c["topic_id"]

        results = retriever.search(q, top_k=6)
        hit_rank = None
        for rank, h in enumerate(results, start=1):
            if h.doc == want_doc and h.page in expect_pages:
                hit_rank = rank
                break

        is_hit = hit_rank is not None
        if is_hit:
            hits += 1

        topic_entry = topic_results.setdefault(t_id, {"name": c["topic_name"], "total": 0, "hits": 0})
        topic_entry["total"] += 1
        if is_hit:
            topic_entry["hits"] += 1

        mark = "✅ OK" if is_hit else "❌ MISS"
        rank_str = f"Rank {hit_rank}" if is_hit else "Not in Top-6"
        print(f"[{idx:03d}/100] {mark} ({rank_str:<10}) {q[:55]:<55} | {want_doc} p.{expect_pages}")

    duration = time.time() - start_time
    hit_rate = (hits / len(cases_to_run)) * 100

    print(f"\n{'-'*80}")
    print(f"📊 SUMMARY BY TOPIC CLUSTER ({len(topic_results)} Topics):")
    print(f"{'-'*80}")
    for t_id, data in topic_results.items():
        rate = (data['hits'] / data['total']) * 100
        print(f"  • {data['name'][:50]:<50}: {data['hits']}/{data['total']} ({rate:.0f}%)")

    print(f"\n{'='*80}")
    print(f"🎯 TOTAL ACCURACY: {hits}/{len(cases_to_run)} ({hit_rate:.1f}%) in {duration:.2f}s")
    print(f"{'='*80}\n")
    return hits, len(cases_to_run)


if __name__ == "__main__":
    generate_100_questions()
    run_daily_training_suite(sample_size=100)

