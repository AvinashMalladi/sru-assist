"""SQLite database layer for persisting student conversations, htno profiles, and sessions.

Zero external dependencies (uses standard library sqlite3).
Enables automatic retrieval of previous chat history and personalized suggestions
whenever a student provides their Hall Ticket / Roll Number (htno).
"""
import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DB_PATH = os.environ.get("DB_PATH", os.path.join(DATA_DIR, "conversations.db"))

_local = threading.local()


def _get_connection() -> sqlite3.Connection:
    """Thread-safe SQLite connection with WAL mode enabled for concurrent reads/writes."""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable WAL (Write-Ahead Logging) for high concurrency
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 10000;")
        _local.conn = conn
    return _local.conn


def init_db() -> None:
    """Initialize database tables with indexes."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                htno TEXT PRIMARY KEY,
                degree TEXT,
                program TEXT,
                school TEXT,
                batch TEXT,
                regulation TEXT,
                handbook_doc TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                htno TEXT,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                message TEXT NOT NULL,
                citations_json TEXT DEFAULT '[]',
                profile_json TEXT DEFAULT '{}',
                mode TEXT DEFAULT 'normal',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_htno ON conversations(htno);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_created ON conversations(created_at);")
    logger.info("Initialized conversation database at %s", DB_PATH)


def save_student(htno: str, profile: Dict[str, Any]) -> None:
    """Insert or update a student's profile."""
    if not htno:
        return
    htno = htno.strip().upper()
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute("""
            INSERT INTO students (htno, degree, program, school, batch, regulation, handbook_doc, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(htno) DO UPDATE SET
                degree = coalesce(excluded.degree, students.degree),
                program = coalesce(excluded.program, students.program),
                school = coalesce(excluded.school, students.school),
                batch = coalesce(excluded.batch, students.batch),
                regulation = coalesce(excluded.regulation, students.regulation),
                handbook_doc = coalesce(excluded.handbook_doc, students.handbook_doc),
                last_active = excluded.last_active;
        """, (
            htno,
            profile.get("degree"),
            profile.get("program") or profile.get("stream") or profile.get("branch"),
            profile.get("school"),
            profile.get("batch"),
            profile.get("regulation"),
            profile.get("handbook_doc"),
            now
        ))


def get_student(htno: str) -> Optional[Dict[str, Any]]:
    """Retrieve student profile by hall ticket number."""
    if not htno:
        return None
    htno = htno.strip().upper()
    conn = _get_connection()
    row = conn.execute("SELECT * FROM students WHERE htno = ?", (htno,)).fetchone()
    if row:
        return {
            "roll_number": row["htno"],
            "htno": row["htno"],
            "degree": row["degree"],
            "program": row["program"],
            "stream": row["program"],
            "school": row["school"],
            "batch": row["batch"],
            "regulation": row["regulation"],
            "handbook_doc": row["handbook_doc"],
            "last_active": row["last_active"],
        }
    return None


def save_message(
    session_id: str,
    role: str,
    message: str,
    htno: Optional[str] = None,
    citations: Optional[List[str]] = None,
    profile: Optional[Dict[str, Any]] = None,
    mode: str = "normal"
) -> int:
    """Save a single chat message (user or bot)."""
    if not session_id or not message:
        return 0
    clean_htno = htno.strip().upper() if htno else None
    citations_json = json.dumps(citations or [])
    profile_json = json.dumps(profile or {})
    
    conn = _get_connection()
    with conn:
        cur = conn.execute("""
            INSERT INTO conversations (session_id, htno, role, message, citations_json, profile_json, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, clean_htno, role, message, citations_json, profile_json, mode))
        msg_id = cur.lastrowid

    if clean_htno and profile:
        save_student(clean_htno, profile)

    return msg_id


def save_turn(
    session_id: str,
    user_message: str,
    bot_answer: str,
    htno: Optional[str] = None,
    citations: Optional[List[str]] = None,
    profile: Optional[Dict[str, Any]] = None,
    mode: str = "normal"
) -> None:
    """Save both user question and bot answer in a single atomic transaction."""
    save_message(session_id, "user", user_message, htno=htno, profile=profile, mode=mode)
    save_message(session_id, "assistant", bot_answer, htno=htno, citations=citations, profile=profile, mode=mode)


def link_session_to_htno(session_id: str, htno: str) -> int:
    """Retroactively links all prior anonymous messages in a session to the newly identified htno."""
    if not session_id or not htno:
        return 0
    clean_htno = htno.strip().upper()
    conn = _get_connection()
    with conn:
        cur = conn.execute("""
            UPDATE conversations
            SET htno = ?
            WHERE session_id = ? AND (htno IS NULL OR htno = '')
        """, (clean_htno, session_id))
        return cur.rowcount


def get_conversation_history(
    htno: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Retrieve previous conversation messages ordered chronologically."""
    conn = _get_connection()
    rows = []
    
    if htno:
        clean_htno = htno.strip().upper()
        # Retrieve all messages for this student across sessions, ordered by time
        rows = conn.execute("""
            SELECT id, session_id, htno, role, message, citations_json, profile_json, mode, created_at
            FROM conversations
            WHERE htno = ?
            ORDER BY id ASC
            LIMIT ?
        """, (clean_htno, limit)).fetchall()
    elif session_id:
        rows = conn.execute("""
            SELECT id, session_id, htno, role, message, citations_json, profile_json, mode, created_at
            FROM conversations
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT ?
        """, (session_id, limit)).fetchall()

    result = []
    for r in rows:
        try:
            cites = json.loads(r["citations_json"] or "[]")
        except Exception:
            cites = []
        try:
            prof = json.loads(r["profile_json"] or "{}")
        except Exception:
            prof = {}
        result.append({
            "id": r["id"],
            "session_id": r["session_id"],
            "htno": r["htno"],
            "role": r["role"],
            "content": r["message"],
            "citations": cites,
            "profile": prof,
            "mode": r["mode"],
            "created_at": r["created_at"]
        })
    return result


def clear_conversation(htno: Optional[str] = None, session_id: Optional[str] = None) -> int:
    """Delete conversation history for an htno or session_id."""
    conn = _get_connection()
    count = 0
    with conn:
        if htno:
            clean_htno = htno.strip().upper()
            cur = conn.execute("DELETE FROM conversations WHERE htno = ?", (clean_htno,))
            count = cur.rowcount
        elif session_id:
            cur = conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            count = cur.rowcount
    return count


# Auto-initialize on module load
try:
    init_db()
except Exception as e:
    logger.warning("DB initialization deferred: %s", e)
