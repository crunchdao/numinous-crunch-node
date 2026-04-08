"""
CrunchNodeNuminousClient — replaces BT wallet auth with API key Bearer auth.

Inherits from the submodule's NuminousClient, overriding only the auth methods.
"""

import time
from unittest.mock import MagicMock

from neurons.validator.numinous_client.client import NuminousClient
from neurons.validator.utils.config import NuminousEnvType
from neurons.validator.utils.logger.logger import NuminousLogger


class CrunchNodeNuminousClient(NuminousClient):
    """NuminousClient that uses Bearer <api_key> instead of BT wallet signatures."""

    def __init__(
        self,
        env: NuminousEnvType,
        logger: NuminousLogger,
        api_key: str,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be a non-empty string.")

        super().__init__(env=env, logger=logger, bt_wallet=MagicMock())
        self.__api_key = api_key

    def make_auth_headers(self, data: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.__api_key}",
        }

    def make_get_auth_headers(self) -> dict[str, str]:
        timestamp = str(int(time.time()))
        return {
            **self.make_auth_headers(data=""),
            "X-Payload": f"crunch-node:{timestamp}",
        }
