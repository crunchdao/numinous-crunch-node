"""Test CoordinatorNuminousClient auth headers."""

import crunch_node.bt_compat  # noqa: F401

from crunch_node.bt_compat.numinous_client import CrunchNodeNuminousClient
from neurons.validator.utils.logger.logger import create_logger


def test_make_auth_headers():
    logger = create_logger("test-client")
    client = CrunchNodeNuminousClient(
        env="test",
        logger=logger,
        api_key="test-key-123",
    )

    headers = client.make_auth_headers(data="some-data")
    assert headers["Authorization"] == "Bearer test-key-123"


def test_make_get_auth_headers():
    logger = create_logger("test-client")
    client = CrunchNodeNuminousClient(
        env="test",
        logger=logger,
        api_key="my-secret-key",
    )

    headers = client.make_get_auth_headers()
    assert headers["Authorization"] == "Bearer my-secret-key"
    assert "X-Payload" in headers
    assert headers["X-Payload"].startswith("crunch-node:")


def test_base_url_prod():
    logger = create_logger("test-client")
    client = CrunchNodeNuminousClient(
        env="prod",
        logger=logger,
        api_key="prod-key",
    )
    # Access via name mangling
    assert client._NuminousClient__base_url == "https://numinous.earth"


def test_base_url_test():
    logger = create_logger("test-client")
    client = CrunchNodeNuminousClient(
        env="test",
        logger=logger,
        api_key="test-key",
    )
    assert client._NuminousClient__base_url == "https://stg.numinous.earth"