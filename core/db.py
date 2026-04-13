import os
import sqlite3
from contextlib import contextmanager

DB_PATH = "data/intervueiq.db"


@contextmanager
def get_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            session_id TEXT PRIMARY KEY,
            candidate_name TEXT,
            role TEXT,
            mode TEXT,
            difficulty TEXT,
            average_score REAL,
            overall_summary TEXT,
            top_strengths TEXT,
            top_improvement_areas TEXT,
            recommended_next_steps TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            question_text TEXT,
            question_category TEXT,
            answer_text TEXT,
            overall_score REAL,
            relevance REAL,
            clarity REAL,
            depth REAL,
            communication REAL,
            role_alignment REAL,
            feedback TEXT,
            strengths TEXT,
            improvements TEXT,
            FOREIGN KEY(session_id) REFERENCES interview_sessions(session_id)
        )
        """)
