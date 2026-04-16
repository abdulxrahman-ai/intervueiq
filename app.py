import html
import gradio as gr
from core.db import init_db
from core.resume_parser import extract_resume_text
from core.profile_builder import build_candidate_profile
from core.role_mapper import infer_role
from core.interview_runtime import (
    initialize_runtime,
    get_current_question,
    submit_answer,
    build_final_report,
)
from core.session_store import (
    save_session,
    get_previous_session,
    get_candidate_role_analytics,
)
from core.comparison_engine import compare_with_previous, format_comparison_text
from core.analytics import format_analytics_text
from core.email_utils import send_report_email
from core.voice_utils import transcribe_audio
from core.pdf_report import build_pdf_report
from utils.helpers import generate_session_id

init_db()

DEFAULT_MODE = "Mixed"
DEFAULT_DIFFICULTY = "Medium"


def normalize_upload(uploaded_file):
    if isinstance(uploaded_file, list):
        return uploaded_file[0] if uploaded_file else None
    return uploaded_file


def store_uploaded_resume(uploaded_file):
    return normalize_upload(uploaded_file)


def safe_text(value, fallback="—"):
    if value is None:
        return fallback
    if isinstance(value, str):
        value = value.strip()
        return html.escape(value) if value else fallback
    return html.escape(str(value))


def normalize_items(items, fallback="None"):
    cleaned = []
    for item in items or []:
        if isinstance(item, dict):
            if item.get("title"):
                cleaned.append(str(item["title"]))
            elif item.get("name"):
                cleaned.append(str(item["name"]))
            else:
                cleaned.append(", ".join(f"{k}: {v}" for k, v in item.items()))
        else:
            cleaned.append(str(item).strip())
    cleaned = [c for c in cleaned if c]
    return cleaned if cleaned else [fallback]


def render_empty_card(title, subtitle):
    return f"""
    <div class="empty-card reveal-up">
        <div class="empty-title">{html.escape(title)}</div>
        <div class="empty-text">{html.escape(subtitle)}</div>
    </div>
    """


def render_analysis_dashboard(profile, inferred_role):
    if not profile:
        return render_empty_card(
            "Analysis Summary",
            "Upload your resume and click Analyze Resume to generate email, phone, skills, experience, projects, and education.",
        )

    email = safe_text(profile.get("email"))
    phone = safe_text(profile.get("phone"))
    role = safe_text(inferred_role or "Other")
    level = safe_text(profile.get("experience_level"), "Experience level not detected")

    skills = normalize_items(profile.get("skills", []), "No skills detected")
    experience = normalize_items(profile.get("experience", []), "No experience detected")
    projects = normalize_items(profile.get("projects", []), "No projects detected")
    education = normalize_items(profile.get("education", []), "No education detected")

    skills_html = "".join(
        f'<span class="skill-chip">{html.escape(skill)}</span>' for skill in skills[:20]
    )
    experience_html = "".join(f"<li>{html.escape(item)}</li>" for item in experience[:4])
    projects_html = "".join(f"<li>{html.escape(item)}</li>" for item in projects[:4])
    education_html = "".join(f"<li>{html.escape(item)}</li>" for item in education[:3])

    return f"""
    <div class="glass-card summary-card reveal-up">
        <div class="eyebrow">Resume Intelligence</div>
        <div class="summary-top">
            <div>
                <div class="card-title">Analysis Summary</div>
                <div class="card-text">Structured resume insights from the uploaded document.</div>
            </div>
            <div class="pill-wrap">
                <span class="meta-pill">Role: {role}</span>
                <span class="meta-pill">Level: {level}</span>
            </div>
        </div>

        <div class="summary-stack">
            <div class="summary-item-card clay-card">
                <div class="summary-item-label">Email</div>
                <div class="summary-item-value">{email}</div>
            </div>

            <div class="summary-item-card clay-card">
                <div class="summary-item-label">Phone</div>
                <div class="summary-item-value">{phone}</div>
            </div>

            <div class="summary-item-card clay-card">
                <div class="summary-item-label">Skills</div>
                <div class="skills-wrap compact">{skills_html}</div>
            </div>

            <div class="summary-item-card clay-card">
                <div class="summary-item-label">Experience</div>
                <ul class="stack-list">{experience_html}</ul>
            </div>

            <div class="summary-item-card clay-card">
                <div class="summary-item-label">Projects</div>
                <ul class="stack-list">{projects_html}</ul>
            </div>

            <div class="summary-item-card clay-card">
                <div class="summary-item-label">Education</div>
                <ul class="stack-list">{education_html}</ul>
            </div>
        </div>
    </div>
    """


def render_progress(progress):
    progress = progress or {}
    answered = progress.get("answered", 0)
    total = progress.get("total", 0)
    role = safe_text(progress.get("role"), "—")
    completed = progress.get("completed", False)
    percent = int((answered / total) * 100) if total else 0

    if completed:
        status_text = "Interview completed"
    elif total:
        status_text = f"Question {min(answered + 1, total)} of {total}"
    else:
        status_text = "Interview not started"

    return f"""
    <div class="glass-card progress-card reveal-up">
        <div class="progress-top">
            <div>
                <div class="eyebrow">Live Progress</div>
                <div class="card-title small">{status_text}</div>
            </div>
            <div class="pill-wrap">
                <span class="meta-pill">Role: {role}</span>
                <span class="meta-pill">Mode: {DEFAULT_MODE}</span>
                <span class="meta-pill">Difficulty: {DEFAULT_DIFFICULTY}</span>
            </div>
        </div>
        <div class="progress-track">
            <div class="progress-fill" style="width: {percent}%;"></div>
        </div>
        <div class="progress-foot">{answered}/{total} answered</div>
    </div>
    """


