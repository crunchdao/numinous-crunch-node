-- Numinous crunch-node PostgreSQL schema

CREATE TABLE IF NOT EXISTS predictions (
    unique_event_id   TEXT    NOT NULL,
    miner_uid         INTEGER NOT NULL,
    track             TEXT    NOT NULL,
    provider_type     TEXT,
    prediction        DOUBLE PRECISION,
    interval_start_minutes INTEGER,
    interval_agg_prediction DOUBLE PRECISION,
    interval_agg_count      INTEGER,
    interval_datetime       TIMESTAMPTZ,
    submitted_at      TIMESTAMPTZ,
    run_id            TEXT,
    version_id        TEXT,
    PRIMARY KEY (unique_event_id, miner_uid, track, interval_start_minutes)
);

CREATE TABLE IF NOT EXISTS scores (
    event_id          TEXT    NOT NULL,
    miner_uid         INTEGER NOT NULL,
    track             TEXT    NOT NULL,
    prediction        DOUBLE PRECISION,
    event_score       DOUBLE PRECISION,
    spec_version      INTEGER,
    outcome           DOUBLE PRECISION,
    scored_at         TIMESTAMPTZ,
    PRIMARY KEY (event_id, miner_uid, track)
);

CREATE TABLE IF NOT EXISTS agent_runs (
    run_id            TEXT PRIMARY KEY,
    unique_event_id   TEXT    NOT NULL,
    agent_version_id  TEXT,
    miner_uid         INTEGER NOT NULL,
    track             TEXT    NOT NULL,
    status            TEXT    NOT NULL,
    is_final          BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS events (
    unique_event_id   TEXT PRIMARY KEY,
    event_id          TEXT NOT NULL,
    market_type       TEXT,
    event_type        TEXT,
    title             TEXT,
    description       TEXT,
    outcome           TEXT,
    status            INTEGER NOT NULL,
    cutoff            TIMESTAMPTZ,
    registered_date   TIMESTAMPTZ,
    resolved_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ,
    tracks            JSONB
);

CREATE TABLE IF NOT EXISTS agent_run_logs (
    run_id            TEXT PRIMARY KEY,
    log_content       TEXT,
    created_at        TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ
);
