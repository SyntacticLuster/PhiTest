import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from phitest.domain.models import (
    Subject, Experiment, Run, Stimulus, Observation,
    Intervention, MetricResult, EvidenceClaim, AuditEvent,
)


def _parse_dt(v: str | None) -> datetime | None:
    if v is None:
        return None
    return datetime.fromisoformat(v)


def _fmt_dt(v: datetime | None) -> str | None:
    if v is None:
        return None
    return v.isoformat()


class SQLiteRepository:
    def __init__(self, db_path: str, migrations_dir: Path):
        self._db_path = db_path
        self._migrations_dir = migrations_dir
        self._apply_migrations()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _apply_migrations(self) -> None:
        conn = self._connect()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        conn.commit()
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_version")}
        migration_files = sorted(self._migrations_dir.glob("*.sql"))
        for mf in migration_files:
            num = int(mf.stem.split("_")[0])
            if num not in applied:
                sql = mf.read_text(encoding="utf-8")
                conn.executescript(sql)
                conn.commit()
        conn.close()

    def schema_version(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(version) FROM schema_version"
            ).fetchone()
            return row[0] or 0

    # --- Subjects ---
    def save_subject(self, s: Subject) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO subjects VALUES (?,?,?,?,?,?,?,?)",
                (s.id, s.name, s.description, s.subject_type, s.adapter_type,
                 s.adapter_config_json, _fmt_dt(s.created_at), _fmt_dt(s.archived_at)),
            )

    def get_subject(self, subject_id: str) -> Subject | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM subjects WHERE id=?", (subject_id,)
            ).fetchone()
        if row is None:
            return None
        return Subject(
            id=row["id"], name=row["name"], description=row["description"],
            subject_type=row["subject_type"], adapter_type=row["adapter_type"],
            adapter_config_json=row["adapter_config_json"],
            created_at=_parse_dt(row["created_at"]),
            archived_at=_parse_dt(row["archived_at"]),
        )

    def list_subjects(self) -> list[Subject]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM subjects ORDER BY created_at DESC").fetchall()
        return [self.get_subject(r["id"]) for r in rows]

    # --- Experiments ---
    def save_experiment(self, e: Experiment) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?)",
                (e.id, e.subject_id, e.name, e.description, e.protocol_key,
                 e.theory_keys_json, e.configuration_json,
                 _fmt_dt(e.created_at), e.created_by, e.status),
            )

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM experiments WHERE id=?", (experiment_id,)
            ).fetchone()
        if row is None:
            return None
        return Experiment(
            id=row["id"], subject_id=row["subject_id"], name=row["name"],
            description=row["description"], protocol_key=row["protocol_key"],
            theory_keys_json=row["theory_keys_json"],
            configuration_json=row["configuration_json"],
            created_at=_parse_dt(row["created_at"]),
            created_by=row["created_by"], status=row["status"],
        )

    def list_experiments(self, subject_id: str | None = None) -> list[Experiment]:
        with self._connect() as conn:
            if subject_id:
                rows = conn.execute(
                    "SELECT id FROM experiments WHERE subject_id=? ORDER BY created_at DESC",
                    (subject_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id FROM experiments ORDER BY created_at DESC"
                ).fetchall()
        return [self.get_experiment(r["id"]) for r in rows]

    def update_experiment_status(self, experiment_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE experiments SET status=? WHERE id=?", (status, experiment_id)
            )

    # --- Runs ---
    def save_run(self, r: Run) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
                (r.id, r.experiment_id, _fmt_dt(r.started_at), _fmt_dt(r.completed_at),
                 r.status, r.random_seed, r.protocol_version, r.target_adapter,
                 r.failure_reason),
            )

    def get_run(self, run_id: str) -> Run | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            return None
        return Run(
            id=row["id"], experiment_id=row["experiment_id"],
            started_at=_parse_dt(row["started_at"]),
            completed_at=_parse_dt(row["completed_at"]),
            status=row["status"], random_seed=row["random_seed"],
            protocol_version=row["protocol_version"],
            target_adapter=row["target_adapter"],
            failure_reason=row["failure_reason"],
        )

    def list_runs(self, experiment_id: str | None = None) -> list[Run]:
        with self._connect() as conn:
            if experiment_id:
                rows = conn.execute(
                    "SELECT id FROM runs WHERE experiment_id=? ORDER BY started_at DESC",
                    (experiment_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id FROM runs ORDER BY started_at DESC"
                ).fetchall()
        return [self.get_run(r["id"]) for r in rows]

    def update_run(self, r: Run) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE runs SET completed_at=?, status=?, failure_reason=? WHERE id=?",
                (_fmt_dt(r.completed_at), r.status, r.failure_reason, r.id),
            )

    # --- Stimuli ---
    def save_stimulus(self, s: Stimulus) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO stimuli VALUES (?,?,?,?,?,?,?)",
                (s.id, s.run_id, s.sequence_no, s.stimulus_type,
                 s.content, s.content_sha256, _fmt_dt(s.created_at)),
            )

    def list_stimuli(self, run_id: str) -> list[Stimulus]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM stimuli WHERE run_id=? ORDER BY sequence_no", (run_id,)
            ).fetchall()
        return [
            Stimulus(id=r["id"], run_id=r["run_id"], sequence_no=r["sequence_no"],
                     stimulus_type=r["stimulus_type"], content=r["content"],
                     content_sha256=r["content_sha256"], created_at=_parse_dt(r["created_at"]))
            for r in rows
        ]

    # --- Observations ---
    def save_observation(self, o: Observation) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO observations VALUES (?,?,?,?,?,?,?,?)",
                (o.id, o.run_id, o.stimulus_id, o.sequence_no, o.observation_type,
                 o.content, o.content_sha256, _fmt_dt(o.created_at)),
            )

    def list_observations(self, run_id: str) -> list[Observation]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM observations WHERE run_id=? ORDER BY sequence_no", (run_id,)
            ).fetchall()
        return [
            Observation(id=r["id"], run_id=r["run_id"], stimulus_id=r["stimulus_id"],
                        sequence_no=r["sequence_no"], observation_type=r["observation_type"],
                        content=r["content"], content_sha256=r["content_sha256"],
                        created_at=_parse_dt(r["created_at"]))
            for r in rows
        ]

    # --- Interventions ---
    def save_intervention(self, i: Intervention) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO interventions VALUES (?,?,?,?,?,?,?)",
                (i.id, i.run_id, i.sequence_no, i.intervention_type,
                 i.configuration_json, i.rationale, _fmt_dt(i.created_at)),
            )

    def list_interventions(self, run_id: str) -> list[Intervention]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM interventions WHERE run_id=? ORDER BY sequence_no", (run_id,)
            ).fetchall()
        return [
            Intervention(id=r["id"], run_id=r["run_id"], sequence_no=r["sequence_no"],
                         intervention_type=r["intervention_type"],
                         configuration_json=r["configuration_json"],
                         rationale=r["rationale"], created_at=_parse_dt(r["created_at"]))
            for r in rows
        ]

    # --- Metrics ---
    def save_metric_result(self, m: MetricResult) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO metric_results VALUES (?,?,?,?,?,?,?)",
                (m.id, m.run_id, m.metric_key, m.metric_version,
                 m.value_json, m.definition, _fmt_dt(m.computed_at)),
            )

    def list_metric_results(self, run_id: str) -> list[MetricResult]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM metric_results WHERE run_id=?", (run_id,)
            ).fetchall()
        return [
            MetricResult(id=r["id"], run_id=r["run_id"], metric_key=r["metric_key"],
                         metric_version=r["metric_version"], value_json=r["value_json"],
                         definition=r["definition"], computed_at=_parse_dt(r["computed_at"]))
            for r in rows
        ]

    # --- Claims ---
    def save_evidence_claim(self, c: EvidenceClaim) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO evidence_claims VALUES (?,?,?,?,?,?,?,?)",
                (c.id, c.run_id, c.claim_type, c.theory_key, c.statement,
                 c.evidence_json, c.confidence_label, _fmt_dt(c.created_at)),
            )

    def list_evidence_claims(self, run_id: str) -> list[EvidenceClaim]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM evidence_claims WHERE run_id=? ORDER BY created_at", (run_id,)
            ).fetchall()
        return [
            EvidenceClaim(id=r["id"], run_id=r["run_id"], claim_type=r["claim_type"],
                          theory_key=r["theory_key"], statement=r["statement"],
                          evidence_json=r["evidence_json"],
                          confidence_label=r["confidence_label"],
                          created_at=_parse_dt(r["created_at"]))
            for r in rows
        ]

    # --- Audit ---
    def append_audit_event(self, event: AuditEvent) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_events VALUES (?,?,?,?,?,?,?,?)",
                (event.id, event.event_type, event.entity_type, event.entity_id,
                 event.payload_json, _fmt_dt(event.created_at),
                 event.previous_event_hash, event.event_hash),
            )

    def list_audit_events(self) -> list[AuditEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_events ORDER BY created_at, id"
            ).fetchall()
        return [
            AuditEvent(id=r["id"], event_type=r["event_type"],
                       entity_type=r["entity_type"], entity_id=r["entity_id"],
                       payload_json=r["payload_json"],
                       created_at=_parse_dt(r["created_at"]),
                       previous_event_hash=r["previous_event_hash"],
                       event_hash=r["event_hash"])
            for r in rows
        ]

    def get_last_audit_event(self) -> AuditEvent | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM audit_events ORDER BY created_at DESC, id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return AuditEvent(
            id=row["id"], event_type=row["event_type"],
            entity_type=row["entity_type"], entity_id=row["entity_id"],
            payload_json=row["payload_json"],
            created_at=_parse_dt(row["created_at"]),
            previous_event_hash=row["previous_event_hash"],
            event_hash=row["event_hash"],
        )