def render_question_card(question_text):
    if not question_text:
        return render_empty_card(
            "Interview not started",
            "Upload and analyze your resume first, then start the interview.",
        )

    return f"""
    <div class="glass-card output-card reveal-up">
        <div class="eyebrow">Current Question</div>
        <div class="card-title">Interview Prompt</div>
        <div class="question-text">{html.escape(question_text)}</div>
    </div>
    """


def render_report_overview(report, runtime):
    if not report:
        return render_empty_card(
            "No report generated yet",
            "Complete the interview first, then generate your final performance dashboard.",
        )

    average_score = report.get("average_score", 0)
    role = safe_text(runtime.get("selected_role"), "—") if runtime else "—"
    summary = report.get("overall_summary", "No summary available.")

    return f"""
    <div class="results-hero glass-card reveal-up">
        <div class="score-orb">
            <div class="score-number">{html.escape(str(average_score))}</div>
            <div class="score-label">Average Score</div>
        </div>
        <div>
            <div class="eyebrow">Command Dashboard</div>
            <div class="card-title">Performance Outcome</div>
            <div class="pill-wrap" style="margin-bottom: 12px;">
                <span class="meta-pill">Role: {role}</span>
                <span class="meta-pill">Mode: {DEFAULT_MODE}</span>
                <span class="meta-pill">Difficulty: {DEFAULT_DIFFICULTY}</span>
            </div>
            <div class="card-text preserve-lines">{html.escape(summary)}</div>
        </div>
    </div>
    """


def render_text_panel(title, eyebrow, body_text):
    if not body_text:
        return render_empty_card(title, f"{title} will appear here once available.")

    return f"""
    <div class="glass-card output-card reveal-up">
        <div class="eyebrow">{html.escape(eyebrow)}</div>
        <div class="card-title">{html.escape(title)}</div>
        <div class="card-text preserve-lines">{html.escape(body_text)}</div>
    </div>
    """


def analyze_resume(uploaded_file):
    uploaded_file = normalize_upload(uploaded_file)
    resume_text = extract_resume_text(uploaded_file, "")

    if not resume_text:
        return (
            render_analysis_dashboard({}, "Other"),
            "Other",
            {},
        )

    profile = build_candidate_profile(resume_text)
    inferred_role = infer_role(profile)

    profile_display = {
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "experience_level": profile.get("experience_level", ""),
        "skills": profile.get("skills", []),
        "experience": profile.get("experience", []),
        "education": profile.get("education", []),
        "projects": profile.get("projects", []),
    }

    return (
        render_analysis_dashboard(profile_display, inferred_role),
        inferred_role,
        profile_display,
    )


def start_interview(profile, inferred_role):
    if not profile:
        empty_progress = {
            "answered": 0,
            "total": 0,
            "role": inferred_role,
            "completed": False,
        }
        return (
            {},
            render_question_card("Please analyze a resume first."),
            [],
            render_progress(empty_progress),
        )

    runtime = initialize_runtime(
        profile=profile,
        selected_role=inferred_role or "Other",
        mode=DEFAULT_MODE,
        difficulty=DEFAULT_DIFFICULTY,
        num_questions=5,
        job_description="",
        jd_analysis={},
    )

    first_question = get_current_question(runtime)

    chat_history = [
        {"role": "assistant", "content": f"Interview started for {inferred_role} role."},
        {"role": "assistant", "content": f"Question 1: {first_question}"},
    ]

    progress = {
        "role": inferred_role,
        "answered": 0,
        "total": len(runtime.get("questions", [])),
        "completed": False,
    }

    return runtime, render_question_card(first_question), chat_history, render_progress(progress)


def handle_answer(runtime, answer, chat_history):
    if not runtime:
        current_progress = {
            "answered": 0,
            "total": 0,
            "completed": False,
        }
        return runtime, chat_history, "", render_progress(current_progress), render_question_card(
            "Please initialize the interview first."
        )

    if not answer or not answer.strip():
        progress = {
            "answered": len(runtime.get("answers", [])),
            "total": len(runtime.get("questions", [])),
            "role": runtime.get("selected_role"),
            "completed": runtime.get("is_complete", False),
        }
        return runtime, chat_history, "", render_progress(progress), render_question_card(
            "Please type an answer before submitting."
        )

    chat_history = chat_history or []
    chat_history.append({"role": "user", "content": answer})

    updated_runtime, evaluation, next_question = submit_answer(runtime, answer)

    feedback_text = (
        f"Score: {evaluation.get('overall_score', 0)}/100\n\n"
        f"Feedback: {evaluation.get('feedback', 'No feedback available.')}\n\n"
        f"Strengths: {', '.join(evaluation.get('strengths', [])) or 'None'}\n\n"
        f"Improvements: {', '.join(evaluation.get('improvements', [])) or 'None'}"
    )

    chat_history.append({"role": "assistant", "content": feedback_text})

    if not updated_runtime.get("is_complete"):
        chat_history.append({"role": "assistant", "content": f"Next Question: {next_question}"})

    progress = {
        "answered": len(updated_runtime.get("answers", [])),
        "total": len(updated_runtime.get("questions", [])),
        "role": updated_runtime.get("selected_role"),
        "completed": updated_runtime.get("is_complete", False),
    }

    next_card_text = (
        "Interview completed. Generate your final report."
        if updated_runtime.get("is_complete")
        else next_question
    )

    return (
        updated_runtime,
        chat_history,
        "",
        render_progress(progress),
        render_question_card(next_card_text),
    )


