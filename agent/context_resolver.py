"""Multi-turn conversation memory and contextual query resolver for SRU Assist.

Resolves student follow-up responses, short phrases (e.g. 'condonation', 'eligibility',
'F grade', 'second one', 'that one', 'yes'), ordinal choices, and pronouns across
multiple conversation turns, synthesizing a fully grounded semantic query for
BM25 retrieval and LLM context.
"""
import re


ORDINALS = {
    "1": 0, "1st": 0, "first": 0, "first one": 0, "option 1": 0, "number 1": 0, "one": 0,
    "2": 1, "2nd": 1, "second": 1, "second one": 1, "option 2": 1, "number 2": 1, "two": 1,
    "3": 2, "3rd": 2, "third": 2, "third one": 2, "option 3": 2, "number 3": 2, "three": 2,
    "4": 3, "4th": 3, "fourth": 3, "fourth one": 3, "option 4": 3, "number 4": 3, "four": 3,
    "5": 4, "5th": 4, "fifth": 4, "fifth one": 4, "option 5": 4, "number 5": 4, "five": 4,
    "last": -1, "last one": -1,
}

# Semantic expansions for common student follow-up terms
SEMANTIC_EXPANSIONS = {
    # Attendance sub-topics
    "condonation": "attendance condonation eligibility rules 65 to 75 medical certificate Dean approval procedure fee",
    "condone": "attendance condonation eligibility rules 65 to 75 percent medical certificate procedure",
    "minimum attendance": "minimum attendance 75 percent required to write semester examinations eligibility",
    "75": "minimum attendance 75 percent required to write examinations",
    "75%": "minimum attendance 75 percent required to write examinations",
    "below 75": "attendance below 75 percent condonation and detention criteria",
    "below 75%": "attendance below 75 percent condonation and detention criteria",
    "detention": "attendance below 65 percent detention repeat semester cannot write examinations",
    "detained": "attendance below 65 percent detention repeat semester cannot write examinations",
    "duty leave": "attendance duty leave sports nss institutional representation exemption",
    "medical exemption": "attendance medical condonation 65 to 75 percent medical certificate",
    "eligibility": "examination attendance eligibility criteria minimum percentage",

    # Grading & Marks sub-topics
    "f grade": "letter grade F grade points 0 fail backlog supplementary examination",
    "f": "letter grade F grade points 0 fail backlog supplementary examination",
    "sgpa": "SGPA calculation formula semester grade point average credits grade points",
    "cgpa": "CGPA calculation formula cumulative grade point average credits grade points",
    "grade points": "letter grade scale grade points O A+ A B+ B C F 10 point scale",
    "revaluation": "revaluation of answer scripts application procedure fee deadline",
    "recounting": "recounting of marks application procedure fee deadline",
    "improvement": "grade improvement supplementary examination rules",

    # Backlog sub-topics
    "clear backlog": "how to clear backlog supplementary examinations attempts allowed",
    "backlog": "backlog supplementary examinations promotion credits requirements",
    "supplementary": "supplementary examinations registration schedule fee attempts",
    "attempts": "maximum duration and attempts allowed to complete degree",
    "promotion": "academic promotion credit requirements backlogs detention rules",

    # Subjects & Electives sub-topics
    "professional elective": "professional electives course selection departmental electives",
    "open elective": "open electives courses outside parent department interdisciplinary",
    "mooc": "MOOCs NPTEL Coursera online courses credit transfer equivalence committee",
    "nptel": "MOOCs NPTEL online courses credit transfer equivalence committee",
    "honors": "B.Tech Honors degree additional 18 to 20 credits eligibility CGPA",
    "minors": "B.Tech Minor degree additional credits interdisciplinary eligibility",

    # Contact & Support sub-topics
    "examinations": "examination department exam cell controller of examinations contact email examcell@sru.edu.in",
    "placements": "placement department career development cell contact officer email pc.soe@sru.edu.in",
    "fee-related issues": "sraap portal tuition fees payment receipts support contact sraap@sru.edu.in",
    "academic issues": "academic issues department leadership assistant dean hod head contact email phone",
}


def extract_previous_options(history):
    """Extract bulleted or listed options from the most recent assistant message."""
    if not history:
        return []
    for msg in reversed(history):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content", "")
            lines = content.split("\n")
            options = []
            for l in lines:
                # Match bullet formats like '- Option text', '* Option text', '1. Option text'
                m = re.match(r"^\s*(?:[-*•]|\d+\.)\s+(.+?)(?:\?|$)", l)
                if m:
                    opt = m.group(1).strip()
                    # Filter out non-option lines like section headers
                    if len(opt) > 3 and not opt.lower().startswith(("immediate", "continuation", "investigation", "action", "definition", "penalties", "reporting", "undergraduate", "postgraduate", "individual")):
                        # Clean markdown bold/italics
                        clean_opt = re.sub(r"[*_`]", "", opt).strip()
                        options.append(clean_opt)
            if options:
                return options
    return []


