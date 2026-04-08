"""Shared fixtures for numinous crunch-node tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure crunch_node package and numinous submodule are importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import bt_compat FIRST to install mocks
import crunch_node.bt_compat  # noqa: F401, E402


@pytest.fixture
def mock_logger():
    """A MagicMock that satisfies NuminousLogger isinstance checks."""
    from neurons.validator.utils.logger.logger import create_logger
    return create_logger("test")


@pytest.fixture
def mock_pg_client():
    client = MagicMock()
    client.execute = MagicMock(return_value=None)
    client.executemany = MagicMock(return_value=None)
    client.fetch = MagicMock(return_value=[])
    client.close = MagicMock(return_value=None)
    return client


@pytest.fixture
def mock_model_cluster():
    """A mock ModelCluster with one model (models_run is a dict)."""
    model = MagicMock()
    model.infos = {
        "miner_uid": 1,
        "miner_hotkey": "test-hotkey-1",
        "track": "MAIN",
        "version_id": "v1",
        "node_ip": "127.0.0.1",
    }
    model.model_id = "model-1"
    cluster = MagicMock()
    cluster.models_run = {"model-1": model}
    return cluster


@pytest.fixture
def mock_concurrent_runner(mock_model_cluster):
    """A mock DynamicSubclassModelConcurrentRunner."""
    runner = MagicMock()
    runner.model_cluster = mock_model_cluster
    runner.call = MagicMock(return_value={})
    return runner