def transcribe_voice(audio_file):
    if not audio_file:
        return "Please record or upload audio first."

    file_path = audio_file if isinstance(audio_file, str) else getattr(audio_file, "name", "")
    return transcribe_audio(file_path)


def generate_report(runtime):
    if not runtime:
        return (
            {},
            render_report_overview({}, {}),
            {},
            render_text_panel("Improvement Comparison", "Progress Delta", ""),
            {},
            render_text_panel("Analytics", "Performance Intelligence", ""),
            "",
            "",
            None,
        )

    report = build_final_report(runtime)
    session_id = generate_session_id()

    session_data = {
        "session_id": session_id,
        "candidate_name": runtime["profile"].get("candidate_name", "Candidate"),
        "role": runtime.get("selected_role"),
        "mode": runtime.get("mode"),
        "difficulty": runtime.get("difficulty"),
        "answers": runtime.get("answers", []),
        "evaluations": runtime.get("evaluations", []),
        "final_report": report,
        "status": "completed",
    }

    previous_session = get_previous_session(
        candidate_name=session_data["candidate_name"],
        role=session_data["role"],
    )

    save_session(session_data)

    comparison = compare_with_previous(previous_session, report)
    analytics = get_candidate_role_analytics(
        candidate_name=session_data["candidate_name"],
        role=session_data["role"],
    )

    strengths_text = "\n- ".join(report.get("top_strengths", [])) if report.get("top_strengths") else "None"
    improve_text = (
        "\n- ".join(report.get("top_improvement_areas", []))
        if report.get("top_improvement_areas")
        else "None"
    )
    steps_text = (
        "\n- ".join(report.get("recommended_next_steps", []))
        if report.get("recommended_next_steps")
        else "None"
    )

    report_text = (
        f"Average Score: {report.get('average_score', 0)}\n\n"
        f"Summary: {report.get('overall_summary', '')}\n\n"
        f"Top Strengths:\n- {strengths_text}\n\n"
        f"Top Improvement Areas:\n- {improve_text}\n\n"
        f"Recommended Next Steps:\n- {steps_text}"
    )

    comparison_text = format_comparison_text(comparison)
    analytics_text = format_analytics_text(analytics)

    pdf_path = build_pdf_report(
        candidate_name=session_data["candidate_name"],
        role=session_data["role"],
        mode=session_data["mode"],
        difficulty=session_data["difficulty"],
        report_text=report_text,
        comparison_text=comparison_text,
        output_dir="data",
    )

    return (
        report,
        render_report_overview(report, runtime),
        comparison,
        render_text_panel("Improvement Comparison", "Progress Delta", comparison_text),
        analytics,
        render_text_panel("Analytics", "Performance Intelligence", analytics_text),
        report_text,
        comparison_text,
        pdf_path,
    )


def send_email_action(email_input, report_text, comparison_text):
    if not email_input or not email_input.strip():
        return "Please enter an email address."

    body = (
        "Your IntervueIQ Interview Report\n\n"
        f"{report_text}\n\n"
        "Comparison Summary\n"
        f"{comparison_text}\n"
    )

    return send_report_email(
        to_email=email_input.strip(),
        subject="Your AI Interview Report – IntervueIQ",
        body=body,
    )


theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="violet",
    neutral_hue="slate",
)

custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

:root {
    --bg-1: #030712;
    --bg-2: #07111f;
    --bg-3: #0b1730;
    --panel: rgba(255,255,255,0.08);
    --panel-2: rgba(255,255,255,0.05);
    --border: rgba(255,255,255,0.14);
    --text: #eef2ff;
    --muted: #bfd0ea;
    --purple: #8b5cf6;
    --indigo: #4f46e5;
    --cyan: #22d3ee;
    --shadow: 0 24px 70px rgba(0,0,0,0.45);
    --shadow-soft: 0 16px 40px rgba(0,0,0,0.28);
    --inner-light: inset 1px 1px 0 rgba(255,255,255,0.12), inset -1px -1px 0 rgba(255,255,255,0.02);
}

* {
    font-family: 'Inter', sans-serif !important;
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

html, body, .gradio-container {
    min-height: 100%;
    background:
        radial-gradient(circle at 12% 14%, rgba(139,92,246,0.24), transparent 18%),
        radial-gradient(circle at 88% 12%, rgba(79,70,229,0.22), transparent 20%),
        radial-gradient(circle at 82% 72%, rgba(34,211,238,0.14), transparent 22%),
        radial-gradient(circle at 24% 86%, rgba(99,102,241,0.10), transparent 18%),
        linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 40%, var(--bg-3) 100%) !important;
    color: var(--text) !important;
    overflow-x: hidden !important;
}

body {
    margin: 0 !important;
}

