import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def wrap_text(text: str, max_chars: int = 95):
    words = text.split()
    lines = []
    current = []

    for word in words:
        trial = " ".join(current + [word])
        if len(trial) <= max_chars:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))

    return lines


def safe_filename(text: str, fallback: str = "candidate") -> str:
    if not text:
        return fallback

    text = text.strip()
    text = re.sub(r"[^A-Za-z0-9_\- ]+", "", text)
    text = text.replace(" ", "_")
    text = text[:40]

    return text or fallback


def build_pdf_report(
    candidate_name: str,
    role: str,
    mode: str,
    difficulty: str,
    report_text: str,
    comparison_text: str,
    output_dir: str = "data"
) -> str:
    os.makedirs(output_dir, exist_ok=True)

    safe_name = safe_filename(candidate_name)
    file_path = os.path.join(output_dir, f"{safe_name}_interview_report.pdf")

    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    x = 50
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "IntervueIQ Interview Report")
    y -= 30

    c.setFont("Helvetica", 11)
    header_lines = [
        f"Candidate: {candidate_name}",
        f"Role: {role}",
        f"Mode: {mode}",
        f"Difficulty: {difficulty}",
        ""
    ]

    for line in header_lines:
        c.drawString(x, y, line)
        y -= 18

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Final Summary")
    y -= 20

    c.setFont("Helvetica", 10)
    for line in wrap_text(report_text):
        c.drawString(x, y, line)
        y -= 15
        if y < 70:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Comparison Summary")
    y -= 20

    c.setFont("Helvetica", 10)
    for line in wrap_text(comparison_text):
        c.drawString(x, y, line)
        y -= 15
        if y < 70:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)

    c.save()
    return file_path