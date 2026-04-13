import fitz
import re
from utils.helpers import clean_text


def preserve_resume_structure(text: str) -> str:
    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines = []
    for line in text.split("\n"):
        line = clean_text(line).strip()
        if line:
            cleaned_lines.append(line)

    structured_text = "\n".join(cleaned_lines)

    # Collapse excessive blank lines but keep section boundaries
    structured_text = re.sub(r"\n{3,}", "\n\n", structured_text)
    return structured_text.strip()


def extract_text_from_pdf(file_path: str) -> str:
    text_chunks = []
    doc = fitz.open(file_path)

    for page in doc:
        page_text = page.get_text("text")
        text_chunks.append(page_text)

    doc.close()

    raw_text = "\n\n".join(text_chunks)
    return preserve_resume_structure(raw_text)


def extract_resume_text(uploaded_file, pasted_text: str) -> str:
    if uploaded_file is not None:
        file_path = uploaded_file if isinstance(uploaded_file, str) else getattr(uploaded_file, "name", None)
        if file_path:
            return extract_text_from_pdf(file_path)

    if pasted_text and pasted_text.strip():
        return preserve_resume_structure(pasted_text)

    return ""