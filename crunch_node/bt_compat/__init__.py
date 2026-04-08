"""
Mock bittensor, bittensor_wallet, and docker in sys.modules
so that submodule imports (neurons.validator.*) work without
installing any Bittensor or Docker dependency.

This module MUST be imported before any neurons.validator.* import.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# The submodule's own code does `from neurons.validator.xxx import ...`,
# so we need its directory on sys.path.
_SUBMODULE = str(Path(__file__).parents[2] / "numinous")
if _SUBMODULE not in sys.path:
    sys.path.insert(0, _SUBMODULE)

# Every module the submodule tries to import from bittensor/docker
# gets a MagicMock — attribute access returns more MagicMocks automatically.
for _mod in [
    "bittensor", "bittensor.core", "bittensor.core.config",
    "bittensor.core.metagraph", "bittensor.utils", "bittensor.utils.btlogging",
    "bittensor_wallet", "bittensor_wallet.wallet",
    "docker", "docker.errors",
]:
    sys.modules.setdefault(_mod, MagicMock())

# DockerException must be a real exception class (used in except clauses)
sys.modules["docker.errors"].DockerException = type("DockerException", (Exception,), {})

# Wallet must be the MagicMock CLASS (not an instance) so that
# isinstance(MagicMock(), MagicMock) → True in NuminousClient.__init__
sys.modules["bittensor_wallet"].Wallet = MagicMock
sys.modules["bittensor_wallet.wallet"].Wallet = MagicMock
