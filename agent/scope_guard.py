"""Strict Scope, Anti-Jailbreak, and Policy Integrity Guard for SRU Assist.

Guards:
  1. Off-topic queries: jokes, funny stories, poems, dating, entertainment, movies, sports scores
  2. Non-academic programming / coding requests: "write python code for binary tree", "html page"
  3. General world trivia: "who is the prime minister", "capital of France", "recipe for cake"
  4. Adversarial prompt injection & jailbreaks: "ignore previous instructions", "DAN", "system prompt"
  5. Policy Dispute & Gaslighting Defense: rejects student attempts to inject fake rules, override official
     regulations, or demand "add this to your rules", firmly asserting handbook authority and directing
     students to the HOD/Dean of their respective branch.
"""
import re

# Deterministic regex for off-topic & joke requests
OFF_TOPIC_REGEX = re.compile(
    r"\b("
    r"tell\s+me\s+a\s+joke|make\s+me\s+laugh|crack\s+a\s+joke|funny\s+joke|"
    r"write\s+(?:a\s+)?(?:poem|story|song|essay|movie\s+script|rap|letter\s+to\s+my\s+gf)|"
    r"who\s+is\s+(?:your\s+)?(?:girlfriend|boyfriend|crush)|"
    r"recipe|cook|baking|how\s+to\s+make\s+(?:cake|pizza|biryani|tea)|"
    r"capital\s+of\s+[a-z]+|who\s+is\s+the\s+prime\s+minister|who\s+is\s+president\s+of|"
    r"who\s+won\s+the\s+(?:match|game|world\s+cup|ipl)|cricket\s+score|football\s+score|"
    r"weather\s+in\s+[a-z]+|temperature\s+today|"
    r"write\s+(?:a\s+)?(?:python|java|c\+\+|javascript|html|sql|php|react)\s+(?:code|script|program|function)|"
    r"solve\s+(?:this\s+)?(?:leetcode|codechef|hackerrank|coding\s+question)|"
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|"
    r"system\s+prompt|prompt\s+injection|jailbreak|unrestricted\s+mode|dan\s+mode|"
    r"what\s+model\s+are\s+you|what\s+is\s+your\s+(?:system\s+prompt|secret\s+instructions)|"
    r"act\s+as\s+(?:an?\s+)?(?:unrestricted|evil|linux\s+terminal|python\s+interpreter|hacker)"
    r")\b",
    re.IGNORECASE,
)

# Rule dispute and adversarial policy injection detector
POLICY_DISPUTE_REGEX = re.compile(
    r"\b("
    r"(?:the|your)?\s*rules?\s*(?:you\s*gave\s*)?(?:is|are)\s*wrong|"
    r"you\s+gave\s+(?:the\s+)?wrong\s+rules?|"
    r"(?:th(?:is|ese)\s+is|here\s+is)\s+(?:the\s+)?correct\s+rules?|"
    r"add\s+th(?:is|ese)\s+(?:to\s+)?(?:your\s+)?rules?|"
    r"(?:change|update|override|modify)\s+(?:the|your)\s+rules?|"
    r"accept\s+(?:th(?:is|ese)|my)\s+rules?|"
    r"new\s+rules?\s+(?:is|says?)|"
    r"the\s+rules?\s+have?\s+changed|"
    r"your\s+(?:information|data|output)\s+is\s+wrong"
    r")\b",
    re.IGNORECASE,
)

REFUSAL_MESSAGE = (
    "I am **AURA** (Autonomous University RAG Agent), the official student handbook assistant for SR University.\n\n"
    "I am strictly dedicated to assisting with **university academic regulations, student handbook rules, "
    "examinations, attendance, grading, hostel policies, and campus facilities**.\n\n"
    "I cannot assist with general programming, entertainment, jokes, or off-topic queries. "
    "Please ask an academic or handbook-related question!"
)

