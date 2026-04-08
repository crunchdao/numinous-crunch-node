# numinous-crunch-node

## What is this project
Crunch node that replaces the Bittensor validator from numinous. Uses the validator as a git submodule but:
- Models are contacted via `model-runner-client` (gRPC) with `DynamicSubclassModelConcurrentRunner`
- Data is exported to PostgreSQL instead of the Numinous API
- Zero Bittensor/Docker dependency
- SQLite remains the internal working database (unchanged, uses alembic migrations from the submodule)

## Project structure
```
numinous-coordinator/
├── numinous/                          # git submodule (numinouslabs/numinous)
├── crunch_node/
│   ├── bt_compat/                     # Mocks for bittensor/docker + patched classes
│   │   ├── __init__.py                # sys.modules mocks (MUST be imported first)
│   │   ├── numinous_client.py         # Bearer API key auth (replaces BT wallet)
│   │   └── scoring.py                 # Scoring without metagraph
│   ├── clients/
│   │   └── pg_client.py               # asyncpg PostgreSQL pool wrapper
│   ├── tasks/
│   │   ├── run_models.py              # Replaces RunAgents → gRPC via DynamicSubclassModelConcurrentRunner
│   │   ├── register_models.py         # Maps model_cluster.models_run → miners table
│   │   ├── export_scores_pg.py        # SQLite → PostgreSQL
│   │   ├── export_predictions_pg.py   # SQLite → PostgreSQL
│   │   ├── export_agent_runs_pg.py    # SQLite → PostgreSQL
│   │   └── export_agent_run_logs_pg.py
│   ├── config.py                      # All config via env vars (see .env.example)
│   ├── main.py                        # Entry point
│   └── version.py
├── tests/                             # 11 tests, all passing
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## Key architectural decisions

### Import resolution
- Both the submodule and our code use `from neurons.validator.xxx import ...`
- `bt_compat/__init__.py` adds `numinous/` to `sys.path` so `neurons.validator.*` resolves to the submodule
- `bt_compat/__init__.py` **MUST** be imported before any submodule import

### bt_compat pattern
- `CrunchNodeNuminousClient` calls `super().__init__()` with a `MagicMock()` wallet, then overrides auth headers
- `CrunchNodeScoring` bypasses parent `__init__` (which requires netuid/subtensor) and uses all DB miners directly (no metagraph filtering)

### Model Runner Client
- `DynamicSubclassModelConcurrentRunner` manages model lifecycle (init, sync, call)
- `concurrent_runner.model_cluster` provides access to connected models
- `concurrent_runner.sync()` runs in parallel with the scheduler via `asyncio.gather`
- `concurrent_runner.call("predict", arguments)` calls all models concurrently (uses `asyncio.gather` internally)
- Optional `SecureCredentials` for TLS (from directory with ca.crt, tls.crt, tls.key)

### Submodule classes reused as-is
`PullEvents`, `ResolveEvents`, `DeleteEvents`, `DbCleaner`, `DbVacuum`, `DatabaseClient`, `DatabaseOperations`, `AbstractTask`, `TasksScheduler`, all Pydantic models

### Export tasks pattern (×4)
1. Read unexported data from SQLite (`db_operations.get_*`)
2. INSERT into PostgreSQL (`pg_client.executemany`) with `ON CONFLICT` upsert
3. Mark as exported in SQLite (`db_operations.mark_*_as_exported`)
- PostgreSQL uses `$1,$2,...` placeholders (asyncpg) vs `?` (aiosqlite)

## Commands
- **Run**: `python -m crunch_node.main` (or `numinous-crunch-node` after pip install)
- **Tests**: `python -m pytest tests/ -v`
- **Install deps**: `pip install -r requirements.txt`

## Dependencies note
- `colorama` is required by the submodule's logger (not in the original plan but needed)
- `model-runner-client` provides `DynamicSubclassModelConcurrentRunner` for gRPC model calls

## Scheduler tasks (12 total)
| Task | Source | Description |
|---|---|---|
| PullEvents | submodule | Fetch events from Numinous API |
| ResolveEvents | submodule | Update resolved events |
| DeleteEvents | submodule | Sync deleted events |
| RegisterModels | new | Map models → miners table |
| RunModels | new | Call models via gRPC, store predictions |
| CrunchNodeScoring | patched | Score events without metagraph |
| ExportPredictionsPg | new | SQLite → PostgreSQL |
| ExportScoresPg | new | SQLite → PostgreSQL |
| ExportAgentRunsPg | new | SQLite → PostgreSQL |
| ExportAgentRunLogsPg | new | SQLite → PostgreSQL |
| DbCleaner | submodule | Clean old SQLite rows |
| DbVacuum | submodule | SQLite VACUUM |
