"""Test CrunchNodeConfig loads from env vars."""

import os

import crunch_node.bt_compat  # noqa: F401


def test_config_defaults(monkeypatch):
    monkeypatch.setenv("NUMINOUS_API_KEY", "key123")
    monkeypatch.setenv("PG_DSN", "postgresql://localhost/test")
    monkeypatch.setenv("MRC_CRUNCH_ID", "crunch-1")
    monkeypatch.setenv("MRC_BASE_CLASSNAME", "some.module.ClassName")

    from crunch_node.config import CrunchNodeConfig
    cfg = CrunchNodeConfig()

    assert cfg.numinous_env == "test"
    assert cfg.api_key == "key123"
    assert cfg.pg_dsn == "postgresql://localhost/test"
    assert cfg.mrc_crunch_id == "crunch-1"
    assert cfg.pull_events_interval == 50.0
    assert cfg.scoring_interval == 307.0


def test_config_custom_intervals(monkeypatch):
    monkeypatch.setenv("NUMINOUS_API_KEY", "key")
    monkeypatch.setenv("PG_DSN", "postgresql://localhost/db")
    monkeypatch.setenv("MRC_CRUNCH_ID", "c1")
    monkeypatch.setenv("MRC_BASE_CLASSNAME", "some.module.ClassName")
    monkeypatch.setenv("PULL_EVENTS_INTERVAL", "120.0")
    monkeypatch.setenv("SCORING_INTERVAL", "500.0")

    from crunch_node.config import CrunchNodeConfig
    cfg = CrunchNodeConfig()

    assert cfg.pull_events_interval == 120.0
    assert cfg.scoring_interval == 500.0