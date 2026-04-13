from statistics import mean
from core.question_generator import generate_questions
from core.answer_evaluator import evaluate_answer
from core.ai_client import AIClient
from core.prompts import FINAL_REPORT_SYSTEM_PROMPT


def initialize_runtime(
    profile: dict,
    selected_role: str,
    mode: str,
    difficulty: str,
    num_questions: int = 5,
    job_description: str = "",
    jd_analysis: dict | None = None
) -> dict:
    questions = generate_questions(
        profile=profile,
        selected_role=selected_role,
        mode=mode,
        difficulty=difficulty,
        num_questions=num_questions,
        job_description=job_description,
        jd_analysis=jd_analysis
    )

    return {
        "profile": profile,
        "selected_role": selected_role,
        "mode": mode,
        "difficulty": difficulty,
        "job_description": job_description,
        "jd_analysis": jd_analysis or {},
        "questions": questions,
        "current_index": 0,
        "answers": [],
        "evaluations": [],
        "is_complete": False
    }


def get_current_question(runtime: dict) -> str:
    if not runtime or runtime.get("is_complete"):
        return "Interview complete."

    idx = runtime.get("current_index", 0)
    questions = runtime.get("questions", [])

    if idx >= len(questions):
        return "Interview complete."

    q = questions[idx]
    return q.get("question", "No question available.")


def submit_answer(runtime: dict, answer: str):
    if not runtime:
        return runtime, {}, "No active interview session found."

    idx = runtime.get("current_index", 0)
    questions = runtime.get("questions", [])

    if idx >= len(questions):
        runtime["is_complete"] = True
        return runtime, {}, "Interview already completed."

    current_question = questions[idx]
    evaluation = evaluate_answer(
        profile=runtime["profile"],
        selected_role=runtime["selected_role"],
        question=current_question,
        answer=answer
    )

    runtime["answers"].append(
        {
            "question": current_question,
            "answer": answer
        }
    )
    runtime["evaluations"].append(evaluation)
    runtime["current_index"] += 1

    if runtime["current_index"] >= len(questions):
        runtime["is_complete"] = True
        next_question = "Interview complete. Generate the final report below."
    else:
        next_question = runtime["questions"][runtime["current_index"]]["question"]

    return runtime, evaluation, next_question


def build_final_report(runtime: dict) -> dict:
    evaluations = runtime.get("evaluations", [])
    if not evaluations:
        return {
            "average_score": 0,
            "overall_summary": "No answers were evaluated yet.",
            "top_strengths": [],
            "top_improvement_areas": [],
            "recommended_next_steps": []
        }

    avg_score = round(mean([e.get("overall_score", 0) for e in evaluations]), 2)

    client = AIClient()
    if not client.is_available():
        return {
            "average_score": avg_score,
            "overall_summary": "The interview was completed. Add API access for richer summary generation.",
            "top_strengths": ["Completed the interview flow"],
            "top_improvement_areas": ["Add more detailed and structured answers"],
            "recommended_next_steps": [
                "Use more concrete examples",
                "Include measurable outcomes",
                "Practice concise but deep explanations"
            ]
        }

    payload = {
        "role": runtime.get("selected_role"),
        "mode": runtime.get("mode"),
        "difficulty": runtime.get("difficulty"),
        "job_description": runtime.get("job_description", ""),
        "jd_analysis": runtime.get("jd_analysis", {}),
        "questions_and_evaluations": [
            {
                "question": answer_item["question"]["question"],
                "category": answer_item["question"].get("category", ""),
                "answer": answer_item["answer"],
                "evaluation": eval_item
            }
            for answer_item, eval_item in zip(runtime["answers"], runtime["evaluations"])
        ]
    }

    summary = client.generate_json(
        system_prompt=FINAL_REPORT_SYSTEM_PROMPT,
        user_prompt=str(payload),
        temperature=0.3
    )

    return {
        "average_score": avg_score,
        **summary
    }
