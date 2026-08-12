-- PhiTest V1 initial schema
-- Apply once; future changes use numbered migration files.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subjects (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    subject_type        TEXT NOT NULL,
    adapter_type        TEXT NOT NULL,
    adapter_config_json TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    archived_at         TEXT
);

CREATE TABLE IF NOT EXISTS experiments (
    id                  TEXT PRIMARY KEY,
    subject_id          TEXT NOT NULL REFERENCES subjects(id),
    name                TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    protocol_key        TEXT NOT NULL,
    theory_keys_json    TEXT NOT NULL DEFAULT '[]',
    configuration_json  TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    created_by          TEXT NOT NULL DEFAULT 'researcher',
    status              TEXT NOT NULL DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS runs (
    id               TEXT PRIMARY KEY,
    experiment_id    TEXT NOT NULL REFERENCES experiments(id),
    started_at       TEXT NOT NULL,
    completed_at     TEXT,
    status           TEXT NOT NULL DEFAULT 'pending',
    random_seed      INTEGER,
    protocol_version TEXT NOT NULL,
    target_adapter   TEXT NOT NULL,
    failure_reason   TEXT
);

CREATE TABLE IF NOT EXISTS stimuli (
    id           TEXT PRIMARY KEY,
    run_id       TEXT NOT NULL REFERENCES runs(id),
    sequence_no  INTEGER NOT NULL,
    stimulus_type TEXT NOT NULL,
    content      TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    id               TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL REFERENCES runs(id),
    stimulus_id      TEXT REFERENCES stimuli(id),
    sequence_no      INTEGER NOT NULL,
    observation_type TEXT NOT NULL,
    content          TEXT NOT NULL,
    content_sha256   TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interventions (
    id                 TEXT PRIMARY KEY,
    run_id             TEXT NOT NULL REFERENCES runs(id),
    sequence_no        INTEGER NOT NULL,
    intervention_type  TEXT NOT NULL,
    configuration_json TEXT NOT NULL DEFAULT '{}',
    rationale          TEXT NOT NULL DEFAULT '',
    created_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metric_results (
    id             TEXT PRIMARY KEY,
    run_id         TEXT NOT NULL REFERENCES runs(id),
    metric_key     TEXT NOT NULL,
    metric_version TEXT NOT NULL,
    value_json     TEXT NOT NULL,
    definition     TEXT NOT NULL,
    computed_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_claims (
    id               TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL REFERENCES runs(id),
    claim_type       TEXT NOT NULL,
    theory_key       TEXT,
    statement        TEXT NOT NULL,
    evidence_json    TEXT NOT NULL DEFAULT '{}',
    confidence_label TEXT NOT NULL DEFAULT 'not_applicable',
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id                  TEXT PRIMARY KEY,
    event_type          TEXT NOT NULL,
    entity_type         TEXT NOT NULL,
    entity_id           TEXT NOT NULL,
    payload_json        TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    previous_event_hash TEXT,
    event_hash          TEXT NOT NULL
);

-- Immutability triggers

CREATE TRIGGER IF NOT EXISTS observations_no_update
BEFORE UPDATE ON observations BEGIN
    SELECT RAISE(ABORT, 'observations are append-only');
END;
CREATE TRIGGER IF NOT EXISTS observations_no_delete
BEFORE DELETE ON observations BEGIN
    SELECT RAISE(ABORT, 'observations are append-only');
END;

CREATE TRIGGER IF NOT EXISTS interventions_no_update
BEFORE UPDATE ON interventions BEGIN
    SELECT RAISE(ABORT, 'interventions are append-only');
END;
CREATE TRIGGER IF NOT EXISTS interventions_no_delete
BEFORE DELETE ON interventions BEGIN
    SELECT RAISE(ABORT, 'interventions are append-only');
END;

CREATE TRIGGER IF NOT EXISTS metric_results_no_update
BEFORE UPDATE ON metric_results BEGIN
    SELECT RAISE(ABORT, 'metric_results are append-only');
END;
CREATE TRIGGER IF NOT EXISTS metric_results_no_delete
BEFORE DELETE ON metric_results BEGIN
    SELECT RAISE(ABORT, 'metric_results are append-only');
END;

CREATE TRIGGER IF NOT EXISTS evidence_claims_no_update
BEFORE UPDATE ON evidence_claims BEGIN
    SELECT RAISE(ABORT, 'evidence_claims are append-only');
END;
CREATE TRIGGER IF NOT EXISTS evidence_claims_no_delete
BEFORE DELETE ON evidence_claims BEGIN
    SELECT RAISE(ABORT, 'evidence_claims are append-only');
END;

CREATE TRIGGER IF NOT EXISTS audit_events_no_update
BEFORE UPDATE ON audit_events BEGIN
    SELECT RAISE(ABORT, 'audit_events are append-only');
END;
CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
BEFORE DELETE ON audit_events BEGIN
    SELECT RAISE(ABORT, 'audit_events are append-only');
END;

INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (1, datetime('now'));