body::before {
    content: "";
    position: fixed;
    inset: 0;
    background:
        linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
    background-size: 36px 36px;
    mask-image: radial-gradient(circle at center, rgba(0,0,0,0.9), transparent 85%);
    pointer-events: none;
    z-index: 0;
}

body::after {
    content: "";
    position: fixed;
    width: 320px;
    height: 320px;
    left: var(--mx, 50vw);
    top: var(--my, 50vh);
    transform: translate(-50%, -50%);
    background: radial-gradient(circle, rgba(139,92,246,0.14), rgba(79,70,229,0.07) 38%, transparent 72%);
    filter: blur(20px);
    pointer-events: none;
    z-index: 0;
}

button, a, [role="button"] {
    cursor: pointer !important;
}

.gradio-container {
    position: relative;
    z-index: 1;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 auto !important;
    padding: 18px 18px 34px 18px !important;
}

.main-shell,
.hero-wrap,
.section-shell,
.glass-card,
.timeline-node,
.summary-item-card,
.info-card,
.mini-panel,
.empty-card {
    overflow: visible !important;
}

.main-shell {
    width: 100%;
}

.hero-wrap {
    position: relative;
    border: 1px solid var(--border);
    background:
        linear-gradient(135deg, rgba(255,255,255,0.13), rgba(255,255,255,0.05)),
        rgba(255,255,255,0.03);
    backdrop-filter: blur(26px);
    -webkit-backdrop-filter: blur(26px);
    border-radius: 34px;
    padding: 34px;
    box-shadow: var(--shadow), var(--inner-light);
    margin-bottom: 18px;
}

.hero-wrap::before {
    content: "";
    position: absolute;
    inset: 1px;
    border-radius: inherit;
    background: linear-gradient(135deg, rgba(255,255,255,0.12), transparent 28%, transparent 72%, rgba(255,255,255,0.04));
    pointer-events: none;
    opacity: 0.9;
}

.hero-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.95fr);
    gap: 24px;
    align-items: stretch;
}

.hero-badge {
    display: inline-flex;
    padding: 10px 16px;
    border-radius: 999px;
    color: #f5e8ff;
    font-weight: 800;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border: 1px solid rgba(196,181,253,0.26);
    background: linear-gradient(135deg, rgba(139,92,246,0.22), rgba(79,70,229,0.14));
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.12);
    margin-bottom: 18px;
}

.hero-title {
    font-size: clamp(42px, 7vw, 84px);
    line-height: 0.98;
    font-weight: 900;
    margin: 0;
    color: white;
    letter-spacing: -0.05em;
    text-shadow: 0 10px 40px rgba(79,70,229,0.25);
}

.hero-subtitle {
    margin-top: 18px;
    font-size: 18px;
    line-height: 1.9;
    color: #dce8ff;
    max-width: 920px;
}

.hero-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 24px;
}

.hero-pill {
    border-radius: 999px;
    padding: 11px 15px;
    background: rgba(255,255,255,0.07);
    border: 1px solid var(--border);
    color: #e7ecff;
    font-size: 13px;
    font-weight: 700;
    box-shadow: var(--inner-light);
    transform-style: preserve-3d;
    transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
}

.hero-pill:hover {
    transform: translateY(-3px) translateZ(0);
    box-shadow: 0 12px 28px rgba(79,70,229,0.22);
    border-color: rgba(196,181,253,0.28);
}

.hero-side {
    position: relative;
    border-radius: 30px;
    border: 1px solid rgba(255,255,255,0.14);
    background:
        linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.05));
    backdrop-filter: blur(22px);
    -webkit-backdrop-filter: blur(22px);
    padding: 24px;
    box-shadow: var(--shadow-soft), var(--inner-light);
}

.hero-side::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(135deg, rgba(255,255,255,0.09), transparent 35%, transparent 65%, rgba(34,211,238,0.05));
    pointer-events: none;
}

.hero-side-title {
    color: white;
    font-size: 17px;
    font-weight: 800;
    margin-bottom: 10px;
}

.hero-side-text {
    color: #d6def8;
    font-size: 14px;
    line-height: 1.9;
}

.skills-heading {
    margin-top: 16px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 800;
}

.skills-cloud {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 12px;
}

.about-chip {
    padding: 8px 12px;
    border-radius: 999px;
    background: linear-gradient(135deg, rgba(139,92,246,0.16), rgba(79,70,229,0.14));
    color: #f0ebff;
    border: 1px solid rgba(196,181,253,0.22);
    font-size: 12px;
    font-weight: 700;
    box-shadow: var(--inner-light);
}

.section-shell {
    position: relative;
    border: 1px solid var(--border);
    background:
        linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 32px;
    padding: 24px;
    box-shadow: var(--shadow), var(--inner-light);
    margin-top: 18px;
}

.section-shell::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(135deg, rgba(255,255,255,0.06), transparent 26%, transparent 74%, rgba(79,70,229,0.04));
    pointer-events: none;
}

.section-kicker {
    color: #c4b5fd;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 8px;
}

.section-title {
    color: white;
    font-size: clamp(28px, 3vw, 38px);
    font-weight: 850;
    letter-spacing: -0.03em;
    margin-bottom: 8px;
}

.section-subtitle {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.85;
    margin-bottom: 20px;
    max-width: 1100px;
}

.full-width-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 18px;
    align-items: start;
}

.input-panel,
.output-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    width: 100%;
}

