-- ARES — Database Schema
-- Run once: psql -U postgres -d ares -f schema.sql
-- 4 tables only: incidents, incident_updates, teams, tasks

CREATE TABLE IF NOT EXISTS incidents (
    id          SERIAL PRIMARY KEY,
    description TEXT         NOT NULL,
    category    VARCHAR(50)  NOT NULL,
    severity    VARCHAR(20)  NOT NULL,
    location    TEXT,
    risks       TEXT,
    status      VARCHAR(20)  NOT NULL DEFAULT 'active',
    feed_id     VARCHAR(50),
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    closed_at   TIMESTAMP
);

CREATE TABLE IF NOT EXISTS incident_updates (
    id            SERIAL PRIMARY KEY,
    incident_id   INT          NOT NULL REFERENCES incidents(id),
    update_text   TEXT         NOT NULL,
    event_type    VARCHAR(20)  NOT NULL DEFAULT 'update',
    update_number INT          NOT NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS teams (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    type         VARCHAR(50)  NOT NULL,
    location     TEXT,
    capabilities TEXT,
    personnel    INT          NOT NULL DEFAULT 1,
    status       VARCHAR(20)  NOT NULL DEFAULT 'available'
);

CREATE TABLE IF NOT EXISTS tasks (
    id           SERIAL PRIMARY KEY,
    incident_id  INT          NOT NULL REFERENCES incidents(id),
    task         TEXT         NOT NULL,
    priority     VARCHAR(20)  NOT NULL,
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending',
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    team_id      INT          REFERENCES teams(id),
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);
