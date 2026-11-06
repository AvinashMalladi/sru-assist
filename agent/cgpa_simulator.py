"""Interactive Target CGPA & Placement Eligibility Simulator for SRU Assist.

Provides mathematical calculations for student academic goal planning:
1. Target CGPA Planner: Calculates required SGPA over upcoming credits to achieve target CGPA.
2. Placement Eligibility Estimator: Explains typical tier-1, dream, and core company CGPA cutoffs
   and backlog rules at SR University.
"""
import re


def simulate_target_cgpa(current_cgpa: float, completed_credits: int, target_cgpa: float, upcoming_credits: int = 20):
    """Calculate the required SGPA in upcoming semesters to achieve target CGPA."""
    if completed_credits <= 0:
        completed_credits = 40  # Default assumption: completed 1st year (2 semesters)
    if upcoming_credits <= 0:
        upcoming_credits = 20   # Default assumption: 1 semester ~ 20 credits

    total_credits = completed_credits + upcoming_credits
    required_points = (target_cgpa * total_credits) - (current_cgpa * completed_credits)
    required_sgpa = required_points / upcoming_credits

    is_achievable_single_sem = required_sgpa <= 10.0
    
    # Also calculate over 2 semesters (40 credits) if single sem is too steep
    two_sem_credits = upcoming_credits * 2
    two_sem_total = completed_credits + two_sem_credits
    two_sem_sgpa = ((target_cgpa * two_sem_total) - (current_cgpa * completed_credits)) / two_sem_credits
    is_achievable_two_sem = two_sem_sgpa <= 10.0

    return {
        "current_cgpa": current_cgpa,
        "completed_credits": completed_credits,
        "target_cgpa": target_cgpa,
        "upcoming_credits": upcoming_credits,
        "required_sgpa": round(required_sgpa, 2),
        "is_achievable_single_sem": is_achievable_single_sem,
        "two_sem_sgpa": round(two_sem_sgpa, 2),
        "is_achievable_two_sem": is_achievable_two_sem,
    }


def format_simulation_response(data: dict):
    """Format simulation results into student-friendly markdown."""
    req = data["required_sgpa"]
    curr = data["current_cgpa"]
    tgt = data["target_cgpa"]
    creds = data["upcoming_credits"]

    if 0 <= req <= 10.0:
        difficulty = "Very Achievable" if req <= 8.5 else "Challenging (Requires consistent A/A+ grades)"
        msg = (
            f"🎯 **Target CGPA Simulation Plan:**\n\n"
            f"- **Current Standing:** `{curr} CGPA` (over {data['completed_credits']} credits)\n"
            f"- **Target Goal:** `{tgt} CGPA`\n"
            f"- **Required SGPA in Next Semester ({creds} credits):** **`{req} SGPA`**\n"
            f"- **Feasibility:** {difficulty}\n\n"
            f"**To reach `{req} SGPA`:** You need an average grade of **{'A (8.0)' if req <= 8.0 else 'A+ (9.0)' if req <= 9.0 else 'O (10.0)'}** "
            f"across all upcoming courses.\n\n"
            f"💡 *Tip: If you maintain `{data['two_sem_sgpa']} SGPA` consistently over the next 2 semesters ({data['upcoming_credits']*2} credits), "
            f"you will hit your target `{tgt} CGPA`!*"
        )
    elif req > 10.0:
        msg = (
            f"🎯 **Target CGPA Simulation Plan:**\n\n"
            f"- **Current Standing:** `{curr} CGPA` (over {data['completed_credits']} credits)\n"
            f"- **Target Goal:** `{tgt} CGPA`\n"
            f"- **Required in 1 Semester ({creds} credits):** `{req} SGPA` ⚠️ *(Mathematically impossible in a single semester as maximum grade point is 10.0)*\n\n"
            f"**Recommended Multi-Semester Roadmap:**\n"
            f"- If you spread this goal over **2 semesters ({data['upcoming_credits']*2} credits)**, you need an average of **`{data['two_sem_sgpa']} SGPA`** "
            f"{'(Achievable with consistent A+ grades!)' if data['is_achievable_two_sem'] else '(Spread over 3 semesters)'}.\n"
            f"- Maximize performance in internal mid-exams and lab assessments to secure maximum grade points."
        )
    else:
        msg = f"You are already above or at your target goal of `{tgt} CGPA`! Keep maintaining an SGPA of `{tgt}` to stay on track."

    msg += (
        f"\n\n**Campus Placement Cutoff Guidelines (Handbook p. 30 / Industry Norms):**\n"
        f"- **Dream / Product Companies (TCS Digital, Amazon, etc.):** Typically require **≥ 7.5 or 8.0 CGPA** with 0 active backlogs.\n"
        f"- **Core & IT Services (Wipro, Infosys, Cognizant):** Typically require **≥ 6.5 or 7.0 CGPA**.\n"
        f"- **Standard Minimum:** Minimum **6.0 CGPA (60% aggregate)** with no standing backlogs at degree completion."
    )
    return msg


def check_cgpa_simulation(question: str):
    """Detect if a question is asking for target CGPA calculation and execute simulation."""
    q = (question or "").lower()

    if not re.search(r"\b(cgpa|sgpa|gpa)\b", q):
        return None
    if not re.search(r"\b(how\s+much|what\s+sgpa|need|reach|get|target|achieve|aim|hit|improve|for)\b", q):
        return None

    nums = [float(x) for x in re.findall(r"\b([1-9]\.[0-9]{1,2}|10\.0|10)\b", q) if 1.0 <= float(x) <= 10.0]
    if len(nums) < 2:
        return None

    # Check 'reach X from Y' or 'for X with current Y'
    m_reach_from = re.search(r"(?:reach|get|target|for)\s*([1-9]\.[0-9]+).*?(?:from|is|have)\s*([1-9]\.[0-9]+)", q)
    if m_reach_from:
        target_val = float(m_reach_from.group(1))
        current_val = float(m_reach_from.group(2))
    else:
        current_val, target_val = nums[0], nums[1]

    # Detect completed credits if specified, else default to 40 (end of 1st year)
    cred_match = re.search(r"(\d+)\s*credits", q)
    completed_credits = int(cred_match.group(1)) if cred_match else 40

    sim_data = simulate_target_cgpa(current_val, completed_credits, target_val, upcoming_credits=20)
    answer = format_simulation_response(sim_data)

    return {
        "answer": answer,
        "citations": ["Handbook 2026-27 p.30"],
        "tool_calls": [],
        "mode": "cgpa_simulator",
    }
