-- PhiTest migration 0002: structured telemetry transport
-- Adds telemetry_samples table for allowlisted operational measurements.

CREATE TABLE IF NOT EXISTS telemetry_samples (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES runs(id),
    observation_id  TEXT REFERENCES observations(id),
    sequence_no     INTEGER NOT NULL,
    phase           TEXT NOT NULL DEFAULT 'stimulus',
    schema_version  TEXT NOT NULL DEFAULT '1.0',
    values_json     TEXT NOT NULL DEFAULT '{}',
    allowed_keys    TEXT NOT NULL DEFAULT '[]',
    sampled_at      TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS telemetry_samples_no_update
BEFORE UPDATE ON telemetry_samples BEGIN
    SELECT RAISE(ABORT, 'telemetry_samples are append-only');
END;
CREATE TRIGGER IF NOT EXISTS telemetry_samples_no_delete
BEFORE DELETE ON telemetry_samples BEGIN
    SELECT RAISE(ABORT, 'telemetry_samples are append-only');
END;

INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (2, datetime('now'));
