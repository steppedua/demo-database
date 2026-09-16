--liquibase formatted sql

--changeset edstepa:003-doctors
CREATE TABLE doctors (
    id      int PRIMARY KEY,
    name    text NOT NULL,
    on_call boolean NOT NULL
);

INSERT INTO doctors (id, name, on_call) VALUES
    (1, 'Alice', true),
    (2, 'Bob', true);
--rollback DROP TABLE doctors;
