import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


class LLMNotConfiguredError(RuntimeError):
    pass


class LLMClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not self.api_key or OpenAI is None:
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)

    def is_available(self) -> bool:
        return self.client is not None

    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: Optional[int] = None) -> str:
        if not self.client:
            raise LLMNotConfiguredError("OPENAI_API_KEY not set or openai package missing")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a careful senior data analyst. Be concise."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()