from typing import Dict, List


COMMON_JD_SKILLS = [
    "python", "sql", "tensorflow", "pytorch", "machine learning", "deep learning",
    "nlp", "fastapi", "flask", "docker", "kubernetes", "aws", "azure", "gcp",
    "tableau", "power bi", "excel", "statistics", "scikit-learn", "react",
    "javascript", "java", "postgresql", "redis", "microservices", "api",
    "stakeholder management", "product strategy", "roadmap", "data analysis"
]


def extract_jd_skills(job_description: str) -> List[str]:
    text = (job_description or "").lower()
    return sorted(list({skill for skill in COMMON_JD_SKILLS if skill in text}))


def analyze_resume_vs_jd(profile: Dict, job_description: str) -> Dict:
    resume_skills = set([skill.lower() for skill in profile.get("skills", [])])
    jd_skills = set(extract_jd_skills(job_description))

    matched = sorted(list(resume_skills.intersection(jd_skills)))
    missing = sorted(list(jd_skills - resume_skills))

    match_percent = 0
    if jd_skills:
        match_percent = round((len(matched) / len(jd_skills)) * 100, 2)

    if match_percent >= 80:
        verdict = "Strong alignment"
    elif match_percent >= 55:
        verdict = "Moderate alignment"
    else:
        verdict = "Low alignment"

    return {
        "resume_skills": sorted(list(resume_skills)),
        "jd_skills": sorted(list(jd_skills)),
        "matched_skills": matched,
        "missing_skills": missing,
        "match_percent": match_percent,
        "verdict": verdict
    }


def format_jd_analysis_text(jd_analysis: Dict) -> str:
    matched = jd_analysis.get("matched_skills", [])
    missing = jd_analysis.get("missing_skills", [])

    matched_text = "\n- ".join(matched) if matched else "None"
    missing_text = "\n- ".join(missing) if missing else "None"

    return (
        f"Match Percentage: {jd_analysis.get('match_percent', 0)}%\n"
        f"Verdict: {jd_analysis.get('verdict', 'Unknown')}\n\n"
        f"Matched Skills:\n- {matched_text}\n\n"
        f"Missing Skills:\n- {missing_text}"
    )
