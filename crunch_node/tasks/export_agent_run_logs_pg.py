"""
ExportAgentRunLogsPg — reads unexported agent run logs from SQLite,
inserts into PostgreSQL, marks as exported in SQLite.
"""

from neurons.validator.db.operations import DatabaseOperations
from neurons.validator.scheduler.task import AbstractTask
from neurons.validator.utils.logger.logger import NuminousLogger

from crunch_node.clients.pg_client import PgClient


class ExportAgentRunLogsPg(AbstractTask):
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
        return "export-agent-run-logs-pg"

    @property
    def interval_seconds(self) -> float:
        return self.interval

    async def run(self) -> None:
        unexported_logs = await self.db_operations.get_unexported_agent_run_logs(
            limit=self.batch_size
        )

        if not unexported_logs:
            self.logger.debug("No unexported logs to export to PG")
        else:
            self.logger.debug(
                "Found unexported logs to export to PG",
                extra={"n_logs": len(unexported_logs)},
            )

            successfully_exported_run_ids = []

            for log in unexported_logs:
                try:
                    await self.pg_client.execute(
                        """
                        INSERT INTO agent_run_logs (run_id, log_content, created_at, updated_at)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (run_id) DO UPDATE SET
                            log_content = EXCLUDED.log_content,
                            updated_at = EXCLUDED.updated_at
                        """,
                        log.run_id,
                        log.log_content,
                        log.created_at,
                        log.updated_at,
                    )
                    successfully_exported_run_ids.append(log.run_id)
                except Exception:
                    self.errors_count += 1
                    self.logger.warning(
                        "Failed to export log to PG",
                        extra={"run_id": log.run_id},
                        exc_info=True,
                    )

            if successfully_exported_run_ids:
                await self.db_operations.mark_agent_run_logs_as_exported(
                    run_ids=successfully_exported_run_ids
                )
                self.logger.debug(
                    "Marked logs as exported",
                    extra={"n_logs": len(successfully_exported_run_ids)},
                )

        self.logger.debug(
            "Export logs PG task completed",
            extra={"errors_count": self.errors_count},
        )
        self.errors_count = 0
