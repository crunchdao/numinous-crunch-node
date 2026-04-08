"""
RegisterModels task — reads models from ModelCluster and upserts them
into the miners SQLite table so that scoring/export can reference them.
"""

from datetime import datetime, timezone

from neurons.validator.db.operations import DatabaseOperations
from neurons.validator.scheduler.task import AbstractTask
from neurons.validator.utils.logger.logger import NuminousLogger


class RegisterModels(AbstractTask):
    def __init__(
        self,
        interval_seconds: float,
        db_operations: DatabaseOperations,
        model_cluster,
        logger: NuminousLogger,
    ):
        self.interval = interval_seconds
        self.db_operations = db_operations
        self.model_cluster = model_cluster
        self.logger = logger

    @property
    def name(self) -> str:
        return "register-models"

    @property
    def interval_seconds(self) -> float:
        return self.interval

    async def run(self) -> None:
        models = self.model_cluster.models_run

        if not models:
            self.logger.debug("No models to register")
            return

        miners_data = []
        now = datetime.now(timezone.utc).isoformat()

        for model in models.values():
            infos = model.infos
            miner_uid = str(infos.get("miner_uid", infos.get("id", 0)))
            miner_hotkey = infos.get("miner_hotkey", infos.get("hotkey", f"model-{miner_uid}"))
            node_ip = infos.get("node_ip", "")
            blocktime = infos.get("blocktime", 0)
            is_validating = infos.get("is_validating", False)
            validator_permit = infos.get("validator_permit", False)

            # Format: [miner_uid, miner_hotkey, node_ip, registered_date, blocktime,
            #          is_validating, validator_permit, node_ip(update), blocktime(update)]
            miners_data.append([
                miner_uid,
                miner_hotkey,
                node_ip,
                now,
                blocktime,
                is_validating,
                validator_permit,
                node_ip,
                blocktime,
            ])

        if miners_data:
            await self.db_operations.upsert_miners(miners_data)
            self.logger.info(
                "Registered models as miners",
                extra={"n_models": len(miners_data)},
            )
