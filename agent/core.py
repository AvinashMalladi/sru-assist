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
from .prompts import FALLBACK_PROMPT, FAST_SYSTEM_PROMPT, SYSTEM_PROMPT
from .retriever import get_retriever

MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "4"))
MAX_HISTORY = 10
FAST_HISTORY = 6
AUTO_CONTEXT_TOP_K = int(os.environ.get("AUTO_CONTEXT_TOP_K", "4"))

CITE_RE = re.compile(r"\[([^\]]+?) · page (\d+)\]")

# Tool arguments that must never leak into a student-facing answer.
_TOOL_KEYS = ("query", "expression", "tool", "name", "arguments", "top_k", "topk")


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
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def _cites_from(text):
    """Extract '<label> p.N' citation strings from retrieved text blocks."""
    return {f"{label.strip()} p.{page}" for label, page in CITE_RE.findall(text or "")}


def _auto_context(question):
    """Always retrieve for the newest question; guarantees grounded answers
    even when the model chooses not to call tools. Uses a SMALLER top_k in
    fast mode so prompts stay short (faster time-to-first-token)."""
    retriever = get_retriever()
    text, cites = retriever.format_hits(question, top_k=AUTO_CONTEXT_TOP_K)
    if not cites:
        return None
    return (
        f"Auto-retrieved handbook context for the student's latest question "
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


PROFILE_KEYS = ("programme", "branch", "year", "semester")


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
    and serves the wrong side's info.
    """
    question = _normalize_question(question)
    clarify = clarify_check(question, history, profile)
    if clarify:
        return clarify
    if _fast_mode():
        return _fast_answer(question, history, profile)
    return _agentic_answer(question, history, profile)


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

    ctx = _auto_context(question)
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

    ctx = _auto_context(question)
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
        return int(os.environ.get("MAX_TOKENS", "700"))
    except ValueError:
        return 700


def _grounded_answer(messages, question):
    """No-tool safety net: last 6 retrieved chunks + direct instruction."""
    text, cites = get_retriever().format_hits(question, top_k=6)
    trimmed = [m for m in messages if m["role"] in ("user", "assistant")]
    msgs = [
        {"role": "system", "content": FALLBACK_PROMPT},
        *trimmed[-6:],
        {"role": "user", "content": f"HANDBOOK CONTEXT:\n{text}\n\nQUESTION: {question}"},
    ]
    reply = llm.chat(msgs, tools=None)
    clean = _cleanup_answer(reply.content or "")
    if _looks_like_tool_call(clean):
        return "I couldn't retrieve a clear answer from the handbook for that question. Please contact the Student Help Desk."
    return clean or "I couldn't find that in the handbook. Please contact the Student Help Desk."


def _web_enabled():
    import os

    return os.environ.get("ENABLE_WEB_SEARCH", "true").lower() != "false"
