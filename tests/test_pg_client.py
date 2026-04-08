"""Test PgClient interface."""

import crunch_node.bt_compat  # noqa: F401

from crunch_node.clients.pg_client import PgClient


def test_pg_client_init():
    client = PgClient(dsn="postgresql://user:pass@localhost:5432/db")
    assert client._dsn == "postgresql://user:pass@localhost:5432/db"
    assert client._pool is None