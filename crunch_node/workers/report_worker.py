"""
Report worker — FastAPI app serving data from PostgreSQL.

Reads predictions, scores, agent runs directly from PG
and exposes them via REST endpoints.
"""

from contextlib import asynccontextmanager
from typing import TypedDict

import asyncpg
from fastapi import FastAPI

from crunch_node.config import CrunchNodeConfig

config = CrunchNodeConfig()
_pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = await asyncpg.create_pool(config.pg_dsn, min_size=2, max_size=10)

    try:
        yield
    finally:
        await _pool.close()
        _pool = None


app = FastAPI(
    title="Numinous Crunch Node — Report Worker",
    lifespan=lifespan,
)


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


class LeaderboardEntry(TypedDict):
    model_id: int
    brier_score: float
    event_count: int


@app.get("/leaderboard")
async def get_leaderboard(
    max_event_count: int | None = None,
) -> list[LeaderboardEntry]:
    max_event_count = max_event_count or 101

    rows = await _pool.fetch(
        """
            SELECT
                miner_uid,
                COUNT(*)         AS event_count,
                AVG(event_score) AS avg_score
            FROM (
                SELECT
                    miner_uid,
                    event_score,
                    ROW_NUMBER() OVER (PARTITION BY miner_uid ORDER BY scored_at DESC) AS rn
                FROM public.scores
            ) ranked
            WHERE rn <= $1
            GROUP BY miner_uid
            ORDER BY miner_uid
        """,
        *[
            max_event_count,
        ]
    )

    entries = []
    for row in rows:
        model_id = row["miner_uid"]

        score = row["avg_score"]
        if score is not None:
            entries.append({
                "model_id": model_id,
                "brier_score": score,
                "event_count": row["event_count"],
            })

    entries.sort(key=lambda x: x["brier_score"])

    return entries


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
