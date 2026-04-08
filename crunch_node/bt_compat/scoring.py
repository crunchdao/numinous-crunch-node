"""
CrunchNodeScoring — scoring without metagraph/subtensor.

Uses all miners from the DB directly (no metagraph filtering).
"""

import pandas as pd

from neurons.validator.db.operations import DatabaseOperations
from neurons.validator.tasks.scoring import Scoring, ScoreNames
from neurons.validator.utils.common.converters import pydantic_models_to_dataframe
from neurons.validator.utils.common.interval import minutes_since_epoch, to_utc
from neurons.validator.utils.logger.logger import NuminousLogger
from neurons.validator.version import __spec_version__ as spec_version


class CrunchNodeScoring(Scoring):
    """Scoring task that skips metagraph sync — uses all DB miners."""

    def __init__(
        self,
        interval_seconds: float,
        db_operations: DatabaseOperations,
        logger: NuminousLogger,
        page_size: int = 100,
    ):
        if not isinstance(interval_seconds, float) or interval_seconds <= 0:
            raise ValueError("interval_seconds must be a positive number (float).")
        if not isinstance(db_operations, DatabaseOperations):
            raise TypeError("db_operations must be an instance of DatabaseOperations.")

        # Skip parent __init__ entirely (it requires netuid/subtensor).
        # Initialize the fields we need directly.
        self.interval = interval_seconds
        self.db_operations = db_operations
        self.logger = logger
        self.page_size = page_size
        self.spec_version = spec_version

        self.current_hotkeys = None
        self.n_hotkeys = None
        self.current_uids = None
        self.current_miners_df = None
        self.miners_last_reg = None
        self.errors_count = 0

    @property
    def name(self):
        return "scoring"

    @property
    def interval_seconds(self):
        return self.interval

    async def miners_last_reg_sync(self) -> bool:
        """Load all miners from DB — no metagraph filtering."""
        miners_last_reg_rows = await self.db_operations.get_miners_last_registration()
        if not miners_last_reg_rows:
            self.errors_count += 1
            self.logger.error("No miners found in the DB, skipping scoring!")
            return False

        miners_last_reg = pydantic_models_to_dataframe(miners_last_reg_rows)
        miners_last_reg[ScoreNames.miner_uid] = miners_last_reg[ScoreNames.miner_uid].astype(
            pd.Int64Dtype()
        )

        # No metagraph inner join — use all DB miners directly
        self.miners_last_reg = miners_last_reg
        self.current_miners_df = miners_last_reg[
            [ScoreNames.miner_uid, ScoreNames.miner_hotkey]
        ].copy()

        if self.miners_last_reg.empty:
            self.logger.error("No miners in DB, skipping scoring!")
            return False

        self.miners_last_reg[ScoreNames.miner_registered_minutes] = (
            self.miners_last_reg[ScoreNames.registered_date]
            .apply(to_utc)
            .apply(minutes_since_epoch)
        )

        return True

    async def run(self):
        """Score events — no metagraph sync needed."""
        miners_synced = await self.miners_last_reg_sync()
        if not miners_synced:
            return

        events_to_score = await self.db_operations.get_events_for_scoring()
        if not events_to_score:
            self.logger.debug("No events to calculate scores.")
        else:
            self.logger.debug(
                "Found events to calculate scores.",
                extra={"n_events": len(events_to_score)},
            )

            for event in events_to_score:
                try:
                    await self._score_single_event(event)
                except Exception as exc:
                    self.errors_count += 1
                    self.logger.exception(
                        "Failed to score event, skipping.",
                        extra={"event_id": event.event_id, "error": str(exc)},
                    )

        self.logger.debug(
            "Scoring run finished. Resetting errors count.",
            extra={"errors_count_in_logs": self.errors_count},
        )
        self.errors_count = 0
