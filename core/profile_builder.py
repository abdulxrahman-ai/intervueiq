import re
from typing import Dict, List


COMMON_SKILLS = [
    "python", "sql", "tensorflow", "pytorch", "scikit-learn", "machine learning",
    "deep learning", "nlp", "fastapi", "flask", "streamlit", "gradio", "excel",
    "tableau", "power bi", "aws", "azure", "gcp", "docker", "kubernetes",
    "java", "javascript", "react", "node.js", "postgresql", "mongodb", "redis",
    "git", "linux", "pandas", "numpy", "statistics", "data analysis", "business analysis"
]


def extract_email(text: str) -> str:
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = re.search(r'(\+?\d[\d\-\(\) ]{8,}\d)', text)
    return match.group(0) if match else ""


def extract_skills(text: str) -> List[str]:
    lowered = text.lower()
    found = [skill for skill in COMMON_SKILLS if skill in lowered]
    return sorted(list(set(found)))


def split_sections(text: str) -> Dict[str, str]:
    sections = {
        "skills": "",
        "experience": "",
        "projects": "",
        "education": ""
    }

    current = None
    lines = text.split("\n")

    for raw_line in lines:
        line = raw_line.strip()
        l = line.lower()

        if not line:
            continue

        if any(x in l for x in ["skills", "technical skills", "core skills", "skills & tools", "tools & technologies"]):
            current = "skills"
            continue
        elif any(x in l for x in ["work experience", "professional experience", "experience", "employment history"]):
            current = "experience"
            continue
        elif any(x in l for x in ["projects", "project", "personal projects", "academic projects"]):
            current = "projects"
            continue
        elif any(x in l for x in ["education", "academic background", "academic details"]):
            current = "education"
            continue

        if current:
            sections[current] += line + "\n"

    return sections


def extract_bullets(section_text: str) -> List[str]:
    if not section_text.strip():
        return []

    lines = [line.strip() for line in section_text.split("\n") if line.strip()]
    cleaned = []

    for line in lines:
        line = line.strip("•- \t").strip()
        if len(line) > 15:
            cleaned.append(line)

    deduped = []
    seen = set()
    for item in cleaned:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:6]


def extract_education(section_text: str) -> List[str]:
    if not section_text.strip():
        return []

    keywords = ["bachelor", "master", "phd", "university", "college", "school", "degree"]
    lines = [line.strip() for line in section_text.split("\n") if line.strip()]

    results = []
    for line in lines:
        if any(k in line.lower() for k in keywords):
            results.append(line)

    deduped = []
    seen = set()
    for item in results:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:5]


def estimate_experience_level(text: str) -> str:
    lowered = text.lower()

    if any(word in lowered for word in ["senior", "lead", "manager", "principal"]):
        return "Senior"
    if any(word in lowered for word in ["junior", "intern", "fresher", "entry"]):
        return "Entry-Level"
    return "Mid-Level"


def build_candidate_profile(text: str) -> Dict:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    candidate_name = lines[0] if lines else "Unknown Candidate"

    sections = split_sections(text)

    profile = {
        "candidate_name": candidate_name,
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "experience": extract_bullets(sections.get("experience", "")),
        "projects": extract_bullets(sections.get("projects", "")),
        "education": extract_education(sections.get("education", "")),
        "experience_level": estimate_experience_level(text),
        "resume_text_preview": text[:1200]
    }

    return profile