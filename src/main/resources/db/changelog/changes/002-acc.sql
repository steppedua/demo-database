--liquibase formatted sql

--changeset edstepa:002-acc
CREATE TABLE acc (
    id      int PRIMARY KEY,
    balance int NOT NULL
);

INSERT INTO acc (id, balance) VALUES (1, 100);
--rollback DROP TABLE acc;