.glass-card {
    position: relative;
    border: 1px solid var(--border);
    background:
        linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.05));
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border-radius: 28px;
    box-shadow: var(--shadow-soft), var(--inner-light);
    transform-style: preserve-3d;
    transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
}

.glass-card::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(135deg, rgba(255,255,255,0.10), transparent 35%, transparent 68%, rgba(255,255,255,0.03));
    pointer-events: none;
}

.glass-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 22px 46px rgba(0,0,0,0.30), 0 0 28px rgba(124,58,237,0.10);
    border-color: rgba(196,181,253,0.24);
}

.clay-card,
.info-card,
.mini-panel,
.summary-item-card {
    background:
        linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
    border: 1px solid rgba(255,255,255,0.10);
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.10),
        inset -1px -1px 0 rgba(0,0,0,0.08),
        0 10px 24px rgba(0,0,0,0.18);
}

.upload-card,
.action-card {
    padding: 24px;
    text-align: center;
}

.summary-card,
.output-card,
.progress-card {
    padding: 22px;
}

.summary-top {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    align-items: flex-start;
    margin-bottom: 16px;
}

.summary-stack {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.summary-item-card {
    padding: 16px 18px;
    border-radius: 22px;
}

.summary-item-label {
    color: #c7d2fe;
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.summary-item-value {
    color: white;
    font-size: 14px;
    line-height: 1.7;
    word-break: break-word;
}

.stack-list {
    margin: 0;
    padding-left: 18px;
}

.stack-list li {
    color: #d8e1f8;
    margin-bottom: 8px;
    line-height: 1.65;
    font-size: 14px;
}

.upload-title {
    color: white;
    font-size: 30px;
    font-weight: 850;
    margin-bottom: 8px;
    letter-spacing: -0.03em;
}

.upload-text {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.85;
    margin-bottom: 12px;
}

.auto-pill {
    display: inline-flex;
    padding: 8px 12px;
    border-radius: 999px;
    background: linear-gradient(135deg, rgba(139,92,246,0.18), rgba(79,70,229,0.16));
    border: 1px solid rgba(196,181,253,0.22);
    color: #efe8ff;
    font-size: 12px;
    font-weight: 700;
    box-shadow: var(--inner-light);
}

.eyebrow {
    color: #c4b5fd;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 8px;
}

.card-title {
    color: white;
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 10px;
    letter-spacing: -0.02em;
}

.card-title.small {
    font-size: 18px;
}

.card-text {
    color: #d7e0fb;
    font-size: 14px;
    line-height: 1.9;
}

.preserve-lines {
    white-space: pre-wrap;
}

.info-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
}

.info-card,
.mini-panel {
    padding: 14px;
    border-radius: 22px;
}

.info-label,
.mini-title {
    color: #c7d2fe;
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 8px;
}

.info-value {
    color: white;
    font-size: 14px;
    line-height: 1.6;
    word-break: break-word;
}

.skills-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 8px;
    margin-bottom: 16px;
}

.skills-wrap.compact {
    margin-top: 0;
    margin-bottom: 0;
}

.skill-chip {
    padding: 8px 12px;
    border-radius: 999px;
    background: linear-gradient(135deg, rgba(139,92,246,0.18), rgba(79,70,229,0.14));
    color: #f0ebff;
    border: 1px solid rgba(196,181,253,0.22);
    font-size: 12px;
    font-weight: 700;
    box-shadow: var(--inner-light);
}

.mini-panel ul {
    margin: 0;
    padding-left: 18px;
}

.mini-panel li {
    color: #d8e1f8;
    margin-bottom: 8px;
    line-height: 1.6;
    font-size: 14px;
}

.question-text {
    color: white;
    font-size: 19px;
    line-height: 1.85;
    font-weight: 500;
}

.progress-top {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    align-items: flex-start;
    margin-bottom: 14px;
}

.pill-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.meta-pill {
    padding: 9px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    color: #eef2ff;
    font-size: 12px;
    font-weight: 700;
    box-shadow: var(--inner-light);
}

.progress-track {
    width: 100%;
    height: 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.08);
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #8b5cf6, #4f46e5, #22d3ee);
    box-shadow: 0 0 28px rgba(99,102,241,0.52);
    transition: width 0.35s ease;
}

.progress-foot {
    margin-top: 10px;
    color: var(--muted);
    font-size: 13px;
}

.timeline-vertical {
    position: relative;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    width: 100%;
}

.timeline-node {
    position: relative;
    border: 1px solid var(--border);
    background:
        linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
    backdrop-filter: blur(16px);
    border-radius: 24px;
    padding: 18px 18px 18px 18px;
    box-shadow: var(--shadow-soft), var(--inner-light);
    transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
}

