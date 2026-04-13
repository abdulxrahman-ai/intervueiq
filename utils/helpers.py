from datetime import datetime
import re


def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def generate_session_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")
