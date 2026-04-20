"""
Custom SQLite migrations on top of the submodule's alembic migrations.
"""

from neurons.validator.db.client import DatabaseClient


class CustomMigrations:
    def __init__(self, db_client: DatabaseClient):
        self.db_client = db_client

    async def run(self) -> None:
        await self._add_pg_exported_status_column()

    async def _add_pg_exported_status_column(self) -> None:
        columns = await self.db_client.many("PRAGMA table_info(events)")
        col_names = [col[1] for col in columns]
        if "pg_exported" in col_names:
            await self.db_client.update(
                "ALTER TABLE events RENAME COLUMN pg_exported TO pg_exported_status"
            )
        elif "pg_exported_status" not in col_names:
            await self.db_client.update(
                "ALTER TABLE events ADD COLUMN pg_exported_status INTEGER DEFAULT 0"
            )