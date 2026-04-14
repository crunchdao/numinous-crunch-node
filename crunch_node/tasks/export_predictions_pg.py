"""
ExportPredictionsPg — reads unexported predictions from SQLite,
inserts into PostgreSQL, marks as exported in SQLite.
"""

from datetime import datetime

from neurons.validator.db.operations import DatabaseOperations
from neurons.validator.scheduler.task import AbstractTask
from neurons.validator.utils.common.interval import get_interval_iso_datetime
from neurons.validator.utils.logger.logger import NuminousLogger

from crunch_node.clients.pg_client import PgClient


class ExportPredictionsPg(AbstractTask):
    def __init__(
        self,
        interval_seconds: float,
        db_operations: DatabaseOperations,
        pg_client: PgClient,
        batch_size: int,
        logger: NuminousLogger,
    ):
        self.interval = interval_seconds
        self.db_operations = db_operations
        self.pg_client = pg_client
        self.batch_size = batch_size
        self.logger = logger

    @property
    def name(self) -> str:
        return "export-predictions-pg"

    @property
    def interval_seconds(self) -> float:
        return self.interval

    async def run(self) -> None:
        while True:
            predictions = await self.db_operations.get_predictions_to_export(
                batch_size=self.batch_size
            )

            if not predictions:
                break

            rows = []
            for p in predictions:
                # p is a tuple from raw SQL: (ROWID, unique_event_id, miner_uid, miner_hotkey,
                #   track, event_type, latest_prediction, interval_start_minutes,
                #   interval_agg_prediction, interval_count, submitted, run_id, version_id)
                interval_start_minutes = p[7]
                rows.append((
                    p[1],   # unique_event_id
                    p[2],   # miner_uid
                    p[4],   # track
                    p[5],   # event_type (provider_type)
                    p[6],   # latest_prediction
                    interval_start_minutes,
                    p[8],   # interval_agg_prediction
                    p[9],   # interval_count
                    datetime.fromisoformat(get_interval_iso_datetime(interval_start_minutes)),
                    datetime.fromisoformat(p[10]),  # submitted_at
                    p[11],  # run_id
                    p[12],  # version_id
                ))

            try:
                await self.pg_client.executemany(
                    """
                    INSERT INTO predictions (
                        unique_event_id, miner_uid, track,
                        provider_type, prediction, interval_start_minutes,
                        interval_agg_prediction, interval_agg_count,
                        interval_datetime, submitted_at, run_id, version_id
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                    ON CONFLICT (unique_event_id, miner_uid, track, interval_start_minutes)
                    DO UPDATE SET
                        prediction = EXCLUDED.prediction,
                        interval_agg_prediction = EXCLUDED.interval_agg_prediction,
                        interval_agg_count = EXCLUDED.interval_agg_count
                    """,
                    rows,
                )
            except Exception:
                self.logger.exception("Failed to export predictions to PG")
                break

            ids = [p[0] for p in predictions]
            await self.db_operations.mark_predictions_as_exported(ids=ids)

            if len(predictions) < self.batch_size:
                break
