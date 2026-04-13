from core.ai_client import AIClient
from core.prompts import QUESTION_GENERATION_SYSTEM_PROMPT


def generate_questions(
    profile: dict,
    selected_role: str,
    mode: str,
    difficulty: str,
    num_questions: int = 5,
    job_description: str = "",
    jd_analysis: dict | None = None
) -> list:
    client = AIClient()

    if not client.is_available():
        return fallback_questions(profile, selected_role, mode, difficulty, num_questions, jd_analysis)

    user_prompt = f"""
Candidate Profile:
{profile}

Target Role: {selected_role}
Interview Mode: {mode}
Difficulty: {difficulty}
Number of Questions: {num_questions}

Job Description:
{job_description if job_description else "Not provided"}

JD Analysis:
{jd_analysis if jd_analysis else "Not provided"}

Generate interview questions tailored to this candidate.
"""

    data = client.generate_json(
        system_prompt=QUESTION_GENERATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.9
    )

    questions = data.get("questions", [])
    return questions[:num_questions]


def fallback_questions(profile: dict, selected_role: str, mode: str, difficulty: str, num_questions: int = 5, jd_analysis: dict | None = None) -> list:
    skills = profile.get("skills", [])
    projects = profile.get("projects", [])
    missing_skills = (jd_analysis or {}).get("missing_skills", [])
    matched_skills = (jd_analysis or {}).get("matched_skills", [])

    questions = [
        {
            "question_id": 1,
            "category": "Resume-Based",
            "question": f"Walk me through your background and why you are targeting the {selected_role} role.",
            "focus_area": "background"
        },
        {
            "question_id": 2,
            "category": "Project-Based",
            "question": f"Tell me about one project from your resume that best demonstrates your fit for a {selected_role} role.",
            "focus_area": "projects"
        }
    ]

    if mode == "Job-Description Based" and matched_skills:
        questions.append(
            {
                "question_id": 3,
                "category": "JD Match",
                "question": f"You appear to match {matched_skills[0]}. How have you used it in practice?",
                "focus_area": matched_skills[0]
            }
        )

    if mode == "Job-Description Based" and missing_skills:
        questions.append(
            {
                "question_id": 4,
                "category": "JD Gap",
                "question": f"This role asks for {missing_skills[0]}. How would you approach learning or handling that requirement?",
                "focus_area": missing_skills[0]
            }
        )

    if skills:
        questions.append(
            {
                "question_id": 5,
                "category": "Technical",
                "question": f"You mention {skills[0]} on your resume. Explain how you used it in a real project.",
                "focus_area": skills[0]
            }
        )

    if projects:
        questions.append(
            {
                "question_id": 6,
                "category": "Deep Dive",
                "question": "What was the most difficult challenge in that project, and how did you solve it?",
                "focus_area": "problem solving"
            }
        )

    questions.append(
        {
            "question_id": 7,
            "category": "Behavioral",
            "question": "Tell me about a time you handled a challenge, setback, or unexpected issue.",
            "focus_area": "behavioral"
        }
    )

    return questions[:num_questions]
