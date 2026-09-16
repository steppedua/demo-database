--liquibase formatted sql

--changeset edstepa:001-extensions
CREATE EXTENSION IF NOT EXISTS pageinspect;
CREATE EXTENSION IF NOT EXISTS pgstattuple;
CREATE EXTENSION IF NOT EXISTS pg_visibility;
--rollback DROP EXTENSION IF EXISTS pg_visibility;
--rollback DROP EXTENSION IF EXISTS pgstattuple;
--rollback DROP EXTENSION IF EXISTS pageinspect;
