FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Needed for Postgres (asyncpg) and git (submodule)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml requirements.txt ./
RUN uv pip install --system -r requirements.txt

# Copy entrypoint script
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# Copy submodule and application code
COPY numinous ./numinous
COPY crunch_node ./crunch_node

# Entrypoint conditionally enables NewRelic if license key is provided
ENTRYPOINT ["./entrypoint.sh"]

# Default command — overridden in docker compose for each worker
CMD ["python", "-m", "crunch_node.main"]
