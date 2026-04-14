"""
ExportAgentRunsPg — reads unexported agent runs from SQLite,
inserts into PostgreSQL, marks as exported in SQLite.
"""

from neurons.validator.db.operations import DatabaseOperations
from neurons.validator.scheduler.task import AbstractTask
from neurons.validator.utils.logger.logger import NuminousLogger

from crunch_node.clients.pg_client import PgClient


class ExportAgentRunsPg(AbstractTask):
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
        self.errors_count = 0

    @property
    def name(self) -> str:
        return "export-agent-runs-pg"

    @property
    def interval_seconds(self) -> float:
        return self.interval

    async def run(self) -> None:
        unexported_runs = await self.db_operations.get_unexported_agent_runs(
            limit=self.batch_size
        )

        if not unexported_runs:
            self.logger.debug("No unexported runs to export to PG")
        else:
            self.logger.debug(
                "Found unexported runs to export to PG",
                extra={"n_runs": len(unexported_runs)},
            )

            rows = [
                (
                    run.run_id,
                    run.unique_event_id,
                    run.agent_version_id,
                    run.miner_uid,
                    str(run.track),
                    run.status.value,
                    run.is_final,
                    run.created_at,
                    run.updated_at,
                )
                for run in unexported_runs
            ]

            try:
                await self.pg_client.executemany(
                    """
                    INSERT INTO agent_runs (
                        run_id, unique_event_id, agent_version_id,
                        miner_uid, track, status, is_final,
                        created_at, updated_at
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                    ON CONFLICT (run_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        is_final = EXCLUDED.is_final,
                        updated_at = EXCLUDED.updated_at
                    """,
                    rows,
                )
            except Exception:
                self.errors_count += 1
                self.logger.exception("Failed to export runs to PG")
                return

            run_ids = [run.run_id for run in unexported_runs]
            await self.db_operations.mark_agent_runs_as_exported(run_ids=run_ids)

        self.logger.debug(
            "Export runs PG task completed",
            extra={"errors_count": self.errors_count},
        )
        self.errors_count = 0
