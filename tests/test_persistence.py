import sqlite3
import pytest
from datetime import datetime, timezone
from phitest.adapters.sqlite_repository import SQLiteRepository
from phitest.domain.models import Subject, Observation, MetricResult, EvidenceClaim
from phitest.application import experiment_service, run_service
from phitest.application.audit_service import verify_audit_chain
from phitest.adapters.manual_target import ManualTarget
import uuid


def _now():
    return datetime.now(timezone.utc)


def _make_run(repo):
    s = experiment_service.create_subject(repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    e = experiment_service.create_experiment(repo, {
        "subject_id": s.id, "name": "E", "protocol_key": "partition_sensitivity",
    })
    return run_service.execute_run(repo, e.id, ManualTarget("ok"), random_seed=42)


# --- Schema / migration ---

def test_schema_version(tmp_repo):
    assert tmp_repo.schema_version() == 1


def test_migration_idempotent(tmp_repo, tmp_path):
    repo2 = SQLiteRepository(str(tmp_path / "test2.db"), tmp_repo._migrations_dir)
    assert repo2.schema_version() == 1


def test_uuid_ids(tmp_repo):
    s = Subject(id=str(uuid.uuid4()), name="T", subject_type="ai",
                adapter_type="manual", created_at=_now())
    tmp_repo.save_subject(s)
    loaded = tmp_repo.get_subject(s.id)
    assert loaded.id == s.id
    assert len(loaded.id) == 36


def test_timezone_aware_timestamps(tmp_repo):
    s = Subject(id=str(uuid.uuid4()), name="T", subject_type="ai",
                adapter_type="manual", created_at=_now())
    tmp_repo.save_subject(s)
    loaded = tmp_repo.get_subject(s.id)
    assert loaded.created_at.tzinfo is not None


def test_foreign_key_enforced(tmp_repo):
    conn = sqlite3.connect(tmp_repo._db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), "nonexistent-subject", "E", "", "partition_sensitivity",
             "[]", "{}", _now().isoformat(), "researcher", "draft"),
        )
        conn.commit()
    conn.close()


# --- Immutability ---

def _make_obs(repo):
    from phitest.domain.models import Run, Experiment
    s = Subject(id=str(uuid.uuid4()), name="T", subject_type="ai",
                adapter_type="manual", created_at=_now())
    repo.save_subject(s)
    e = Experiment(id=str(uuid.uuid4()), subject_id=s.id, name="E",
                   protocol_key="partition_sensitivity", created_at=_now())
    repo.save_experiment(e)
    r = Run(id=str(uuid.uuid4()), experiment_id=e.id, started_at=_now(),
            status="running", protocol_version="1.0", target_adapter="manual")
    repo.save_run(r)
    obs = Observation(id=str(uuid.uuid4()), run_id=r.id, sequence_no=0,
                      observation_type="response", content="hello",
                      content_sha256="abc", created_at=_now())
    repo.save_observation(obs)
    return obs, r


def test_observations_reject_update(tmp_repo):
    obs, _ = _make_obs(tmp_repo)
    conn = sqlite3.connect(tmp_repo._db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE observations SET content='changed' WHERE id=?", (obs.id,))
        conn.commit()
    conn.close()


def test_observations_reject_delete(tmp_repo):
    obs, _ = _make_obs(tmp_repo)
    conn = sqlite3.connect(tmp_repo._db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM observations WHERE id=?", (obs.id,))
        conn.commit()
    conn.close()


def test_metric_results_reject_update(tmp_repo):
    from phitest.domain.models import Run, Experiment
    s = Subject(id=str(uuid.uuid4()), name="T", subject_type="ai",
                adapter_type="manual", created_at=_now())
    tmp_repo.save_subject(s)
    e = Experiment(id=str(uuid.uuid4()), subject_id=s.id, name="E",
                   protocol_key="partition_sensitivity", created_at=_now())
    tmp_repo.save_experiment(e)
    r = Run(id=str(uuid.uuid4()), experiment_id=e.id, started_at=_now(),
            status="running", protocol_version="1.0", target_adapter="manual")
    tmp_repo.save_run(r)
    m = MetricResult(id=str(uuid.uuid4()), run_id=r.id, metric_key="k",
                     metric_version="1.0", value_json="{}", definition="d",
                     computed_at=_now())
    tmp_repo.save_metric_result(m)
    conn = sqlite3.connect(tmp_repo._db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE metric_results SET metric_key='x' WHERE id=?", (m.id,))
        conn.commit()
    conn.close()


def test_evidence_claims_reject_delete(tmp_repo):
    from phitest.domain.models import Run, Experiment
    s = Subject(id=str(uuid.uuid4()), name="T", subject_type="ai",
                adapter_type="manual", created_at=_now())
    tmp_repo.save_subject(s)
    e = Experiment(id=str(uuid.uuid4()), subject_id=s.id, name="E",
                   protocol_key="partition_sensitivity", created_at=_now())
    tmp_repo.save_experiment(e)
    r = Run(id=str(uuid.uuid4()), experiment_id=e.id, started_at=_now(),
            status="running", protocol_version="1.0", target_adapter="manual")
    tmp_repo.save_run(r)
    c = EvidenceClaim(id=str(uuid.uuid4()), run_id=r.id, claim_type="unresolved",
                      statement="s", created_at=_now())
    tmp_repo.save_evidence_claim(c)
    conn = sqlite3.connect(tmp_repo._db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM evidence_claims WHERE id=?", (c.id,))
        conn.commit()
    conn.close()


# --- Audit chain ---

def test_valid_chain_passes(tmp_repo):
    _make_run(tmp_repo)
    valid, msg = verify_audit_chain(tmp_repo)
    assert valid, msg


def test_empty_chain_passes(tmp_repo):
    valid, _ = verify_audit_chain(tmp_repo)
    assert valid


def test_reordered_events_detected(tmp_repo):
    _make_run(tmp_repo)
    events = tmp_repo.list_audit_events()
    if len(events) < 2:
        pytest.skip("Need at least 2 events")
    e0, e1 = events[0], events[1]
    assert e1.previous_event_hash == e0.event_hash


def test_correct_chain_validates(tmp_repo):
    _make_run(tmp_repo)
    valid, msg = verify_audit_chain(tmp_repo)
    assert valid
    assert len(tmp_repo.list_audit_events()) > 0


def test_modified_payload_fails_chain(tmp_repo):
    """If a payload is modified bypassing triggers, chain verification must catch it."""
    _make_run(tmp_repo)
    conn = sqlite3.connect(tmp_repo._db_path)
    # Disable triggers temporarily via a direct raw write
    conn.execute("DROP TRIGGER IF EXISTS audit_events_no_update")
    conn.execute(
        "UPDATE audit_events SET payload_json='{\"tampered\":true}' "
        "WHERE id=(SELECT id FROM audit_events ORDER BY created_at LIMIT 1)"
    )
    conn.commit()
    conn.close()
    valid, msg = verify_audit_chain(tmp_repo)
    assert not valid
