"""Tool definitions + implementations for the agentic loop."""
import ast
import operator
import re

import requests

from .retriever import get_retriever

TOOL_SEARCH = {
    "type": "function",
    "function": {
        "name": "search_handbook",
        "description": (
            "Search the official SR University Student Handbook. Use for any "
            "question about credits, grades, CGPA, pass marks, attendance, "
            "exams, promotion, fees, hostel, dress code, or university policies."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keyword search query, e.g. 'minimum pass marks end semester'",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of sections to return (default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}

TOOL_CALC = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Evaluate an arithmetic expression, e.g. '(75/100)*10'. Use for CGPA or percentage math.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Arithmetic expression using + - * / ( ) and numbers."},
            },
            "required": ["expression"],
        },
    },
}

TOOL_WEB = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Search the public web via Tavily. ONLY use when the handbook does "
            "not contain the answer, e.g. national exam bodies, current events. "
            "Never use before trying search_handbook."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    },
}


def tool_specs(enable_web=False):
    specs = [TOOL_SEARCH, TOOL_CALC]
    if enable_web:
        specs.append(TOOL_WEB)
    return specs


# ---------- implementations ----------

def run_search_handbook(query, top_k=5):
    retriever = get_retriever()
    text, cites = retriever.format_hits(query, top_k=top_k)
    header = f"Handbook sections matched ({', '.join(cites)}):" if cites else "No handbook match."
    return f"{header}\n\n{text}"


_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported expression")


def run_calculator(expression):
    try:
        expr = re.sub(r"[^0-9+\-*/().% ]", "", str(expression))
        value = _safe_eval(ast.parse(expr, mode="eval"))
        return f"{expression} = {value:g}"
    except Exception as exc:  # noqa: BLE001 - report bad input to the model
        return f"Calculator error: {exc}"


def run_search_web(query):
    import os

    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return "Web search unavailable (TAVILY_API_KEY not configured)."
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": query, "max_results": 4},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return "No web results found."
        blocks = [
            f"- {r.get('title', '')}: {r.get('content', '')[:400]} (URL: {r.get('url', '')})"
            for r in results
        ]
        return "WEB RESULTS (not from the official handbook):\n" + "\n".join(blocks)
    except Exception as exc:  # noqa: BLE001
        return f"Web search failed: {exc}"


def execute(name, arguments):
    """Dispatch a tool call; always returns a string."""
    try:
        if name == "search_handbook":
            return run_search_handbook(
                arguments.get("query", ""), int(arguments.get("top_k", 5))
            )
        if name == "calculator":
            return run_calculator(arguments.get("expression", ""))
        if name == "search_web":
            return run_search_web(arguments.get("query", ""))
        return f"Unknown tool: {name}"
    except Exception as exc:  # noqa: BLE001
        return f"Tool '{name}' error: {exc}"
