"""
ExportScoresPg — reads unexported scores from SQLite, inserts into PostgreSQL,
then marks them as exported in SQLite.
"""

from neurons.validator.db.operations import DatabaseOperations
from neurons.validator.scheduler.task import AbstractTask
from neurons.validator.utils.logger.logger import NuminousLogger

from crunch_node.clients.pg_client import PgClient


class ExportScoresPg(AbstractTask):
    def __init__(
        self,
        interval_seconds: float,
        page_size: int,
        db_operations: DatabaseOperations,
        pg_client: PgClient,
        logger: NuminousLogger,
        crunch_node_uid: int,
        crunch_node_hotkey: str,
    ):
        self.interval = interval_seconds
        self.page_size = page_size
        self.db_operations = db_operations
        self.pg_client = pg_client
        self.logger = logger
        self.crunch_node_uid = crunch_node_uid
        self.crunch_node_hotkey = crunch_node_hotkey
        self.errors_count = 0

    @property
    def name(self) -> str:
        return "export-scores-pg"

    @property
    def interval_seconds(self) -> float:
        return self.interval

    async def run(self) -> None:
        scored_events = await self.db_operations.get_scored_events_for_export(
            max_events=self.page_size
        )
        if not scored_events:
            self.logger.debug("No scored events to export to PG")
        else:
            self.logger.debug(
                "Found scored events to export to PG",
                extra={"n_events": len(scored_events)},
            )

            for event in scored_events:
                scores = await self.db_operations.get_scores_for_export(event_id=event.event_id)
                if not scores:
                    self.errors_count += 1
                    self.logger.warning(
                        "No scores found for event",
                        extra={"event_id": event.event_id},
                    )
                    continue

                rows = [
                    (
                        s.event_id,
                        s.miner_uid,
                        s.miner_hotkey,
                        str(s.track),
                        s.prediction,
                        s.event_score,
                        s.spec_version,
                        float(event.outcome) if event.outcome else None,
                        self.crunch_node_uid,
                        self.crunch_node_hotkey,
                        s.created_at,
                    )
                    for s in scores
                ]

                try:
                    await self.pg_client.executemany(
                        """
                        INSERT INTO scores (
                            event_id, miner_uid, miner_hotkey, track,
                            prediction, event_score, spec_version,
                            outcome, coordinator_uid, coordinator_hotkey, scored_at
                        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                        ON CONFLICT (event_id, miner_uid, miner_hotkey, track)
                        DO UPDATE SET
                            prediction = EXCLUDED.prediction,
                            event_score = EXCLUDED.event_score,
                            spec_version = EXCLUDED.spec_version
                        """,
                        rows,
                    )
                except Exception:
                    self.errors_count += 1
                    self.logger.exception(
                        "Failed to export scores to PG",
                        extra={"event_id": event.event_id},
                    )
                    continue

                await self.db_operations.mark_scores_as_exported(event_id=event.event_id)
                await self.db_operations.mark_event_as_exported(
                    unique_event_id=event.unique_event_id
                )

        self.logger.debug(
            "Export scores PG task completed",
            extra={"errors_count": self.errors_count},
        )
        self.errors_count = 0
