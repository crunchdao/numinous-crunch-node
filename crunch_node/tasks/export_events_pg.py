"""
ExportEventsPg — reads unexported events from SQLite,
inserts into PostgreSQL, marks as exported in SQLite.

Uses a custom `pg_exported` column (added via ALTER TABLE at startup)
since the built-in `exported` flag is already used by the scores export.
"""

from datetime import datetime
from typing import Optional

from neurons.validator.db.client import DatabaseClient
from neurons.validator.scheduler.task import AbstractTask
from neurons.validator.utils.logger.logger import NuminousLogger

from crunch_node.clients.pg_client import PgClient


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value)

_FIELDS = (
    "unique_event_id, event_id, market_type, event_type, title, description,"
    " outcome, status, metadata, cutoff, run_days_before_cutoff,"
    " registered_date, resolved_at, created_at, tracks"
)


class ExportEventsPg(AbstractTask):
    def __init__(
        self,
        interval_seconds: float,
        batch_size: int,
        db_client: DatabaseClient,
        pg_client: PgClient,
        logger: NuminousLogger,
    ):
        self.interval = interval_seconds
        self.batch_size = batch_size
        self.db_client = db_client
        self.pg_client = pg_client
        self.logger = logger
        self.errors_count = 0

    @property
    def name(self) -> str:
        return "export-events-pg"

    @property
    def interval_seconds(self) -> float:
        return self.interval

    async def run(self) -> None:
        rows = await self.db_client.many(
            f"SELECT {_FIELDS} FROM events WHERE pg_exported = 0 LIMIT ?",
            parameters=[self.batch_size],
            use_row_factory=True,
        )

        if not rows:
            self.logger.debug("No unexported events to export to PG")
        else:
            self.logger.debug(
                "Found unexported events to export to PG",
                extra={"n_events": len(rows)},
            )

            pg_rows = [
                (
                    row["unique_event_id"],
                    row["event_id"],
                    row["market_type"],
                    row["event_type"],
                    row["title"],
                    row["description"],
                    row["outcome"],
                    int(row["status"]),
                    row["metadata"],
                    _parse_dt(row["cutoff"]),
                    int(row["run_days_before_cutoff"]),
                    _parse_dt(row["registered_date"]),
                    _parse_dt(row["resolved_at"]),
                    _parse_dt(row["created_at"]),
                    row["tracks"],
                )
                for row in rows
            ]

            try:
                await self.pg_client.executemany(
                    """
                    INSERT INTO events (
                        unique_event_id, event_id, market_type, event_type,
                        title, description, outcome, status,
                        metadata, cutoff, run_days_before_cutoff,
                        registered_date, resolved_at, created_at, tracks
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                    ON CONFLICT (unique_event_id) DO UPDATE SET
                        outcome = EXCLUDED.outcome,
                        status = EXCLUDED.status,
                        resolved_at = EXCLUDED.resolved_at
                    """,
                    pg_rows,
                )
            except Exception:
                self.errors_count += 1
                self.logger.exception("Failed to export events to PG")
                return

            event_ids = [row["unique_event_id"] for row in rows]
            placeholders = ",".join("?" for _ in event_ids)
            await self.db_client.update(
                f"UPDATE events SET pg_exported = 1 WHERE unique_event_id IN ({placeholders})",
                parameters=event_ids,
            )

            self.logger.debug(
                "Exported events to PG",
                extra={"n_events": len(event_ids)},
            )

        self.logger.debug(
            "Export events PG task completed",
            extra={"errors_count": self.errors_count},
        )
        self.errors_count = 0