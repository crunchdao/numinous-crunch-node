"""
ExportReasoningPg — reads unexported reasoning from SQLite,
inserts into PostgreSQL, marks as exported in SQLite.
"""

from neurons.validator.db.operations import DatabaseOperations
from neurons.validator.scheduler.task import AbstractTask
from neurons.validator.utils.logger.logger import NuminousLogger

from crunch_node.clients.pg_client import PgClient


class ExportReasoningPg(AbstractTask):
    def __init__(
        self,
        interval_seconds: float,
        batch_size: int,
        db_operations: DatabaseOperations,
        pg_client: PgClient,
        logger: NuminousLogger,
    ):
        self.interval = interval_seconds
        self.batch_size = batch_size
        self.db_operations = db_operations
        self.pg_client = pg_client
        self.logger = logger

    @property
    def name(self) -> str:
        return "export-reasoning-pg"

    @property
    def interval_seconds(self) -> float:
        return self.interval

    async def run(self) -> None:
        unexported = await self.db_operations.get_reasonings_for_export(
            limit=self.batch_size
        )

        if not unexported:
            self.logger.debug("No reasoning to export to PG")
            return

        rows = [
            (
                r.run_id,
                r.event_id,
                r.miner_uid,
                r.track,
                r.reasoning,
                r.created_at,
            )
            for r in unexported
        ]

        try:
            await self.pg_client.executemany(
                """
                INSERT INTO reasoning (
                    run_id, unique_event_id, miner_uid,
                    track, reasoning, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT (run_id) DO NOTHING
                """,
                rows,
            )
        except Exception:
            self.logger.exception("Failed to export reasoning to PG")
            return

        run_ids = [r.run_id for r in unexported]
        await self.db_operations.mark_reasonings_as_exported(run_ids=run_ids)

        self.logger.debug(
            "Exported reasoning to PG",
            extra={"count": len(run_ids)},
        )