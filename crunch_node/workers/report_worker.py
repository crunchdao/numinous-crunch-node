"""
Report worker — FastAPI app serving data from PostgreSQL.

Reads predictions, scores, agent runs directly from PG
and exposes them via REST endpoints.
"""

import os

import asyncpg
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Numinous Crunch Node — Report Worker")

_pool: asyncpg.Pool | None = None


def _pg_dsn() -> str:
    dsn = os.getenv("PG_DSN")
    if dsn:
        return dsn
    user = os.getenv("POSTGRES_USER", "numinous")
    password = os.getenv("POSTGRES_PASSWORD", "numinous")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "numinous")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@app.on_event("startup")
async def _startup():
    global _pool
    _pool = await asyncpg.create_pool(_pg_dsn(), min_size=2, max_size=10)


@app.on_event("shutdown")
async def _shutdown():
    if _pool:
        await _pool.close()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/predictions")
async def get_predictions(
    event_id: str | None = None,
    limit: int = 100,
):
    query = "SELECT * FROM predictions"
    args = []
    if event_id:
        query += " WHERE unique_event_id = $1"
        args.append(event_id)
    query += f" ORDER BY submitted_at DESC LIMIT {min(limit, 1000)}"

    rows = await _pool.fetch(query, *args)
    return [dict(r) for r in rows]


@app.get("/scores")
async def get_scores(
    event_id: str | None = None,
    limit: int = 100,
):
    query = "SELECT * FROM scores"
    args = []
    if event_id:
        query += " WHERE event_id = $1"
        args.append(event_id)
    query += f" ORDER BY scored_at DESC LIMIT {min(limit, 1000)}"

    rows = await _pool.fetch(query, *args)
    return [dict(r) for r in rows]


@app.get("/agent-runs")
async def get_agent_runs(
    event_id: str | None = None,
    limit: int = 100,
):
    query = "SELECT * FROM agent_runs"
    args = []
    if event_id:
        query += " WHERE unique_event_id = $1"
        args.append(event_id)
    query += f" ORDER BY created_at DESC LIMIT {min(limit, 1000)}"

    rows = await _pool.fetch(query, *args)
    return [dict(r) for r in rows]
