"""SRU Assist - Flask API for the agentic student handbook chatbot.

Run:  python app.py   (serves API + demo portal on http://localhost:5000)
"""
import os
import time
import uuid

from flask import Flask, jsonify, request, send_from_directory

from agent.config import load_env
from agent.core import run_agent
from agent import db
from agent.roll_decoder import parse_roll_number
from agent.stats import get_suggestions, track_query

load_env()

app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.after_request  # allow the widget to be embedded from any portal origin
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


ROOT = os.path.dirname(os.path.abspath(__file__))

# Lightweight in-memory rate limiter to protect OpenRouter quotas from request floods
_IP_REQUESTS = {}
_RATE_LIMIT_WINDOW = 60.0  # seconds
_MAX_REQUESTS_PER_WINDOW = 25  # max 25 reqs/min per IP


def _is_rate_limited(ip):
    now = time.time()
    history = _IP_REQUESTS.setdefault(ip, [])
    # Evict requests older than the rolling window
    _IP_REQUESTS[ip] = [t for t in history if now - t < _RATE_LIMIT_WINDOW]
    if len(_IP_REQUESTS[ip]) >= _MAX_REQUESTS_PER_WINDOW:
        return True
    _IP_REQUESTS[ip].append(now)
    return False


@app.get("/")
def demo_portal():
    return send_from_directory(os.path.join(ROOT, "demo"), "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "model": os.environ.get("MODEL_NAME", "default")})


@app.get("/api/suggestions")
def suggestions():
    n = int(request.args.get("limit", "3") or "3")
    htno = request.args.get("htno", "").strip()
    profile = None
    if htno:
        profile = db.get_student(htno)
        if not profile:
            detected = parse_roll_number(htno)
            if detected:
                profile = detected
    return jsonify({"suggestions": get_suggestions(n, profile=profile)})


@app.get("/api/history")
def get_history():
    htno = request.args.get("htno", "").strip()
    session_id = request.args.get("session_id", "").strip()
    limit = int(request.args.get("limit", "50") or "50")

    if not htno and not session_id:
        return jsonify({"error": "htno or session_id parameter required"}), 400

    profile = None
    if htno:
        profile = db.get_student(htno)
        if not profile:
            detected = parse_roll_number(htno)
            if detected:
                profile = detected
                db.save_student(htno, profile)

    messages = db.get_conversation_history(htno=htno or None, session_id=session_id or None, limit=limit)
    suggestions_list = get_suggestions(4, profile=profile)

    return jsonify({
        "htno": htno,
        "session_id": session_id,
        "profile": profile,
        "messages": messages,
        "suggestions": suggestions_list,
    })


@app.delete("/api/history")
def delete_history():
    htno = request.args.get("htno", "").strip()
    session_id = request.args.get("session_id", "").strip()
    if not htno and not session_id:
        return jsonify({"error": "htno or session_id required"}), 400
    deleted_count = db.clear_conversation(htno=htno or None, session_id=session_id or None)
    return jsonify({"status": "cleared", "deleted_count": deleted_count})


@app.post("/api/chat")
def chat():
    client_ip = (
        request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")
        .split(",")[0]
        .strip()
    )
    if _is_rate_limited(client_ip):
        return (
            jsonify(
                {
                    "answer": "You are sending messages too quickly. Please pause a moment before asking another question.",
                    "citations": [],
                    "tool_calls": [],
                    "mode": "rate_limited",
                }
            ),
            429,
        )

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    history = data.get("history") or []
    profile = data.get("profile") or {}
    session_id = (data.get("session_id") or "").strip() or str(uuid.uuid4())
    htno = (data.get("htno") or profile.get("roll_number") or "").strip()

    # Detect roll number from question if not already provided
    detected_roll = parse_roll_number(question)
    if detected_roll:
        htno = detected_roll["roll_number"]
        profile.update(detected_roll)
        db.link_session_to_htno(session_id, htno)
        db.save_student(htno, profile)
    elif htno and not profile.get("regulation"):
        existing_profile = db.get_student(htno)
        if existing_profile:
            profile.update(existing_profile)

    if not question:
        return jsonify({"error": "message is required"}), 400
    if len(question) > 1000:
        return jsonify({"error": "message too long (max 1000 chars)"}), 400

    track_query(question)

    t0 = time.time()
    try:
        result = run_agent(question, history, profile=profile)
        if result.get("profile"):
            profile.update(result["profile"])
            if result["profile"].get("roll_number"):
                htno = result["profile"]["roll_number"]
                db.link_session_to_htno(session_id, htno)
                db.save_student(htno, profile)

        db.save_turn(
            session_id=session_id,
            user_message=question,
            bot_answer=result.get("answer", ""),
            htno=htno or None,
            citations=result.get("citations"),
            profile=profile,
            mode=result.get("mode", "normal")
        )
    except Exception as exc:  # noqa: BLE001 - never crash the widget
        app.logger.exception("agent failure")
        return (
            jsonify(
                {
                    "answer": "Sorry, I'm having trouble right now. Please try again "
                    "in a moment or contact the Student Help Desk.",
                    "citations": [],
                    "tool_calls": [],
                    "mode": "error",
                    "latency_ms": int((time.time() - t0) * 1000),
                    "detail": str(exc),
                }
            ),
            200,
        )
    result["latency_ms"] = int((time.time() - t0) * 1000)
    result["session_id"] = session_id
    result["htno"] = htno
    result["suggestions"] = get_suggestions(4, profile=profile)
    return jsonify(result)


@app.post("/api/sync")
def sync_documents():
    """Portal-push content ingestion - no PDFs need to ship with the backend.

    Body (JSON):
      {"label": "2026 Handbook",
       "sections": [{"page": 5, "text": "..."}, ...]}   -> content passed in
      -- or --
      {"label": "2026 Handbook", "url": "https://…/handbook.json"}   -> fetch

    Optional auth: set SYNC_TOKEN in .env; clients send
    `Authorization: Bearer <token>`. Responds 401 when token required/missing.
    """
    expected = os.environ.get("SYNC_TOKEN", "").strip()
    supplied = (
        request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        or request.headers.get("X-Sync-Token", "").strip()
    )
    if expected and supplied != expected:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    label = (data.get("label") or "").strip()
    if not label:
        return jsonify({"error": "label is required"}), 400

    from agent import retriever
    from agent.retriever import rebuild

    try:
        if data.get("url"):
            txt_path = retriever.fetch_remote(data["url"], label)
        elif data.get("sections") or data.get("pages") or data.get("chunks"):
            slug = retriever._slug(label)
            txt_path = os.path.join(retriever.DATA, f"{slug}.txt")
            retriever.sync_from_json(txt_path, label, data)
        else:
            return (
                jsonify({"error": "send a 'url', or 'sections'/'pages' with text"}),
                400,
            )
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("sync failure")
        return jsonify({"error": f"sync failed: {exc}"}), 400

    # Register the pushed/remote source so it survives restart.
    txt_name = os.path.basename(txt_path)
    retriever.add_source({"txt": txt_name, "label": label})

    r = rebuild()
    return jsonify(
        {
            "ok": True,
            "label": label,
            "chunks": len(r.chunks),
            "source": txt_name,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("FLASK_PORT", "5000")))
    print(f"* SRU Assist running on http://localhost:{port} (demo portal at /)")
    app.run(host="0.0.0.0", port=port, debug=False)
