# NL-to-SQL Agent (LogicLoop-style)

A small FastAPI app that turns natural language questions into safe SQL, executes against your database, and returns a natural-language answer plus tabular results.

## Features
- Natural language to SQL using an LLM (OpenAI)
- Schema-aware prompting via live DB reflection
- Strong safety: SELECT-only, single-statement, auto LIMIT, keyword guard, configurable row caps
- Works with SQLite (default) and Postgres (via `DB_URL`)
- Simple web UI and JSON API

## Quickstart
1. Create `.env` from example and set keys
```bash
cp .env.example .env
# Edit .env to add OPENAI_API_KEY and desired DB_URL
```
2. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
3. Bootstrap sample data (SQLite)
```bash
python app/bootstrap.py
```
4. Run the server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API
- `POST /ask` with JSON `{ "question": "..." }`
- `GET /ask?question=...`

Response:
```json
{
  "question": "total revenue by city",
  "dialect": "sqlite",
  "sql": "SELECT ... LIMIT 200",
  "columns": ["city", "total_amount"],
  "rows": [["New York", 12345.67]],
  "answer": "Total revenue by city: New York $12,345.67 ...",
  "row_count": 1
}
```

## Configuration
- `OPENAI_API_KEY`: OpenAI key
- `OPENAI_MODEL`: model name (default `gpt-4o-mini`)
- `DB_URL`: SQLAlchemy URL (e.g., `sqlite:////workspace/app/data.db`, `postgresql+psycopg2://user:pass@host/db`)
- `MAX_RESULT_ROWS`: hard cap for results and default LIMIT (default 200)

## Notes
- The agent enforces SELECT-only SQL and blocks dangerous statements.
- If `OPENAI_API_KEY` is not set, it still runs but will not generate SQL or summaries; you can provide SQL manually for testing.