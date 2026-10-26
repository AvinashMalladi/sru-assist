"""Recommendation scoring for student questions (drives widget suggestion chips).

Suggestion mining is a lightweight multi-armed-bandit:
  * Every question a student types is counted and time-stamped.
  * Queries are folded onto a small set of KNOWN TOPICS by keyword overlap.
  * Each topic keeps a decaying score:  score = Σ 2^(-age_days / half_life)
    Recent, repeated asks push a topic up; ancient history fades out.
  * Returned as clean template phrases ("Promotion rules", "Attendance criteria")
    capped at REQUESTED caps (widget limit = 3).

This is a zero-dependency, deterministic stand-in for a learned recommender; the
interface (get_suggestions) is unchanged so a model-based ranker can slot in later.
"""
import json
import os
import re
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS_FILE = os.path.join(ROOT, "data", "query_stats.json")

_lock = threading.Lock()

HALF_LIFE_DAYS = 7.0          # a topic's score halves every 7 days
TOPIC_CAP = 40                # what /api/suggestions returns by default
DEFAULT_LIMIT = 3             # what the widget asks for / renders

# topic label -> keywords that fold a typed question onto it.
# Keep labels short and familiar, matching the main handbook sections.
TOPICS = {
    "Promotion rules": ("promotion", "next year", "forward", "year to year", "flowchart"),
    "Attendance criteria": ("attendance", "condonation", "75%", "75 percent"),
    "Pass marks": ("pass", "fail", "minimum mark", "grace"),
    "CGPA / grading": ("cgpa", "sgpa", "gpa", "grade", "grading", "credit"),
    "Exams & re-eval": ("exam", "re-evaluation", "revaluation", "malpractice", "unfair"),
    "Hostel & campus": ("hostel", "dress code", "library", "ragging", "id card"),
    "Fees & scholarship": ("fee", "scholarship", "finance", "refund"),
}


def _topics_for(text):
    """Which topic labels does this question touch? (empty = uncategorized)"""
    t = text.lower()
    hits = []
    for label, keywords in TOPICS.items():
        if any(k in t for k in keywords):
            hits.append(label)
    return hits


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
    """Count + timestamp a typed question, and bump any topic it belongs to.

    Stores both raw query counts and topic-level counters so the suggestion
    layer can rank by topic while still showing FAQ-ish defaults when a topic
    has no history yet.
    """
    key = _normalize(question)
    if not key:
        return
    now = time.time()
    with _lock:
        stats = _load()
        # raw query counts (kept for completeness)
        entry = stats.get(key, {"count": 0, "last": 0})
        entry["count"] += 1
        entry["last"] = now
        entry["display"] = question.strip()[:80]
        stats[key] = entry
        # topic counters
        topics = stats.setdefault("_topics", {})
        for label in _topics_for(question):
            te = topics.get(label, {"count": 0, "last": 0})
            te["count"] += 1
            te["last"] = now
            topics[label] = te
        _save(stats)


def _decay(entry, now):
    """Score a topic or query favoring recency + frequency."""
    count = entry.get("count", 0)
    last = entry.get("last", 0)
    age_days = max(0.0, (now - last) / 86400.0) if last else 1e9
    return count * (2.0 ** (-age_days / HALF_LIFE_DAYS))


def top_topics(now=None):
    """Decayed topic scores, newest-first."""

    with _lock:
        stats = _load()
    topics = stats.get("_topics") if isinstance(stats, dict) else {}
    if not topics:
        return []
    now = now if now is not None else time.time()
    ranked = sorted(
        topics.items(),
        key=lambda kv: (_decay(kv[1], now), kv[1].get("last", 0)),
        reverse=True,
    )
    return [label for label, _ in ranked]


def get_suggestions(limit=DEFAULT_LIMIT, profile=None):
    """Return up to `limit` clean topic suggestion phrases.

    1. Personalized by student batch/regulation/branch if profile is provided.
    2. Decayed, popular topics next.
    3. Padded with curated defaults so the chip row is never empty.
    """
    if profile and isinstance(profile, dict) and any(profile.values()):
        return get_personalized_suggestions(profile, limit=limit)

    ranked = top_topics()
    merged = []
    for label in ranked:
        if label in TOPICS and label not in merged:
            merged.append(label)
        if len(merged) >= limit:
            break
    for d in DEFAULT_SUGGESTIONS:
        if len(merged) >= limit:
            break
        if d not in merged:
            merged.append(d)
    return merged[:limit]


def get_personalized_suggestions(profile, limit=DEFAULT_LIMIT):
    """Generate high-relevance suggestion chips tailored to a specific student."""
    reg = str(profile.get("regulation", "") or profile.get("batch", "")).lower()
    prog = str(profile.get("program", "") or profile.get("stream", "") or profile.get("branch", "")).upper()

    res = []
    if "r23" in reg or "2023" in reg:
        res.append("R23 Promotion rules")
        res.append("1st year 0-backlog rule")
    elif "2026" in reg:
        res.append("2026-27 Promotion credit %")
        res.append("UG pass marks (45%)")
    else:
        res.append("Promotion rules")

    if "CSE" in prog or "CS" in prog:
        res.append("CS & AI leadership contact")
    elif "ECE" in prog:
        res.append("ECE department contact")
    elif "MECH" in prog:
        res.append("Mechanical department contact")
    elif "CIVIL" in prog:
        res.append("Civil department contact")

    res.append("Attendance condonation (65-75%)")
    res.append("CGPA / grading")
    res.append("Exams & revaluation")

    seen = set()
    out = []
    for s in res:
        if s not in seen:
            seen.add(s)
            out.append(s)
        if len(out) >= limit:
            break
    return out


# Curated fallback chips (used when a topic has no history yet).
DEFAULT_SUGGESTIONS = [
    "Promotion rules",
    "Attendance criteria",
    "CGPA / grading",
]
