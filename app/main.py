import os
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .db import execute_sqlReturning_rows, get_dialect_name, reflect_schema_ddl
from .llm import LLMNotConfiguredError
from .nl_renderer import render_answer
from .sql_generator import generate_sql_from_question

app = FastAPI(title="NL-to-SQL Agent", version="0.1.0")


class AskRequest(BaseModel):
    question: str
    sql: Optional[str] = None  # optional manual SQL override


@app.get("/healthz")
async def healthz():
    return {"ok": True, "dialect": get_dialect_name()}


@app.get("/", response_class=HTMLResponse)
async def index():
    html = f"""
    <html>
      <head>
        <meta charset='utf-8'/>
        <title>NL-to-SQL Agent</title>
        <style>
          body {{ font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 40px; }}
          input, textarea {{ width: 100%; padding: 12px; margin: 8px 0; font-size: 16px; }}
          button {{ padding: 10px 16px; font-size: 16px; }}
          pre {{ background: #f6f8fa; padding: 12px; border-radius: 6px; overflow: auto; }}
          table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
          th, td {{ border: 1px solid #e5e7eb; padding: 8px; text-align: left; }}
          th {{ background: #f9fafb; }}
          .container {{ max-width: 900px; margin: 0 auto; }}
          .muted {{ color: #6b7280; font-size: 14px; }}
        </style>
      </head>
      <body>
        <div class="container">
          <h2>Ask your database</h2>
          <form id="ask-form">
            <textarea id="question" rows="3" placeholder="e.g., total revenue by city last quarter"></textarea>
            <div class="muted">Optional SQL override (SELECT only):</div>
            <textarea id="sql" rows="3" placeholder="SELECT ..."></textarea>
            <button type="submit">Ask</button>
          </form>
          <div id="result"></div>
        </div>
        <script>
          const form = document.getElementById('ask-form');
          const resultDiv = document.getElementById('result');
          form.addEventListener('submit', async (e) => {
            e.preventDefault();
            resultDiv.innerHTML = 'Running...';
            const question = document.getElementById('question').value;
            const sql = document.getElementById('sql').value || null;
            const res = await fetch('/ask', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ question, sql })
            });
            const data = await res.json();
            if (!res.ok) {
              resultDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
              return;
            }
            const tbl = (cols, rows) => {
              if (!rows || rows.length === 0) return '<div class="muted">No rows</div>';
              const thead = `<thead><tr>${cols.map(c=>`<th>${c}</th>`).join('')}</tr></thead>`;
              const tbody = `<tbody>${rows.slice(0, 50).map(r=>`<tr>${r.map(v=>`<td>${v}</td>`).join('')}</tr>`).join('')}</tbody>`;
              return `<table>${thead}${tbody}</table>`;
            };
            resultDiv.innerHTML = `
              <h3>Answer</h3>
              <p>${data.answer}</p>
              <h4>SQL</h4>
              <pre>${data.sql}</pre>
              <h4>Rows (${data.row_count})</h4>
              ${tbl(data.columns, data.rows)}
            `;
          });
        </script>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/ask")
async def ask(req: AskRequest):
    if not req.question and not req.sql:
        raise HTTPException(status_code=400, detail="Provide a question or SQL")

    dialect = get_dialect_name()

    # Determine SQL
    try:
        if req.sql:
            sql = req.sql
        else:
            sql = generate_sql_from_question(req.question, dialect=dialect)
    except LLMNotConfiguredError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate SQL: {e}")

    # Execute
    try:
        columns, rows = execute_sqlReturning_rows(sql)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {e}")

    # Summarize
    try:
        answer = render_answer(req.question or "", columns, rows)
    except Exception as e:
        answer = f"{len(rows)} rows returned."

    return JSONResponse(
        {
            "question": req.question,
            "dialect": dialect,
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "answer": answer,
            "row_count": len(rows),
        }
    )