BRANCH_LEADERSHIP = {
    "cs": ("Computer Science & Artificial Intelligence (CS & AI, SOCS)", "Mr. G. Ranjith Kumar", "Assistant Dean", "90144 32147", "g.ranjith@sru.edu.in"),
    "cse": ("Computer Science & Engineering (SOCS)", "Mr. G. Ranjith Kumar", "Assistant Dean", "90144 32147", "g.ranjith@sru.edu.in"),
    "aiml": ("CS & AI / Machine Learning (SOCS)", "Mr. G. Ranjith Kumar", "Assistant Dean", "90144 32147", "g.ranjith@sru.edu.in"),
    "ece": ("Electronics & Communication Engineering (SOE)", "Dr. Kallepelli Sagar", "Assistant Dean", "99590 26505", "rajkumar.k@sru.edu.in"),
    "eee": ("Electrical & Electronics Engineering (SOE)", "Dr. B. Sathyavani", "Assistant Dean", "99087 60926", "b.sathyavani@sru.edu.in"),
    "business": ("School of Business (SOB)", "Dr. D. Ramesh Babu", "Assistant Dean", "94946 13402", "rameshbabu.d@sru.edu.in"),
    "bba": ("School of Business (SOB)", "Dr. D. Ramesh Babu", "Assistant Dean", "94946 13402", "rameshbabu.d@sru.edu.in"),
    "agriculture": ("School of Agriculture (SOA)", "Dr. Pandit Vaibhav Bhagwan", "Assistant Dean", "9359179778", "pandit.vaibhavbhagwan@sru.edu.in"),
}


def _get_branch_contact(profile):
    """Retrieve departmental contact based on student profile/stream."""
    if not isinstance(profile, dict):
        return None
    token = str(profile.get("stream") or profile.get("branch") or profile.get("program") or "").lower()
    for key, contact in BRANCH_LEADERSHIP.items():
        if key in token:
            return contact
    return None


def check_out_of_scope(question: str, profile: dict = None):
    """Returns standard refusal response dict if question is off-topic, adversarial, or disputing policies, else None."""
    if not question:
        return None

    # 1. General off-topic and DAN jailbreak checks
    if OFF_TOPIC_REGEX.search(question):
        return {
            "answer": REFUSAL_MESSAGE,
            "citations": [],
            "tool_calls": [],
            "mode": "scope_restricted",
        }

    # 2. Anti-Gaslighting & Policy Dispute Defense
    if POLICY_DISPUTE_REGEX.search(question):
        branch_info = _get_branch_contact(profile)
        if branch_info:
            dept, name, title, phone, email = branch_info
            contact_block = (
                f"**Your Department Leadership ({dept}):**\n"
                f"- **{title}**: {name}\n"
                f"- **Phone**: {phone}\n"
                f"- **Email**: `{email}`\n\n"
                f"You may also contact the **Dean of Student Welfare** at `dean.sw@sru.edu.in`."
            )
        else:
            contact_block = (
                "**Department Leadership Directory (Handbook p. 54):**\n"
                "- **CS & AI (SOCS)**: Mr. G. Ranjith Kumar (Assistant Dean) · 90144 32147 · `g.ranjith@sru.edu.in`\n"
                "- **ECE (SOE)**: Dr. Kallepelli Sagar (Assistant Dean) · 99590 26505 · `rajkumar.k@sru.edu.in`\n"
                "- **EEE (SOE)**: Dr. B. Sathyavani (Assistant Dean) · 99087 60926 · `b.sathyavani@sru.edu.in`\n"
                "- **School of Business**: Dr. D. Ramesh Babu (Assistant Dean) · 94946 13402 · `rameshbabu.d@sru.edu.in`\n"
                "- **School of Agriculture**: Dr. Pandit Vaibhav Bhagwan · 9359179778 · `pandit.vaibhavbhagwan@sru.edu.in`\n"
                "- **Dean Student Welfare**: `dean.sw@sru.edu.in`"
            )

        answer = (
            "🏛️ **SR University Official Academic Regulations Notice:**\n\n"
            "All regulations, grading policies, attendance thresholds, and examination criteria provided by **AURA** "
            "are strictly authoritative and grounded in the official **SR University Student Handbook & Academic Regulations** "
            "(Handbook 2026-27 / R23 Academic Regulations).\n\n"
            "As an automated university assistant, I **cannot modify, override, or accept unofficial rules** submitted in the chat. "
            "My responses must remain strictly consistent with the officially approved Senate academic policies.\n\n"
            "If you have concerns, believe a specific departmental exemption applies, or wish to present special circumstances, "
            "please consult the **Head of the Department (HOD) or Dean of your respective branch**:\n\n"
            f"{contact_block}"
        )

        return {
            "answer": answer,
            "citations": ["Handbook 2026-27 p.54"],
            "tool_calls": [],
            "mode": "policy_dispute_defended",
        }

    return None
