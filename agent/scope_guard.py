"""Strict Scope & Anti-Jailbreak Guard for SRU Assist.

Rejects:
  1. Off-topic queries: jokes, funny stories, poems, dating, entertainment, movies, sports scores
  2. Non-academic programming / coding requests: "write python code for binary tree", "html page"
  3. General world trivia: "who is the prime minister", "capital of France", "recipe for cake"
  4. Adversarial prompt injection & jailbreaks: "ignore previous instructions", "DAN", "system prompt"
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

REFUSAL_MESSAGE = (
    "I am **SRU Assist**, the official student handbook assistant for SR University.\n\n"
    "I am strictly dedicated to assisting with **university academic regulations, student handbook rules, "
    "examinations, attendance, grading, hostel policies, and campus facilities**.\n\n"
    "I cannot assist with general programming, entertainment, jokes, or off-topic queries. "
    "Please ask an academic or handbook-related question!"
)


def check_out_of_scope(question: str):
    """Returns standard refusal response dict if question is off-topic/adversarial, else None."""
    if not question:
        return None

    if OFF_TOPIC_REGEX.search(question):
        return {
            "answer": REFUSAL_MESSAGE,
            "citations": [],
            "tool_calls": [],
            "mode": "scope_restricted",
        }

    return None

