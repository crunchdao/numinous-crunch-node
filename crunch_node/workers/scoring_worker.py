"""
Scoring worker — standalone async loop that runs reasoning scoring
and leaderboard computation against PostgreSQL.

Runs independently from the main coordinator node.
"""

import asyncio

from neurons.validator.utils.logger.logger import NuminousLogger, create_logger

from crunch_node._logging import ExtraFormatter
from crunch_node.clients.pg_client import PgClient
from crunch_node.config import CrunchNodeConfig
from crunch_node.services.scoring_service import ScoringService
from crunch_node.tasks.score_reasoning import ScoreReasoning


async def main():
    config = CrunchNodeConfig()

    logger: NuminousLogger = create_logger("scoring-worker")
    ExtraFormatter.install(logger, config.log_level)

    pg_client = PgClient(dsn=config.pg_dsn)
    await pg_client.connect()

    score_reasoning = ScoreReasoning(
        interval_seconds=config.score_reasoning_interval,
        pg_client=pg_client,
        openai_api_key=config.openai_api_key,
        openai_model=config.openai_model,
        logger=logger,
    )

    scoring_service = ScoringService(pg_client=pg_client, logger=logger)

    logger.info(
        "Scoring worker started",
        extra={
            "score_reasoning_interval": config.score_reasoning_interval,
            "compute_leaderboard_interval": config.compute_leaderboard_interval,
            "openai_model": config.openai_model,
        },
    )

    try:
        await asyncio.gather(
            _run_loop(score_reasoning, logger),
            _run_loop_service(scoring_service, config.compute_leaderboard_interval, logger),
        )
    finally:
        await pg_client.close()


async def _run_loop(task: ScoreReasoning, logger: NuminousLogger) -> None:
    while True:
        try:
            await task.run()
        except Exception:
            logger.exception(f"Error in {task.name}")
        await asyncio.sleep(task.interval_seconds)


async def _run_loop_service(
    service: ScoringService, interval: float, logger: NuminousLogger
) -> None:
    while True:
        try:
            await service.compute_all()
        except Exception:
            logger.exception("Error in compute_all")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())