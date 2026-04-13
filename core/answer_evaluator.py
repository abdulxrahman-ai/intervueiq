from core.ai_client import AIClient
from core.prompts import ANSWER_EVALUATION_SYSTEM_PROMPT


def evaluate_answer(profile: dict, selected_role: str, question: dict, answer: str) -> dict:
    client = AIClient()

    if not answer or not answer.strip():
        return {
            "overall_score": 0,
            "dimension_scores": {
                "relevance": 0,
                "clarity": 0,
                "depth": 0,
                "communication": 0,
                "role_alignment": 0
            },
            "strengths": [],
            "improvements": ["No answer was provided."],
            "feedback": "Please provide an answer to receive evaluation."
        }

    if not client.is_available():
        return fallback_evaluation(answer)

    user_prompt = f"""
Candidate Profile:
{profile}

Target Role: {selected_role}

Question:
{question}

Candidate Answer:
{answer}

Evaluate this answer.
"""

    return client.generate_json(
        system_prompt=ANSWER_EVALUATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3
    )


def fallback_evaluation(answer: str) -> dict:
    word_count = len(answer.split())
    base_score = min(85, max(45, word_count))

    return {
        "overall_score": base_score,
        "dimension_scores": {
            "relevance": base_score,
            "clarity": max(base_score - 5, 0),
            "depth": max(base_score - 8, 0),
            "communication": base_score,
            "role_alignment": max(base_score - 3, 0)
        },
        "strengths": ["Answer was provided clearly."],
        "improvements": ["Add more specifics, measurable impact, and technical depth."],
        "feedback": "Decent initial answer. Improve it by adding structure, examples, and stronger technical detail."
    }
