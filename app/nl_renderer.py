from typing import Any, Dict, List

from .llm import LLMClient


def render_answer(question: str, columns: List[str], rows: List[List[Any]]) -> str:
    if not rows:
        return "No results found."

    llm = LLMClient()
    sample_rows = rows[:10]

    if llm.is_available():
        header = ", ".join(columns)
        data_preview = "\n".join(
            [", ".join(str(v) for v in r) for r in sample_rows]
        )
        prompt = (
            "You are a data analyst. Provide a concise, plain-English answer to the user's question "
            "using the data provided. Avoid speculation. If aggregation is present, report the key numbers.\n\n"
            f"Question: {question}\n"
            f"Columns: {header}\n"
            f"Rows (up to 10 shown):\n{data_preview}\n\n"
            "Answer succinctly in 1-3 sentences."
        )
        try:
            return llm.generate(prompt, temperature=0.0, max_tokens=200)
        except Exception:
            pass

    # Fallback deterministic summary
    return f"Found {len(rows)} rows. Showing {min(len(rows), 10)} preview rows. Columns: {', '.join(columns)}."