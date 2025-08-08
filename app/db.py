import os
from contextlib import contextmanager
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DB_URL = os.getenv("DB_URL", "sqlite:////workspace/app/data.db")
MAX_RESULT_ROWS = int(os.getenv("MAX_RESULT_ROWS", "200"))


def create_db_engine() -> Engine:
    is_sqlite = DB_URL.startswith("sqlite:")
    engine = create_engine(
        DB_URL,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        pool_pre_ping=True,
    )
    return engine


engine: Engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_dialect_name() -> str:
    return engine.dialect.name


def reflect_schema_ddl() -> str:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    lines: List[str] = []
    for table_name, table in sorted(metadata.tables.items()):
        col_defs = ", ".join(f"{c.name} {str(c.type)}" for c in table.columns)
        lines.append(f"CREATE TABLE {table_name} ({col_defs});")
    if not lines:
        return "-- (no tables)"
    return "\n".join(lines)


DANGEROUS_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "REPLACE",
    "ATTACH", "DETACH", "VACUUM", "PRAGMA", "GRANT", "REVOKE", "COMMENT", "MERGE",
}


def sanitize_and_validate_sql(sql: str) -> str:
    if not sql:
        raise ValueError("Empty SQL")
    cleaned = sql.strip().strip(";\n\r\t ")
    # Remove inline comments to reduce prompt injection vectors embedded in SQL
    lines = []
    for line in cleaned.splitlines():
        # Strip -- comments
        parts = line.split("--", 1)
        lines.append(parts[0])
    cleaned = "\n".join(lines).strip()

    upper = cleaned.upper()

    # Enforce single-statement, SELECT/CTE only
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise ValueError("Only SELECT/CTE queries are allowed")

    # Block dangerous keywords
    for kw in DANGEROUS_KEYWORDS:
        if f" {kw} " in f" {upper} ":
            raise ValueError(f"Disallowed keyword in SQL: {kw}")

    # Disallow multiple statements via semicolon
    if ";" in cleaned:
        raise ValueError("Multiple statements are not allowed")

    # Enforce LIMIT
    if " LIMIT " not in upper:
        cleaned = f"{cleaned} LIMIT {MAX_RESULT_ROWS}"
    else:
        # Try to cap if limit is too high (best-effort simple parse)
        try:
            limit_part = upper.rsplit(" LIMIT ", 1)[1].strip()
            # Handle cases like 'LIMIT 100 OFFSET 0'
            limit_value_str = ''.join(ch for ch in limit_part if ch.isdigit()).strip()
            if limit_value_str:
                limit_value = int(limit_value_str)
                if limit_value > MAX_RESULT_ROWS:
                    cleaned = cleaned[: upper.rfind(" LIMIT ")]
                    cleaned = f"{cleaned} LIMIT {MAX_RESULT_ROWS}"
        except Exception:
            # If parsing fails, enforce our cap conservatively by appending another LIMIT via subquery
            cleaned = f"SELECT * FROM ({cleaned}) AS limited_subquery LIMIT {MAX_RESULT_ROWS}"

    return cleaned


def execute_sqlReturning_rows(sql: str) -> Tuple[List[str], List[List[Any]]]:
    safe_sql = sanitize_and_validate_sql(sql)
    with engine.connect() as conn:
        result = conn.execute(text(safe_sql))
        rows = [list(row) for row in result.fetchall()]
        columns = list(result.keys())
    return columns, rows


def execute_sqlReturning_dicts(sql: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    columns, rows = execute_sqlReturning_rows(sql)
    dict_rows = [dict(zip(columns, row)) for row in rows]
    return columns, dict_rows