def match_student_choice(user_text, options):
    """Match user input against a list of options using ordinals, numbers, or keywords."""
    if not user_text or not options:
        return None

    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", user_text.lower()).strip()
    words = cleaned.split()

    # 1. Check exact ordinal or numeric phrase
    if cleaned in ORDINALS:
        idx = ORDINALS[cleaned]
        if -len(options) <= idx < len(options):
            return options[idx]

    # Check words for ordinals
    for w in words:
        if w in ORDINALS and len(words) <= 3:
            idx = ORDINALS[w]
            if -len(options) <= idx < len(options):
                return options[idx]

    # 2. Check keyword overlap with options
    best_opt = None
    best_score = 0
    for opt in options:
        opt_low = opt.lower()
        score = 0
        for w in words:
            if len(w) >= 3 and w in opt_low:
                score += 1
        if score > best_score:
            best_score = score
            best_opt = opt

    if best_score > 0:
        return best_opt

    return None


def find_active_topic(history):
    """Detect the overarching topic of discussion from the conversation history."""
    if not history:
        return None

    combined_text = []
    for msg in reversed(history[-6:]):
        if isinstance(msg, dict):
            combined_text.append(str(msg.get("content", "")).lower())
    text = " ".join(combined_text)

    if re.search(r"\b(attendance|condonation|condone|detention|detained|absent|shortage)\b", text):
        return "attendance"
    if re.search(r"\b(grade|grades|grading|sgpa|cgpa|marks|revaluation|recounting|f grade|letter grade)\b", text):
        return "grades"
    if re.search(r"\b(backlog|backlogs|fail|failed|failing|supplementary|clear)\b", text):
        return "backlogs"
    if re.search(r"\b(exam|exams|examination|examinations|hall ticket|admit card)\b", text):
        return "exams"
    if re.search(r"\b(subject|subjects|elective|electives|curriculum|syllabus|mooc|nptel|minor|honors)\b", text):
        return "subjects"
    if re.search(r"\b(hostel|mess|warden|room|bh-\d|gh-\d)\b", text):
        return "hostel"
    if re.search(r"\b(promotion|credits|graduation|degree)\b", text):
        return "promotion"

    return None


def resolve_contextual_query(question, history=None, profile=None):
    """Reconstruct a complete, context-rich search query from multi-turn dialogue.

    Returns:
        dict:
            - resolved_query (str): Enriched query for retrieval & model grounding
            - matched_option (str or None): Selected option if student picked one
            - active_topic (str or None): Topic domain (e.g. 'attendance', 'grades')
            - is_continuation (bool): True if this is a follow-up answer in a multi-turn thread
    """
    q = (question or "").strip()
    q_low = q.lower()
    words = q.split()

    options = extract_previous_options(history) if history else []
    matched = match_student_choice(q, options)
    active_topic = find_active_topic(history) if history else None

    # Check if this is a continuation
    is_short = len(words) <= 6
    is_continuation = bool(history and (matched or is_short or active_topic))

    resolved_parts = []

    # 1. If an option was matched, incorporate its semantics
    if matched:
        resolved_parts.append(matched)

    # 2. Check semantic expansions for short student phrases
    for key, expansion in SEMANTIC_EXPANSIONS.items():
        if re.search(r"\b" + re.escape(key) + r"\b", q_low):
            resolved_parts.append(expansion)
            break

    # 3. If there's an active topic, ensure the topic keyword is present
    if active_topic:
        resolved_parts.append(active_topic)

    # 4. Include previous user queries for multi-turn topic coherence
    if history and is_short:
        for m in reversed(history[-4:]):
            if isinstance(m, dict) and m.get("role") == "user":
                prev_text = str(m.get("content", "")).strip()
                if prev_text and prev_text.lower() != q_low:
                    resolved_parts.append(prev_text)
                    break

    # Always keep the original user question text
    resolved_parts.append(q)

    # De-duplicate words while maintaining order
    seen_words = set()
    final_tokens = []
    combined_raw = " ".join(resolved_parts)
    for tok in re.findall(r"[A-Za-z0-9#\+\-\%\.]+", combined_raw):
        tok_low = tok.lower()
        if tok_low not in seen_words:
            seen_words.add(tok_low)
            final_tokens.append(tok)

    resolved_query = " ".join(final_tokens) if final_tokens else q

    return {
        "resolved_query": resolved_query,
        "matched_option": matched,
        "active_topic": active_topic,
        "is_continuation": is_continuation,
    }

