import logging
import os
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

NuminousEnvType = Literal["test", "prod"]


@dataclass(frozen=True)
class CrunchNodeConfig:
    # Core
    numinous_env: NuminousEnvType = field(
        default_factory=lambda: os.getenv("NUMINOUS_ENV", "test")
    )
    api_key: str = field(
        default_factory=lambda: os.environ["NUMINOUS_API_KEY"]
    )
    database_path: str = field(
        default_factory=lambda: os.getenv("DATABASE_PATH", "./crunch_node.db")
    )
    pg_dsn: str = field(
        default_factory=lambda: (
            os.getenv("PG_DSN")
            or "postgresql://{user}:{password}@{host}:{port}/{db}".format(
                user=os.getenv("POSTGRES_USER", "numinous"),
                password=os.getenv("POSTGRES_PASSWORD", "numinous"),
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                db=os.getenv("POSTGRES_DB", "numinous"),
            )
        )
    )

    # Sandbox
    run_registry_dir: str = field(
        default_factory=lambda: os.getenv("RUN_REGISTRY_DIR", "./deployment/gateway/run_registry/")
    )

    # Model Runner Client
    mrc_crunch_id: str = field(
        default_factory=lambda: os.environ["MRC_CRUNCH_ID"]
    )
    mrc_host: str = field(
        default_factory=lambda: os.getenv("MRC_HOST", "localhost")
    )
    mrc_port: int = field(
        default_factory=lambda: int(os.getenv("MRC_PORT", "8765"))
    )
    mrc_base_classname: str = field(
        default_factory=lambda: os.environ["MRC_BASE_CLASSNAME"]
    )
    mrc_secure_credentials_dir: str = field(
        default_factory=lambda: os.getenv("MRC_SECURE_CREDENTIALS_DIR", "")
    )

    # Task intervals (seconds)
    pull_events_interval: float = field(
        default_factory=lambda: float(os.getenv("PULL_EVENTS_INTERVAL", "50.0"))
    )
    resolve_events_interval: float = field(
        default_factory=lambda: float(os.getenv("RESOLVE_EVENTS_INTERVAL", "900.0"))
    )
    delete_events_interval: float = field(
        default_factory=lambda: float(os.getenv("DELETE_EVENTS_INTERVAL", "1800.0"))
    )
    run_models_interval: float = field(
        default_factory=lambda: float(os.getenv("RUN_MODELS_INTERVAL", "600.0"))
    )
    register_models_interval: float = field(
        default_factory=lambda: float(os.getenv("REGISTER_MODELS_INTERVAL", "300.0"))
    )
    scoring_interval: float = field(
        default_factory=lambda: float(os.getenv("SCORING_INTERVAL", "307.0"))
    )
    export_scores_interval: float = field(
        default_factory=lambda: float(os.getenv("EXPORT_SCORES_INTERVAL", "373.0"))
    )
    export_predictions_interval: float = field(
        default_factory=lambda: float(os.getenv("EXPORT_PREDICTIONS_INTERVAL", "180.0"))
    )
    export_agent_runs_interval: float = field(
        default_factory=lambda: float(os.getenv("EXPORT_AGENT_RUNS_INTERVAL", "300.0"))
    )
    export_agent_run_logs_interval: float = field(
        default_factory=lambda: float(os.getenv("EXPORT_AGENT_RUN_LOGS_INTERVAL", "600.0"))
    )
    db_cleaner_interval: float = field(
        default_factory=lambda: float(os.getenv("DB_CLEANER_INTERVAL", "53.0"))
    )
    db_vacuum_interval: float = field(
        default_factory=lambda: float(os.getenv("DB_VACUUM_INTERVAL", "300.0"))
    )

    # Logging
    log_level: int = field(
        default_factory=lambda: getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    )

    # Batch sizes
    export_batch_size: int = field(
        default_factory=lambda: int(os.getenv("EXPORT_BATCH_SIZE", "500"))
    )
    scoring_page_size: int = field(
        default_factory=lambda: int(os.getenv("SCORING_PAGE_SIZE", "100"))
    )
    run_models_timeout: int = field(
        default_factory=lambda: int(os.getenv("RUN_MODELS_TIMEOUT", "240"))
    )
