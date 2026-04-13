import json
from typing import Dict, List, Optional
from core.db import get_connection


def save_session(session_data: Dict) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()

        final_report = session_data.get("final_report", {})
        cursor.execute("""
        INSERT INTO interview_sessions (
            session_id,
            candidate_name,
            role,
            mode,
            difficulty,
            average_score,
            overall_summary,
            top_strengths,
            top_improvement_areas,
            recommended_next_steps
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_data["session_id"],
            session_data.get("candidate_name"),
            session_data.get("role"),
            session_data.get("mode"),
            session_data.get("difficulty"),
            final_report.get("average_score", 0),
            final_report.get("overall_summary", ""),
            json.dumps(final_report.get("top_strengths", [])),
            json.dumps(final_report.get("top_improvement_areas", [])),
            json.dumps(final_report.get("recommended_next_steps", []))
        ))

        answers = session_data.get("answers", [])
        evaluations = session_data.get("evaluations", [])

        for answer_item, eval_item in zip(answers, evaluations):
            dim = eval_item.get("dimension_scores", {})
            cursor.execute("""
            INSERT INTO interview_answers (
                session_id,
                question_text,
                question_category,
                answer_text,
                overall_score,
                relevance,
                clarity,
                depth,
                communication,
                role_alignment,
                feedback,
                strengths,
                improvements
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_data["session_id"],
                answer_item["question"]["question"],
                answer_item["question"].get("category", ""),
                answer_item["answer"],
                eval_item.get("overall_score", 0),
                dim.get("relevance", 0),
                dim.get("clarity", 0),
                dim.get("depth", 0),
                dim.get("communication", 0),
                dim.get("role_alignment", 0),
                eval_item.get("feedback", ""),
                json.dumps(eval_item.get("strengths", [])),
                json.dumps(eval_item.get("improvements", []))
            ))


def get_previous_session(candidate_name: str, role: str, current_session_id: Optional[str] = None):
    with get_connection() as conn:
        cursor = conn.cursor()

        if current_session_id:
            cursor.execute("""
            SELECT *
            FROM interview_sessions
            WHERE candidate_name = ? AND role = ? AND session_id != ?
            ORDER BY created_at DESC
            LIMIT 1
            """, (candidate_name, role, current_session_id))
        else:
            cursor.execute("""
            SELECT *
            FROM interview_sessions
            WHERE candidate_name = ? AND role = ?
            ORDER BY created_at DESC
            LIMIT 1
            """, (candidate_name, role))

        row = cursor.fetchone()
        return dict(row) if row else None


def get_role_history(candidate_name: str, role: str) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT session_id, candidate_name, role, mode, difficulty, average_score, created_at
        FROM interview_sessions
        WHERE candidate_name = ? AND role = ?
        ORDER BY created_at ASC
        """, (candidate_name, role))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_candidate_role_analytics(candidate_name: str, role: str) -> Dict:
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT
            COUNT(*) AS total_interviews,
            ROUND(AVG(average_score), 2) AS avg_score,
            ROUND(MAX(average_score), 2) AS best_score,
            ROUND(MIN(average_score), 2) AS lowest_score
        FROM interview_sessions
        WHERE candidate_name = ? AND role = ?
        """, (candidate_name, role))

        summary = cursor.fetchone()

        cursor.execute("""
        SELECT
            ROUND(AVG(ia.relevance), 2) AS avg_relevance,
            ROUND(AVG(ia.clarity), 2) AS avg_clarity,
            ROUND(AVG(ia.depth), 2) AS avg_depth,
            ROUND(AVG(ia.communication), 2) AS avg_communication,
            ROUND(AVG(ia.role_alignment), 2) AS avg_role_alignment
        FROM interview_answers ia
        JOIN interview_sessions s ON ia.session_id = s.session_id
        WHERE s.candidate_name = ? AND s.role = ?
        """, (candidate_name, role))

        dimensions = cursor.fetchone()

        return {
            "summary": dict(summary) if summary else {},
            "dimensions": dict(dimensions) if dimensions else {}
        }
