#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'readonly_user') THEN
            CREATE USER readonly_user WITH PASSWORD '$READONLY_USER_PASSWORD';
        END IF;
    END
    \$$;

    GRANT USAGE ON SCHEMA public TO readonly_user;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

    ALTER ROLE readonly_user SET statement_timeout = '30s';
    ALTER ROLE readonly_user SET idle_in_transaction_session_timeout = '10s';
    ALTER ROLE readonly_user SET idle_session_timeout = '15min';
    ALTER ROLE readonly_user SET work_mem = '16MB';
EOSQL

echo "Read-only user 'readonly_user' configured."
