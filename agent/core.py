"""Agent loop: auto-RAG grounding + optional tool calling with fallbacks.

LATENCY MODE (default): exactly ONE LLM call per question. Auto-RAG context is
injected so answers stay grounded, but tools are not offered - fastest path,
~1 round-trip. Set AGENT_MODE=agent to re-enable the multi-step tool loop
(AGENT_MAX_STEPS tool rounds) for models where tool-calling is reliable.
"""
import json
import os
import re

from . import llm, tools
from .clarify import check as clarify_check
from .counts import check as counts_check
from .prompts import FALLBACK_PROMPT, FAST_SYSTEM_PROMPT, SYSTEM_PROMPT
from .retriever import get_retriever

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
    "hello", "hi", "hey", "hii", "hiii", "helloo", "hey there", "good morning",
    "good afternoon", "good evening", "who are you", "what is your name",
    "what can you do", "help", "start", "namaste", "namaskaram", "sup",
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
    words = q.split()
    if len(words) <= 5 and history:
        for m in reversed(history):
            if isinstance(m, dict) and m.get("role") == "user":
                prev = (m.get("content") or "").strip()
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
    return (
        f"Auto-retrieved handbook context for the student's question "
        f"(pages {', '.join(cites)}):\n\n{text}\n\n"
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


PROFILE_KEYS = ("programme", "branch", "year", "semester", "batch")


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
    return "\n\nSTUDENT PROFILE: " + "; ".join(parts)


def run_agent(question, history=None, profile=None):
    """Returns {"answer", "citations", "tool_calls", "mode"}.

    A deterministic clarify pre-pass (zero LLM cost) fires first for ambiguous
    questions (Boys/Girls hostel, programme/branch) so the model never guesses
    and serves the wrong side's info. A deterministic count pre-pass fires next
    for "how many clubs" style questions so exact numbers never depend on the
    model's arithmetic.
    """
    question = _normalize_question(question)
    ckey = _cache_key(question)

    if ckey in _GREETINGS:
        return {
            "answer": (
                "Hello! 👋 I'm **SRU Assist**, your official student handbook assistant.\n\n"
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

    if not history and result.get("mode") in ("fast", "agent") and "experiencing high network demand" not in result.get("answer", ""):
        _CACHE[ckey] = result

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

    ctx = _auto_context(question, history=history, profile=profile)
    user_msg = question if not ctx else f"{question}\n\n[system note] {ctx}"
    messages.append({"role": "user", "content": user_msg})

    try:
        reply = llm.chat(messages, tools=None, max_tokens=_max_tokens())
    except Exception:
        answer = _finalize_answer("", messages, question)
        citations |= _cites_from(ctx or "")
        return {
            "answer": answer,
            "citations": sorted(citations),
            "tool_calls": [],
            "mode": "fast-fallback",
        }

    answer = _finalize_answer(reply.content, messages, question)
    citations |= _cites_from(ctx or "")

    return {
        "answer": answer,
        "citations": sorted(citations),
        "tool_calls": [],
        "mode": "fast",
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

    ctx = _auto_context(question, history=history, profile=profile)
    user_msg = question if not ctx else f"{question}\n\n[system note] {ctx}"
    messages.append({"role": "user", "content": user_msg})

    specs = tools.tool_specs(enable_web=bool(_web_enabled()))

    try:
        reply = llm.chat(messages, tools=specs, max_tokens=_max_tokens())
    except Exception:
        # Model/provider rejected tools -> plain grounded answer path.
        answer = _grounded_answer(messages, question)
        return {
            "answer": answer,
            "citations": sorted(citations),
            "tool_calls": used_tools,
            "mode": "rag-fallback",
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

        try:
            reply = llm.chat(messages, tools=specs, max_tokens=_max_tokens())
        except Exception:
            answer = _grounded_answer(messages, question)
            return {
                "answer": answer,
                "citations": sorted(citations),
                "tool_calls": used_tools,
                "mode": "rag-fallback-midloop",
            }

    answer = _finalize_answer(reply.content, messages, question)

    # Merge pages the model saw via auto-context into citations.
    citations |= _cites_from(ctx or "")

    return {
        "answer": answer,
        "citations": sorted(citations),
        "tool_calls": used_tools,
        "mode": "agent",
    }


def _max_tokens():
    try:
        return int(os.environ.get("MAX_TOKENS", "2048"))
    except ValueError:
        return 2048


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
