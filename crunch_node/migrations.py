"""
Custom SQLite migrations on top of the submodule's alembic migrations.
"""

from neurons.validator.db.client import DatabaseClient


class CustomMigrations:
    def __init__(self, db_client: DatabaseClient):
        self.db_client = db_client

    async def run(self) -> None:
        await self._add_pg_exported_column()

    async def _add_pg_exported_column(self) -> None:
        columns = await self.db_client.many("PRAGMA table_info(events)")
        if not any(col[1] == "pg_exported" for col in columns):
            await self.db_client.update(
                "ALTER TABLE events ADD COLUMN pg_exported INTEGER DEFAULT 0"
            )