"""Integration tests for ScoringService against a real PostgreSQL instance.

Uses testcontainers to spin up a fresh PostgreSQL container per session.
Run: python -m pytest tests/test_scoring_service.py -v
"""

import json
import sys
from pathlib import Path

# bt_compat (via conftest) mocks docker.* in sys.modules — restore real docker for testcontainers
import importlib
for mod_name in [k for k in sys.modules if k == "docker" or k.startswith("docker.")]:
    del sys.modules[mod_name]
import docker  # noqa: E402
importlib.import_module("docker.models.images")

import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from crunch_node.clients.pg_client import PgClient
from crunch_node.services.scoring_service import ScoringService

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "deployment" / "postgres" / "init-scripts" / "02-create-tables.sql"


@pytest.fixture(scope="module")
def postgres_dsn():
    with PostgresContainer("postgres:15") as pg:
        yield pg.get_connection_url().replace("psycopg2", "asyncpg").replace("+asyncpg", "")


@pytest_asyncio.fixture
async def pg(postgres_dsn, mock_logger):
    client = PgClient(dsn=postgres_dsn)
    await client.connect(min_size=1, max_size=2)

    schema = SCHEMA_PATH.read_text()
    async with client._pool.acquire() as conn:
        await conn.execute(schema)

    yield client

    # Truncate between tests for isolation
    for table in ["leaderboard", "model_scores", "scores", "events"]:
        await client.execute(f"TRUNCATE {table} CASCADE")

    await client.close()


async def _insert_event(pg, event_id, topics=None):
    metadata = json.dumps({"topics": topics or []})
    await pg.execute(
        """INSERT INTO events (unique_event_id, event_id, status, metadata)
           VALUES ($1, $2, 3, $3)""",
        event_id, event_id, metadata,
    )


async def _insert_score(pg, event_id, miner_uid, track, event_score, reasoning_scores=None):
    from datetime import datetime, timezone
    await pg.execute(
        """INSERT INTO scores (event_id, miner_uid, track, event_score, reasoning_scores, scored_at)
           VALUES ($1, $2, $3, $4, $5, $6)""",
        event_id, miner_uid, track, event_score,
        json.dumps(reasoning_scores) if reasoning_scores else None,
        datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_no_weighted_score_when_pools_incomplete(pg, mock_logger):
    """Without all 3 pools valid, miner has no weighted_score and no leaderboard entry."""
    for i in range(250):
        eid = f"ev-{i}"
        await _insert_event(pg, eid, topics=["Politics"])
        await _insert_score(pg, eid, miner_uid=1, track="SIGNAL", event_score=0.2)

    service = ScoringService(pg_client=pg, logger=mock_logger)
    await service.compute_all()

    row = await pg.fetchrow("SELECT * FROM model_scores WHERE miner_uid = 1")
    assert row is not None
    ws = json.loads(row["weighted_scores"]) if isinstance(row["weighted_scores"], str) else row["weighted_scores"]
    assert "SIGNAL" not in ws  # missing reasoning + geopolitics → no score

    lb = await pg.fetch("SELECT * FROM leaderboard WHERE miner_uid = 1")
    assert len(lb) == 0


@pytest.mark.asyncio
async def test_reasoning_inverted_score(pg, mock_logger):
    """Reasoning score 5 (best) maps to 0.0, score 1 (worst) maps to 1.0."""
    best = {"sources": 5, "evidence": 5, "weighting": 5, "uncertainties": 5, "mapping": 5}
    for i in range(250):
        eid = f"ev-{i}"
        await _insert_event(pg, eid, topics=["Politics"])
        await _insert_score(pg, eid, miner_uid=1, track="SIGNAL", event_score=0.1,
                            reasoning_scores=best if i < 100 else None)

    service = ScoringService(pg_client=pg, logger=mock_logger)
    await service.compute_all()

    row = await pg.fetchrow("SELECT * FROM model_scores WHERE miner_uid = 1")
    pools = json.loads(row["scores_by_pool"])
    reasoning_pool = next(p for p in pools if p["pool"] == "reasoning" and p["track"] == "SIGNAL")
    assert reasoning_pool["rolling_avg"] == pytest.approx(0.0, abs=0.01)
    assert reasoning_pool["event_count"] == 100


@pytest.mark.asyncio
async def test_leaderboard_ranking(pg, mock_logger):
    """Two miners with all 3 pools valid: lower weighted score gets rank 1."""
    good_reasoning = {"sources": 4, "evidence": 4, "weighting": 4, "uncertainties": 4, "mapping": 4}
    bad_reasoning = {"sources": 2, "evidence": 2, "weighting": 2, "uncertainties": 2, "mapping": 2}

    for i in range(250):
        # Global brier events
        eid_a = f"ev-a-{i}"
        eid_b = f"ev-b-{i}"
        await _insert_event(pg, eid_a, topics=["Politics"])
        await _insert_event(pg, eid_b, topics=["Politics"])
        await _insert_score(pg, eid_a, miner_uid=1, track="SIGNAL", event_score=0.1, reasoning_scores=good_reasoning)
        await _insert_score(pg, eid_b, miner_uid=2, track="SIGNAL", event_score=0.4, reasoning_scores=bad_reasoning)

        # Geopolitics events
        eid_ga = f"ev-ga-{i}"
        eid_gb = f"ev-gb-{i}"
        await _insert_event(pg, eid_ga, topics=["Geopolitics"])
        await _insert_event(pg, eid_gb, topics=["Geopolitics"])
        await _insert_score(pg, eid_ga, miner_uid=1, track="SIGNAL", event_score=0.1)
        await _insert_score(pg, eid_gb, miner_uid=2, track="SIGNAL", event_score=0.4)

    service = ScoringService(pg_client=pg, logger=mock_logger)
    await service.compute_all()

    lb = await pg.fetch("SELECT * FROM leaderboard WHERE track = 'SIGNAL' ORDER BY rank")
    assert len(lb) == 2
    assert lb[0]["miner_uid"] == 1
    assert lb[0]["rank"] == 1
    assert lb[1]["miner_uid"] == 2
    assert lb[1]["rank"] == 2


@pytest.mark.asyncio
async def test_geopolitics_pool(pg, mock_logger):
    """Geopolitics events go into geopolitics_brier pool, not global_brier."""
    # 250 geopolitics events for SIGNAL track (min_events=100 for geo SIGNAL)
    for i in range(250):
        eid = f"ev-geo-{i}"
        await _insert_event(pg, eid, topics=["Politics", "Geopolitics"])
        await _insert_score(pg, eid, miner_uid=1, track="SIGNAL", event_score=0.3)

    service = ScoringService(pg_client=pg, logger=mock_logger)
    await service.compute_all()

    row = await pg.fetchrow("SELECT * FROM model_scores WHERE miner_uid = 1")
    pools = json.loads(row["scores_by_pool"]) if isinstance(row["scores_by_pool"], str) else row["scores_by_pool"]

    geo_pool = next(p for p in pools if p["pool"] == "geopolitics_brier" and p["track"] == "SIGNAL")
    assert geo_pool["rolling_avg"] == pytest.approx(0.3, abs=0.01)
    assert geo_pool["event_count"] == 200  # capped at max_events=200

    # Global pool should have no events (geopolitics excluded)
    global_pool = next(p for p in pools if p["pool"] == "global_brier" and p["track"] == "SIGNAL")
    assert global_pool["rolling_avg"] is None
    assert global_pool["event_count"] == 0