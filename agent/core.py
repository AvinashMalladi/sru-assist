"""Agentic loop: auto-RAG grounding + optional tool calling with fallbacks."""
import json

from . import llm, tools
from .prompts import FALLBACK_PROMPT, SYSTEM_PROMPT
from .retriever import get_retriever

MAX_STEPS = 4
MAX_HISTORY = 10


def _auto_context(question):
    """Always retrieve for the newest question; guarantees grounded answers
    even when the model chooses not to call tools."""
    retriever = get_retriever()
    text, cites = retriever.format_hits(question, top_k=6)
    if not cites:
        return None
    return (
        f"Auto-retrieved handbook context for the student's latest question "
        f"(pages {', '.join(cites)}):\n\n{text}\n\n"
        "Use this context first; you may still call search_handbook for more."
    )


def _trim_history(history):
    clean = []
    for m in history[-MAX_HISTORY:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            clean.append({"role": role, "content": content})
    return clean


def run_agent(question, history=None):
    """Returns {"answer", "citations", "tool_calls", "mode"}."""
    history = _trim_history(history or [])
    citations = set()
    used_tools = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)

    ctx = _auto_context(question)
    user_msg = question if not ctx else f"{question}\n\n[system note] {ctx}"
    messages.append({"role": "user", "content": user_msg})

    specs = tools.tool_specs(enable_web=bool(_web_enabled()))

    try:
        reply = llm.chat(messages, tools=specs)
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
                for page in _pages_in(result):
                    citations.add(page)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result[:6000],
                }
            )

        try:
            reply = llm.chat(messages, tools=specs)
        except Exception:
            answer = _grounded_answer(messages, question)
            return {
                "answer": answer,
                "citations": sorted(citations),
                "tool_calls": used_tools,
                "mode": "rag-fallback-midloop",
            }

    answer = (reply.content or "").strip()
    if not answer:
        answer = _grounded_answer(messages, question)

    # Merge pages the model saw via auto-context into citations.
    for page in _pages_in(ctx or ""):
        citations.add(page)

    return {
        "answer": answer,
        "citations": sorted(citations),
        "tool_calls": used_tools,
        "mode": "agent",
    }


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
    return (reply.content or "").strip()


def _pages_in(text):
    import re

    return {int(p) for p in re.findall(r"p\.(\d+)|page (\d+)", text) for p in p if p}


def _web_enabled():
    import os

    return os.environ.get("ENABLE_WEB_SEARCH", "true").lower() != "false"
