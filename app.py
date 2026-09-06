"""SRU Assist - Flask API for the agentic student handbook chatbot.

Run:  python app.py   (serves API + demo portal on http://localhost:5000)
"""
import os
import time

from flask import Flask, jsonify, request, send_from_directory

from agent.config import load_env
from agent.core import run_agent
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


@app.get("/")
def demo_portal():
    return send_from_directory(os.path.join(ROOT, "demo"), "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "model": os.environ.get("MODEL_NAME", "default")})


@app.get("/api/suggestions")
def suggestions():
    n = int(request.args.get("limit", "3") or "3")
    return jsonify({"suggestions": get_suggestions(n)})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    history = data.get("history") or []
    profile = data.get("profile") or {}

    if not question:
        return jsonify({"error": "message is required"}), 400
    if len(question) > 1000:
        return jsonify({"error": "message too long (max 1000 chars)"}), 400

    track_query(question)

    t0 = time.time()
    try:
        result = run_agent(question, history, profile=profile)
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
