"""Test that bt_compat mocks allow submodule imports without bittensor."""

import sys


def test_bittensor_mocked():
    """bittensor should be in sys.modules after bt_compat import."""
    import crunch_node.bt_compat  # noqa: F401
    assert "bittensor" in sys.modules
    assert "bittensor_wallet" in sys.modules
    assert "docker" in sys.modules


def test_submodule_imports():
    """Key submodule modules should import without error."""
    import crunch_node.bt_compat  # noqa: F401

    from neurons.validator.scheduler.task import AbstractTask
    from neurons.validator.scheduler.tasks_scheduler import TasksScheduler
    from neurons.validator.db.client import DatabaseClient
    from neurons.validator.db.operations import DatabaseOperations
    from neurons.validator.models.event import EventsModel
    from neurons.validator.models.score import ScoresModel
    from neurons.validator.models.prediction import PredictionsModel

    assert AbstractTask is not None
    assert TasksScheduler is not None
    assert DatabaseClient is not None
    assert DatabaseOperations is not None
    assert EventsModel is not None
    assert ScoresModel is not None
    assert PredictionsModel is not None


def test_scoring_import():
    """Scoring class should import (it imports bittensor.AsyncSubtensor)."""
    import crunch_node.bt_compat  # noqa: F401
    from neurons.validator.tasks.scoring import Scoring
    assert Scoring is not None