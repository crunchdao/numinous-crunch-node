"""Test CrunchNodeScoring initializes without metagraph."""

import crunch_node.bt_compat  # noqa: F401

from unittest.mock import AsyncMock, MagicMock

import pytest

from crunch_node.bt_compat.scoring import CrunchNodeScoring
from neurons.validator.utils.logger.logger import create_logger


def test_scoring_init():
    logger = create_logger("test-scoring")
    db_ops = MagicMock()
    # Override isinstance check
    db_ops.__class__ = type("DatabaseOperations", (), {})

    scoring = CrunchNodeScoring.__new__(CrunchNodeScoring)
    scoring.interval = 300.0
    scoring.db_operations = db_ops
    scoring.logger = logger
    scoring.page_size = 100
    scoring.spec_version = 1000
    scoring.current_hotkeys = None
    scoring.n_hotkeys = None
    scoring.current_uids = None
    scoring.current_miners_df = None
    scoring.miners_last_reg = None
    scoring.errors_count = 0

    assert scoring.name == "scoring"
    assert scoring.interval_seconds == 300.0