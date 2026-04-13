"""
Report worker — FastAPI app serving data from PostgreSQL.

Reads predictions, scores, agent runs directly from PG
and exposes them via REST endpoints.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal, TypedDict

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
    window: Literal["brier-24h", "brier-72h", "brier-7d"]
    brier_score: float
    event_count: int


@app.get("/leaderboard")
async def get_leaderboard(
    when: datetime | None = None,
) -> list[LeaderboardEntry]:
    if when:
        when = when.replace(tzinfo=None)  # Ensure naive datetime in UTC
    else:
        when = datetime.now(timezone.utc)

    rows = await _pool.fetch(
        """
            SELECT
                miner_uid,

                COUNT(CASE WHEN scored_at >= $2::timestamptz THEN 1 END) AS event_count_24h,
                AVG(CASE WHEN scored_at >= $2::timestamptz THEN event_score END) AS avg_score_24h,

                COUNT(CASE WHEN scored_at >= $3::timestamptz THEN 1 END) AS event_count_72h,
                AVG(CASE WHEN scored_at >= $3::timestamptz THEN event_score END) AS avg_score_72h,

                COUNT(*) AS event_count_7d,
                AVG(event_score) AS avg_score_7d
            FROM
                public.scores
            WHERE
                scored_at >= $4::timestamptz
                AND scored_at <= $1::timestamptz
            GROUP BY
                miner_uid
            ORDER BY
                miner_uid;
        """,
        *[
            when,
            when - timedelta(days=1),
            when - timedelta(days=3),
            when - timedelta(days=7),
        ]
    )

    entries_24h, entries_72h, entries_7d = [], [], []
    for row in rows:
        model_id = row["miner_uid"]

        score_24h = row["avg_score_24h"]
        if score_24h is not None:
            entries_24h.append({
                "model_id": model_id,
                "window": "brier-24h",
                "brier_score": score_24h,
                "event_count": row["event_count_24h"],
            })

        score_72h = row["avg_score_72h"]
        if score_72h is not None:
            entries_72h.append({
                "model_id": model_id,
                "window": "brier-72h",
                "brier_score": score_72h,
                "event_count": row["event_count_72h"],
            })

        score_7d = row["avg_score_7d"]
        if score_7d is not None:
            entries_7d.append({
                "model_id": model_id,
                "window": "brier-7d",
                "brier_score": score_7d,
                "event_count": row["event_count_7d"],
            })

    entries_24h.sort(key=lambda x: x["brier_score"])
    entries_72h.sort(key=lambda x: x["brier_score"])
    entries_7d.sort(key=lambda x: x["brier_score"])

    return [
        *entries_24h,
        *entries_72h,
        *entries_7d,
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
