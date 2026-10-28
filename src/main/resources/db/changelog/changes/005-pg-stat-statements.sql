--liquibase formatted sql

--changeset edstepa:005-pg-stat-statements
-- нужен shared_preload_libraries=pg_stat_statements (см. docker-compose.yml); читают PgHero и Grafana
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
--rollback DROP EXTENSION IF EXISTS pg_stat_statements;
