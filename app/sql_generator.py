from typing import Optional

from .db import get_dialect_name, reflect_schema_ddl, sanitize_and_validate_sql
from .llm import LLMClient, LLMNotConfiguredError


SQL_SYSTEM_PROMPT = (
    "You convert natural language questions into a SINGLE, SAFE SQL query.\n"
    "Rules:\n"
    "- Output only the SQL, no explanations.\n"
    "- Use the given SQL dialect.\n"
    "- SELECT-only. No writes, no DDL, no comments.\n"
    "- Use only tables/columns from the provided schema.\n"
    "- If the question is ambiguous, make the smallest reasonable assumption.\n"
    "- Always include an ORDER BY when returning many rows.\n"
    "- Always include a LIMIT.\n"
)


def build_prompt(question: str, dialect: str, schema_ddl: str) -> str:
    return (
        f"Dialect: {dialect}\n\n"
        f"Schema:\n{schema_ddl}\n\n"
        f"Question: {question}\n\n"
        f"Return ONLY the SQL."
    )


def generate_sql_from_question(question: str, *, dialect: Optional[str] = None, schema_ddl: Optional[str] = None) -> str:
    llm = LLMClient()
    if not llm.is_available():
        raise LLMNotConfiguredError("LLM not configured; set OPENAI_API_KEY to enable NL-to-SQL")

    if dialect is None:
        dialect = get_dialect_name()
    if schema_ddl is None:
        schema_ddl = reflect_schema_ddl()

    prompt = SQL_SYSTEM_PROMPT + "\n\n" + build_prompt(question, dialect, schema_ddl)
    sql = llm.generate(prompt, temperature=0.0, max_tokens=600)

    # Final safety pass
    safe_sql = sanitize_and_validate_sql(sql)
    return safe_sql