import json
from openai import OpenAI
from utils.config import OPENAI_API_KEY


class AIClient:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    def is_available(self) -> bool:
        return self.client is not None

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        if not self.client:
            raise ValueError("Missing OPENAI_API_KEY")

        response = self.client.responses.create(
            model="gpt-4.1-mini",
            temperature=temperature,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        text = response.output_text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start:end + 1])
            raise ValueError(f"Model did not return valid JSON:\n{text}")
