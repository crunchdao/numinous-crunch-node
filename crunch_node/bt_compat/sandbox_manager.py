from pathlib import Path
from unittest.mock import MagicMock

from neurons.validator.sandbox.manager import SandboxManager
from neurons.validator.utils.logger.logger import NuminousLogger


class CrunchNodeSandboxManager(SandboxManager):

    def __init__(
        self,
        run_registry_dir: str,
        logger: NuminousLogger,
    ) -> None:
        super().__init__(
            bt_wallet=MagicMock(),
            gateway_url="https://example.com",
            logger=logger,
        )

        self.run_registry_dir = Path(run_registry_dir)
        self.run_registry_dir.mkdir(parents=True, exist_ok=True)

    def _build_images(self, force_rebuild: bool) -> None:
        pass