.timeline-node::before {
    content: "";
    position: absolute;
    inset: -1px;
    border-radius: inherit;
    padding: 1px;
    background: linear-gradient(135deg, rgba(139,92,246,0.35), rgba(79,70,229,0.10), rgba(34,211,238,0.20));
    -webkit-mask:
        linear-gradient(#000 0 0) content-box,
        linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    pointer-events: none;
}

.timeline-node:hover {
    transform: translateY(-4px);
    box-shadow: 0 18px 34px rgba(0,0,0,0.24), 0 0 24px rgba(124,58,237,0.12);
    border-color: rgba(196,181,253,0.22);
}

.timeline-step {
    color: #c4b5fd;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
}

.timeline-title {
    color: white;
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 8px;
}

.timeline-text {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.8;
}

.results-hero {
    padding: 24px;
    display: grid;
    grid-template-columns: minmax(220px, 250px) minmax(0, 1fr);
    gap: 22px;
    align-items: center;
}

.score-orb {
    width: 220px;
    height: 220px;
    border-radius: 999px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background:
        radial-gradient(circle at 30% 28%, rgba(255,255,255,0.26), transparent 34%),
        linear-gradient(135deg, rgba(139,92,246,0.56), rgba(79,70,229,0.42), rgba(34,211,238,0.22));
    border: 1px solid rgba(255,255,255,0.14);
    box-shadow:
        0 0 46px rgba(124,58,237,0.30),
        inset 0 0 30px rgba(255,255,255,0.08),
        var(--inner-light);
    margin: 0 auto;
}

.score-number {
    color: white;
    font-size: 60px;
    font-weight: 900;
    line-height: 1;
}

.score-label {
    margin-top: 10px;
    color: #efe8ff;
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 16px;
}

.empty-card {
    padding: 28px 20px;
    border-radius: 28px;
    border: 1px dashed rgba(255,255,255,0.16);
    background: rgba(255,255,255,0.03);
    box-shadow: var(--inner-light);
}

.empty-title {
    color: white;
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 8px;
}

.empty-text {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.8;
}

footer {
    display: none !important;
}

.gr-button, button {
    position: relative;
    overflow: hidden !important;
    border-radius: 18px !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    background:
        linear-gradient(135deg, rgba(139,92,246,0.96), rgba(79,70,229,0.94), rgba(34,211,238,0.85)) !important;
    color: white !important;
    font-weight: 800 !important;
    letter-spacing: 0.02em;
    box-shadow:
        0 14px 30px rgba(79,70,229,0.28),
        0 0 24px rgba(139,92,246,0.18),
        inset 0 1px 0 rgba(255,255,255,0.14) !important;
    transition: transform 0.22s ease, box-shadow 0.22s ease, filter 0.22s ease !important;
}

.gr-button::before, button::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(110deg, transparent 15%, rgba(255,255,255,0.28) 45%, transparent 75%);
    transform: translateX(-130%);
    transition: transform 0.7s ease;
    pointer-events: none;
}

.gr-button:hover::before, button:hover::before {
    transform: translateX(130%);
}

.gr-button:hover, button:hover {
    transform: translateY(-2px);
    box-shadow:
        0 18px 34px rgba(79,70,229,0.36),
        0 0 34px rgba(124,58,237,0.28),
        inset 0 1px 0 rgba(255,255,255,0.16) !important;
    filter: brightness(1.03);
}

.upload-resume-btn button {
    min-height: 60px !important;
    height: 60px !important;
    width: 100% !important;
    border-radius: 20px !important;
    font-size: 16px !important;
}

.small-action button,
.small-download button {
    min-height: 48px !important;
    height: 48px !important;
    width: 100% !important;
    border-radius: 16px !important;
    font-size: 14px !important;
}

input, textarea, .gr-box, .gr-input, .gr-textbox, .gr-dropdown, .gr-file, .gr-audio {
    border-radius: 20px !important;
}

textarea, input, .wrap, .gr-box, .gr-form, .gr-file, .gr-audio, .gr-dropdown, .gr-textbox {
    background: rgba(255,255,255,0.06) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08) !important;
}

textarea:focus, input:focus {
    border-color: rgba(196,181,253,0.35) !important;
    box-shadow:
        0 0 0 2px rgba(139,92,246,0.12),
        inset 0 1px 0 rgba(255,255,255,0.08) !important;
}

label, .gr-form > label, .gr-block-label {
    color: #dbe4ff !important;
    font-weight: 700 !important;
}

::placeholder {
    color: #9fb2d6 !important;
}

.gr-chatbot {
    border-radius: 28px !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    background: rgba(255,255,255,0.05) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-soft), var(--inner-light);
}

.message-row .message, .bubble {
    border-radius: 20px !important;
}

.control-row {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
}

.results-actions-stack {
    display: flex;
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
    width: 100%;
    margin-top: 18px;
}

.reveal-up {
    opacity: 0;
    transform: translateY(34px);
    transition: opacity 0.8s ease, transform 0.8s cubic-bezier(.2,.8,.2,1);
    will-change: opacity, transform;
}

.reveal-up.is-visible {
    opacity: 1;
    transform: translateY(0);
}

