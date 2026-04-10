"""
RegisterModels task — reads models from ModelCluster and upserts them
into the miners SQLite table so that scoring/export can reference them.
"""

from datetime import datetime, timezone

from model_runner_client.model_cluster import ModelCluster
from neurons.validator.db.operations import DatabaseOperations
from neurons.validator.models.miner_agent import MinerAgentsModel
from neurons.validator.scheduler.task import AbstractTask
from neurons.validator.utils.logger.logger import NuminousLogger


BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def base58_to_int(s: str) -> int:
    result = 0
    for char in s:
        result = result * 58 + BASE58_ALPHABET.index(char)
    
    long_max = 2**63 - 1
    return result % long_max

print(base58_to_int("6wyWqKLet5H22e1p2xB4dGy1edBQa9eqWP92a8X3ySw6"))

class RegisterModels(AbstractTask):
    def __init__(
        self,
        interval_seconds: float,
        db_operations: DatabaseOperations,
        model_cluster: ModelCluster,
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
            self.logger.warning("No models to register")
            return

        miners_data = []
        miner_agents = []
        now = datetime.now(timezone.utc).isoformat()

        for model in models.values():
            infos = model.infos
            miner_uid = base58_to_int(infos["cruncher_id"])  # TODO: Is it unique enough to identify a miner?
            miner_hotkey = infos["cruncher_hotkey"]
            node_ip = "0.0.0.0"
            blocktime = "0"
            is_validating = False
            validator_permit = False

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

            miner_agents.append(MinerAgentsModel(
                version_id=f"ver-{miner_uid}",
                miner_uid=miner_uid,
                miner_hotkey=miner_hotkey,
                track="MAIN",
                agent_name="default",
                version_number="1",
                file_path="/dev/null",
                pulled_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            ))

        if miners_data:
            await self.db_operations.upsert_miners(miners_data)
            self.logger.info(
                "Registered models as miners",
                extra={"n_models": len(miners_data)},
            )

            await self.db_operations.upsert_miner_agents(miner_agents)
