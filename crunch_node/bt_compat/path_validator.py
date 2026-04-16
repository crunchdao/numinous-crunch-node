import os

from lru import LRU
from neurons.validator.sandbox.signing_proxy.async_host import AsyncValidatorSigningProxy


class UnknownRunIdException(Exception):
    pass


class CrunchNodeAsyncValidatorSigningProxy(AsyncValidatorSigningProxy):

    def __init__(self, run_registry_dir: str):
        os.environ["RUN_REGISTRY_DIR"] = run_registry_dir
        super().__init__(
            wallet=None,
            proxy_upstream_url=None,
            port=None,
        )

        self.track_cache = LRU(50_000)  # magic number

    def _get_track(self, run_id: str) -> str | None:
        result = super()._get_track(run_id)

        if result is not None:
            return result

        raise UnknownRunIdException(f"Unknown run with id \"{run_id}\"")