@media (max-width: 1280px) {
    .timeline-vertical {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 1100px) {
    .hero-grid,
    .dashboard-grid,
    .results-hero,
    .info-grid,
    .control-row,
    .summary-top {
        grid-template-columns: 1fr !important;
        flex-direction: column;
    }

    .hero-side {
        min-height: auto;
    }

    .score-orb {
        width: 190px;
        height: 190px;
    }
}

@media (max-width: 768px) {
    .gradio-container {
        padding: 10px 10px 24px 10px !important;
    }

    .hero-wrap,
    .section-shell {
        padding: 16px;
        border-radius: 24px;
    }

    .hero-title {
        font-size: 40px;
    }

    .hero-subtitle {
        font-size: 15px;
        line-height: 1.75;
    }

    .section-title {
        font-size: 24px;
    }

    .card-title {
        font-size: 20px;
    }

    .timeline-vertical,
    .dashboard-grid,
    .control-row {
        grid-template-columns: 1fr !important;
    }

    .results-hero {
        grid-template-columns: 1fr !important;
        text-align: left;
    }

    .question-text {
        font-size: 17px;
    }

    .upload-title {
        font-size: 26px;
    }

    .summary-card,
    .output-card,
    .progress-card,
    .upload-card,
    .action-card {
        padding: 18px;
    }
}
"""

cursor_script = """
<script>
document.addEventListener("mousemove", function(e){
  document.documentElement.style.setProperty("--mx", e.clientX + "px");
  document.documentElement.style.setProperty("--my", e.clientY + "px");
});

(function(){
  const applyReveal = () => {
    const items = document.querySelectorAll('.reveal-up');
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
        }
      });
    }, { threshold: 0.12 });

    items.forEach((item) => observer.observe(item));
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyReveal);
  } else {
    applyReveal();
  }

  const rerunReveal = () => {
    document.querySelectorAll('.reveal-up').forEach((el, idx) => {
      setTimeout(() => el.classList.add('is-visible'), idx * 40);
    });
  };

  setTimeout(rerunReveal, 500);
  document.addEventListener("click", () => setTimeout(rerunReveal, 500));
})();
</script>
"""

with gr.Blocks(theme=theme, css=custom_css) as demo:
    profile_state = gr.State({})
    inferred_role_state = gr.State("Other")
    uploaded_resume_state = gr.State(None)
    runtime_state = gr.State({})
    report_state = gr.State({})
    comparison_state = gr.State({})
    analytics_state = gr.State({})
    report_text_state = gr.State("")
    comparison_text_state = gr.State("")

    gr.HTML(cursor_script)

    gr.HTML(
        """
        <div class="main-shell reveal-up">
            <div class="hero-wrap">
                <div class="hero-grid">
                    <div>
                        <div class="hero-badge">Premium AI Interview Experience</div>
                        <h1 class="hero-title">IntervueIQ</h1>
                        <div class="hero-subtitle">
                            Adaptive multi-role AI interview simulator with automatic role detection,
                            resume intelligence, voice support, performance analytics, and PDF reporting.
                        </div>
                        <div class="hero-pills">
                            <div class="hero-pill">Full-Screen Flow</div>
                            <div class="hero-pill">Glass Morphism</div>
                            <div class="hero-pill">Clay Morphism</div>
                            <div class="hero-pill">Smooth Scroll</div>
                            <div class="hero-pill">Scroll Reveal</div>
                            <div class="hero-pill">3D Premium Depth</div>
                        </div>
                    </div>
                    <div class="hero-side">
                        <div class="hero-side-title">About This Project</div>
                        <div class="hero-side-text">
                            IntervueIQ is an automatic AI interview simulator that parses resumes,
                            infers the most suitable role, runs adaptive interview questions,
                            evaluates answers, tracks progress, and generates exportable reports.
                        </div>
                        <div class="skills-heading">Skills & Technologies Used</div>
                        <div class="skills-cloud">
                            <span class="about-chip">Python</span>
                            <span class="about-chip">Gradio</span>
                            <span class="about-chip">AI/ML Workflow Design</span>
                            <span class="about-chip">Resume Parsing</span>
                            <span class="about-chip">Role Inference</span>
                            <span class="about-chip">Interview Evaluation</span>
                            <span class="about-chip">Voice Transcription</span>
                            <span class="about-chip">PDF Generation</span>
                            <span class="about-chip">Email Automation</span>
                            <span class="about-chip">Analytics</span>
                            <span class="about-chip">State Management</span>
                            <span class="about-chip">UI/UX Design</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    )

    with gr.Column(elem_classes=["section-shell", "reveal-up"]):
        gr.HTML(
            """
            <div class="section-kicker">Top Layout</div>
            <div class="section-title">Full-Screen Resume Workspace</div>
            <div class="section-subtitle">
                No split screen. Everything flows in a clean full-width layout with premium cards,
                smooth transitions, better readability, and stronger mobile responsiveness.
            </div>
            """
        )

        with gr.Row(elem_classes=["full-width-grid"]):
            with gr.Column(elem_classes=["input-panel"]):
                gr.HTML(
                    """
                    <div class="glass-card upload-card reveal-up">
                        <div class="upload-title">Resume Upload</div>
                        <div class="upload-text">
                            Upload your PDF resume. The system will automatically detect the best-fit role for the interview.
                        </div>
                        <div class="auto-pill">Automatic Setup Enabled</div>
                    </div>
                    """
                )

                upload_resume = gr.UploadButton(
                    "Upload Resume (PDF)",
                    file_types=[".pdf"],
                    file_count="single",
                    elem_classes=["upload-resume-btn"],
                )

                gr.HTML(
                    """
                    <div class="glass-card action-card reveal-up">
                        <div class="upload-text" style="margin-bottom: 0;">
                            Click Analyze Resume to generate a clean structured summary with contact details, skills, experience, projects, and education.
                        </div>
                    </div>
                    """
                )

                analyze_btn = gr.Button(
                    "Analyze Resume",
                    variant="primary",
                    elem_classes=["small-action"],
                )

                summary_html = gr.HTML(
                    render_analysis_dashboard({}, "Other")
                )

            with gr.Column(elem_classes=["output-panel"]):
                gr.HTML(
                    """
                    <div class="timeline-vertical reveal-up">
                        <div class="timeline-node">
                            <div class="timeline-step">Step 01</div>
                            <div class="timeline-title">Upload Resume</div>
                            <div class="timeline-text">User uploads a PDF resume through the premium upload control.</div>
                        </div>
                        <div class="timeline-node">
                            <div class="timeline-step">Step 02</div>
                            <div class="timeline-title">Auto Detection</div>
                            <div class="timeline-text">The system parses the resume and infers the most suitable interview role automatically.</div>
                        </div>
                        <div class="timeline-node">
                            <div class="timeline-step">Step 03</div>
                            <div class="timeline-title">Adaptive Interview</div>
                            <div class="timeline-text">Questions are generated and evaluated with progress tracking and optional voice input.</div>
                        </div>
                        <div class="timeline-node">
                            <div class="timeline-step">Step 04</div>
                            <div class="timeline-title">Command Dashboard</div>
                            <div class="timeline-text">Final score, analytics, improvements, PDF export, and email delivery are generated.</div>
                        </div>
                    </div>
                    """
                )

    with gr.Column(elem_classes=["section-shell", "reveal-up"]):
        gr.HTML(
            """
            <div class="section-kicker">Middle Layout</div>
            <div class="section-title">Interview Workspace</div>
            <div class="section-subtitle">
                Start the interview, answer questions by text or voice, and track your progress in one clean full-width section.
            </div>
            """
        )

        progress_html = gr.HTML(
            render_progress(
                {
                    "answered": 0,
                    "total": 0,
                    "role": "—",
                    "completed": False,
                }
            )
        )

        question_html = gr.HTML(
            render_empty_card(
                "Interview not started",
                "Upload and analyze your resume first, then start the interview.",
            )
        )

        chatbot = gr.Chatbot(
            label="Interview Session",
            height=320,
        )

        answer_box = gr.Textbox(
            placeholder="Type your answer here...",
            lines=5,
            label="Your Answer",
        )

        audio_input = gr.Audio(
            sources=["microphone", "upload"],
            type="filepath",
            label="Voice Answer (Optional)",
        )

        with gr.Row(elem_classes=["control-row"]):
            start_btn = gr.Button(
                "Start Interview",
                variant="primary",
                elem_classes=["small-action"],
            )
            transcribe_btn = gr.Button(
                "Transcribe Voice",
                elem_classes=["small-action"],
            )
            submit_btn = gr.Button(
                "Submit Answer",
                variant="primary",
                elem_classes=["small-action"],
            )

        final_report_btn = gr.Button(
            "Generate Final Report",
            variant="primary",
            elem_classes=["small-action"],
        )

    with gr.Column(elem_classes=["section-shell", "reveal-up"]):
        gr.HTML(
            """
            <div class="section-kicker">Bottom Layout</div>
            <div class="section-title">Command Dashboard</div>
            <div class="section-subtitle">
                Review outcome, analytics, improvement delta, export the report, and send it by email.
            </div>
            """
        )

        overview_html = gr.HTML(
            render_empty_card(
                "No report generated yet",
                "Complete the interview first, then generate your final performance dashboard.",
            )
        )

        with gr.Row(elem_classes=["dashboard-grid"]):
            comparison_html = gr.HTML(
                render_empty_card(
                    "Improvement Comparison",
                    "Comparison against previous sessions will appear here.",
                )
            )
            analytics_html = gr.HTML(
                render_empty_card(
                    "Analytics",
                    "Performance analytics will appear here after report generation.",
                )
            )

        with gr.Column(elem_classes=["results-actions-stack"]):
            pdf_file = gr.File(label="Download PDF Report", elem_classes=["small-download"])
            email_input = gr.Textbox(
                placeholder="Enter email address to receive the report",
                label="Send Report",
            )
            send_email_btn = gr.Button("Send Email", variant="primary", elem_classes=["small-action"])
            email_status = gr.Textbox(label="Email Status", lines=2)

    upload_resume.upload(
        fn=store_uploaded_resume,
        inputs=[upload_resume],
        outputs=[uploaded_resume_state],
    )

    analyze_btn.click(
        fn=analyze_resume,
        inputs=[uploaded_resume_state],
        outputs=[summary_html, inferred_role_state, profile_state],
    )

    start_btn.click(
        fn=start_interview,
        inputs=[profile_state, inferred_role_state],
        outputs=[runtime_state, question_html, chatbot, progress_html],
    )

    transcribe_btn.click(
        fn=transcribe_voice,
        inputs=[audio_input],
        outputs=[answer_box],
    )

    submit_btn.click(
        fn=handle_answer,
        inputs=[runtime_state, answer_box, chatbot],
        outputs=[runtime_state, chatbot, answer_box, progress_html, question_html],
    )

    final_report_btn.click(
        fn=generate_report,
        inputs=[runtime_state],
        outputs=[
            report_state,
            overview_html,
            comparison_state,
            comparison_html,
            analytics_state,
            analytics_html,
            report_text_state,
            comparison_text_state,
            pdf_file,
        ],
    )

    send_email_btn.click(
        fn=send_email_action,
        inputs=[email_input, report_text_state, comparison_text_state],
        outputs=[email_status],
    )

demo.launch()
