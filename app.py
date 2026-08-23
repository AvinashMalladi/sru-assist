"""SRU Assist - Flask API for the agentic student handbook chatbot.

Run:  python app.py   (serves API + demo portal on http://localhost:5000)
"""
import os

from flask import Flask, jsonify, request, send_from_directory

from agent.config import load_env
from agent.core import run_agent

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


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not question:
        return jsonify({"error": "message is required"}), 400
    if len(question) > 1000:
        return jsonify({"error": "message too long (max 1000 chars)"}), 400

    try:
        result = run_agent(question, history)
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
                    "detail": str(exc),
                }
            ),
            200,
        )

    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", "5000"))
    print(f"* SRU Assist running on http://localhost:{port} (demo portal at /)")
    app.run(host="0.0.0.0", port=port, debug=False)
