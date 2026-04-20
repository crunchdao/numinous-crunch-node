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
    reasoning_scores  JSONB,
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
    metadata          JSONB,
    cutoff            TIMESTAMPTZ,
    run_days_before_cutoff INTEGER,
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

CREATE TABLE IF NOT EXISTS reasoning (
    run_id            TEXT PRIMARY KEY,
    unique_event_id   TEXT NOT NULL,
    miner_uid         INTEGER NOT NULL,
    track             TEXT NOT NULL,
    reasoning         TEXT,
    reasoning_scored  BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS model_scores (
    miner_uid         INTEGER PRIMARY KEY,
    weighted_scores   JSONB,
    scores_by_pool    JSONB,
    computed_at       TIMESTAMPTZ
);
-- weighted_scores: {"MAIN": 0.23, "SIGNAL": 0.18}

CREATE TABLE IF NOT EXISTS leaderboard (
    miner_uid              INTEGER NOT NULL,
    track                  TEXT NOT NULL,
    rank                   INTEGER NOT NULL,
    weighted_score         DOUBLE PRECISION,
    event_count            INTEGER,
    global_brier           DOUBLE PRECISION,
    global_brier_count     INTEGER,
    geopolitics_brier      DOUBLE PRECISION,
    geopolitics_brier_count INTEGER,
    reasoning              DOUBLE PRECISION,
    computed_at            TIMESTAMPTZ,
    PRIMARY KEY (miner_uid, track)
);
