from typing import Dict


ROLE_KEYWORDS = {
    "AI/ML Engineer": ["machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "scikit-learn"],
    "Data Scientist": ["statistics", "machine learning", "python", "pandas", "numpy", "model"],
    "Data Analyst": ["sql", "excel", "tableau", "power bi", "dashboard", "reporting"],
    "Software Engineer": ["python", "java", "javascript", "api", "backend", "frontend"],
    "Backend Engineer": ["fastapi", "flask", "api", "postgresql", "redis", "microservices"],
    "Frontend Engineer": ["javascript", "react", "html", "css", "frontend"],
    "Full Stack Developer": ["react", "node.js", "api", "frontend", "backend"],
    "Business Analyst": ["business analysis", "excel", "sql", "reporting", "stakeholder"],
    "Product Manager": ["roadmap", "product", "stakeholder", "metrics", "prioritization"],
    "DevOps Engineer": ["docker", "kubernetes", "aws", "azure", "ci/cd", "linux"],
    "Cloud Engineer": ["aws", "azure", "gcp", "cloud", "infrastructure"],
    "QA Engineer": ["testing", "qa", "automation", "selenium"],
    "Cybersecurity Analyst": ["security", "cybersecurity", "risk", "threat", "vulnerability"]
}


def infer_role(profile: Dict) -> str:
    skills = " ".join(profile.get("skills", [])).lower()
    preview = profile.get("resume_text_preview", "").lower()
    combined_text = f"{skills} {preview}"

    best_role = "Other"
    best_score = 0

    for role, keywords in ROLE_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in combined_text)
        if score > best_score:
            best_score = score
            best_role = role

    return best_role
