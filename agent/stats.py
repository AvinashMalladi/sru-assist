"""Popularity tracking for student questions (drives widget suggestions).

In-memory counters persisted to data/query_stats.json so restarts keep history.
"""
import json
import os
import re
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS_FILE = os.path.join(ROOT, "data", "query_stats.json")

_lock = threading.Lock()

DEFAULT_SUGGESTIONS = [
    "How is CGPA calculated?",
    "What are the minimum pass marks?",
    "Attendance requirement for exams?",
    "Explain the letter grade scale",
]


def _normalize(q):
    q = re.sub(r"[^a-z0-9 ]+", " ", q.lower()).strip()
    return re.sub(r"\s+", " ", q)[:80]


def _load():
    try:
        with open(STATS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001 - missing/corrupt file -> fresh start
        return {}


def _save(stats):
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=1)


def track_query(question):
    key = _normalize(question)
    if not key:
        return
    with _lock:
        stats = _load()
        entry = stats.get(key, {"count": 0, "last": 0})
        import time

        entry["count"] += 1
        entry["last"] = time.time()
        entry["display"] = question.strip()[:80]
        stats[key] = entry
        _save(stats)


def top_queries(n=5):
    with _lock:
        stats = _load()
    ranked = sorted(
        stats.items(),
        key=lambda kv: (kv[1]["count"], kv[1]["last"]),
        reverse=True,
    )
    seen, out = set(), []
    for _, v in ranked:
        disp = v.get("display") or kv[0]
        if disp.lower() not in seen:
            seen.add(disp.lower())
            out.append(disp)
        if len(out) >= n:
            break
    return out


def get_suggestions(n=6):
    """Popular tracked queries first, padded with curated defaults."""
    tracked = top_queries(n)
    merged = list(tracked)
    for d in DEFAULT_SUGGESTIONS:
        if len(merged) >= n:
            break
        if d.lower() not in [t.lower() for t in merged]:
            merged.append(d)
    return merged[:n]
