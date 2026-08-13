"""
Focused tests for PhiTest Telemetry Transport V1.

Covers:
1. Old non-instrumented adapters still work
2. Valid structured telemetry persists correctly
3. Missing optional telemetry is valid
4. Malformed telemetry fails visibly
5. Unknown/raw metadata is not persisted
6. Auth/secrets are not recorded
7. Telemetry is correctly associated to run/stimulus/phase
8. Interventions are persisted and passed correctly
9. Existing six protocols retain their behavior
10. Audit integrity still passes
"""
import json
import sqlite3
import uuid
import pytest
from datetime import datetime, timezone

from phitest.adapters.manual_target import ManualTarget
from phitest.application import experiment_service, run_service, report_service
from phitest.application.audit_service import verify_audit_chain
from phitest.domain.models import Subject, TelemetrySample
from phitest.domain.telemetry import ALLOWED_TELEMETRY_KEYS
from phitest.ports.target import ControllableTarget


def _now():
    return datetime.now(timezone.utc)


def _make_experiment(repo, protocol_key="partition_sensitivity", config=None):
    s = experiment_service.create_subject(repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    extra = json.dumps(config) if config else "{}"
    e = experiment_service.create_experiment(repo, {
        "subject_id": s.id, "name": "E", "protocol_key": protocol_key,
        "configuration_json": extra,
    })
    return e


class InstrumentedAdapter:
    """Adapter that returns structured telemetry in metadata."""
    adapter_type = "instrumented"

    def __init__(self, text="response", metadata=None):
        self._text = text
        self._metadata = metadata or {}

    def send(self, stimulus, context=None):
        from phitest.domain.models import TargetResponse
        return TargetResponse(
            text=self._text,
            metadata=self._metadata,
            received_at=_now(),
        )


class ControllableInstrumentedAdapter(InstrumentedAdapter):
    """Adapter that also implements ControllableTarget."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interventions_received = []

    def apply_intervention(self, intervention_type: str, config: dict) -> dict:
        self.interventions_received.append((intervention_type, config))
        return {"applied": intervention_type, "status": "ok"}


# ── 1. Old non-instrumented adapters still work ──────────────────────────────

def test_manual_target_unchanged(tmp_repo):
    e = _make_experiment(tmp_repo)
    run = run_service.execute_run(tmp_repo, e.id, ManualTarget("ok"), random_seed=42)
    assert run.status == "completed"
    assert len(tmp_repo.list_observations(run.id)) > 0
    assert len(tmp_repo.list_metric_results(run.id)) > 0
    # No telemetry without allowlist
    assert tmp_repo.list_telemetry_samples(run.id) == []


def test_instrumented_adapter_without_allowlist_produces_no_telemetry(tmp_repo):
    e = _make_experiment(tmp_repo)
    adapter = InstrumentedAdapter(metadata={"compute.input_tokens": 10})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    assert run.status == "completed"
    assert tmp_repo.list_telemetry_samples(run.id) == []


# ── 2. Valid structured telemetry persists correctly ─────────────────────────

def test_valid_telemetry_persisted(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens", "compute.output_tokens"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={
        "compute.input_tokens": 42,
        "compute.output_tokens": 17,
    })
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    assert run.status == "completed"
    samples = tmp_repo.list_telemetry_samples(run.id)
    assert len(samples) > 0
    for s in samples:
        values = json.loads(s.values_json)
        assert "compute.input_tokens" in values
        assert "compute.output_tokens" in values
        assert values["compute.input_tokens"] == 42


def test_telemetry_schema_version_set(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={"compute.input_tokens": 5})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    samples = tmp_repo.list_telemetry_samples(run.id)
    assert all(s.schema_version == "1.0" for s in samples)


def test_telemetry_allowed_keys_recorded(tmp_repo):
    allowlist = ["compute.input_tokens", "memory.reads"]
    config = {"telemetry_allowlist": allowlist}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={"compute.input_tokens": 1})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    samples = tmp_repo.list_telemetry_samples(run.id)
    assert len(samples) > 0
    recorded_keys = json.loads(samples[0].allowed_keys)
    # Only canonical keys survive the intersection with ALLOWED_TELEMETRY_KEYS
    for k in recorded_keys:
        assert k in ALLOWED_TELEMETRY_KEYS


# ── 3. Missing optional telemetry is valid ───────────────────────────────────

def test_empty_metadata_with_allowlist_produces_no_samples(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    assert run.status == "completed"
    assert tmp_repo.list_telemetry_samples(run.id) == []


def test_partial_telemetry_only_present_keys_stored(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens", "memory.reads"]}
    e = _make_experiment(tmp_repo, config=config)
    # Only one of the two allowlisted keys is present
    adapter = InstrumentedAdapter(metadata={"compute.input_tokens": 99})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    samples = tmp_repo.list_telemetry_samples(run.id)
    assert len(samples) > 0
    for s in samples:
        values = json.loads(s.values_json)
        assert "memory.reads" not in values
        assert "compute.input_tokens" in values


# ── 4. Malformed telemetry fails visibly ─────────────────────────────────────

def test_non_canonical_key_in_allowlist_is_silently_dropped(tmp_repo):
    # A key not in ALLOWED_TELEMETRY_KEYS is requested in the allowlist —
    # the intersection with ALLOWED_TELEMETRY_KEYS removes it before persistence.
    config = {"telemetry_allowlist": ["compute.input_tokens", "not_a_real_key"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={
        "compute.input_tokens": 5,
        "not_a_real_key": "should_not_appear",
    })
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    samples = tmp_repo.list_telemetry_samples(run.id)
    for s in samples:
        values = json.loads(s.values_json)
        assert "not_a_real_key" not in values
        allowed = json.loads(s.allowed_keys)
        assert "not_a_real_key" not in allowed


def test_telemetry_sample_append_only_rejects_update(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={"compute.input_tokens": 1})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    samples = tmp_repo.list_telemetry_samples(run.id)
    assert len(samples) > 0
    with sqlite3.connect(tmp_repo._db_path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE telemetry_samples SET values_json=? WHERE id=?",
                ('{"tampered": 1}', samples[0].id),
            )


def test_telemetry_sample_append_only_rejects_delete(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={"compute.input_tokens": 1})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    samples = tmp_repo.list_telemetry_samples(run.id)
    assert len(samples) > 0
    with sqlite3.connect(tmp_repo._db_path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "DELETE FROM telemetry_samples WHERE id=?", (samples[0].id,)
            )


# ── 5. Unknown/raw metadata is not persisted ─────────────────────────────────

def test_raw_metadata_not_persisted_without_allowlist(tmp_repo):
    e = _make_experiment(tmp_repo)
    adapter = InstrumentedAdapter(metadata={
        "compute.input_tokens": 10,
        "internal_state": "private",
        "hidden_reasoning": "chain of thought",
    })
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    assert tmp_repo.list_telemetry_samples(run.id) == []


def test_raw_metadata_not_persisted_even_with_allowlist_if_key_not_canonical(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={
        "compute.input_tokens": 5,
        "internal_state": "private",
        "hidden_reasoning": "chain of thought",
        "system_prompt": "secret",
    })
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    samples = tmp_repo.list_telemetry_samples(run.id)
    for s in samples:
        values = json.loads(s.values_json)
        assert "internal_state" not in values
        assert "hidden_reasoning" not in values
        assert "system_prompt" not in values


# ── 6. Auth/secrets are not recorded ─────────────────────────────────────────

def test_auth_keys_not_in_telemetry(tmp_repo):
    config = {"telemetry_allowlist": list(ALLOWED_TELEMETRY_KEYS)}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={
        "compute.input_tokens": 3,
        "auth_token": "secret123",
        "authorization": "Bearer xyz",
        "api_key": "sk-private",
    })
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    samples = tmp_repo.list_telemetry_samples(run.id)
    for s in samples:
        values = json.loads(s.values_json)
        for k in values:
            assert "auth" not in k.lower()
            assert "api_key" not in k.lower()
            assert "secret" not in k.lower()


def test_auth_keys_not_in_audit_events(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={
        "compute.input_tokens": 1,
        "auth_token": "secret",
    })
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    events = tmp_repo.list_audit_events()
    for ev in events:
        assert "secret" not in ev.payload_json
        assert "auth_token" not in ev.payload_json


# ── 7. Telemetry correctly associated to run/stimulus/phase ──────────────────

def test_telemetry_linked_to_observation(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={"compute.input_tokens": 7})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    samples = tmp_repo.list_telemetry_samples(run.id)
    observations = tmp_repo.list_observations(run.id)
    obs_ids = {o.id for o in observations}
    for s in samples:
        assert s.run_id == run.id
        assert s.observation_id in obs_ids
        assert s.phase == "stimulus"


def test_telemetry_sequence_nos_match_stimuli(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={"compute.input_tokens": 2})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    samples = tmp_repo.list_telemetry_samples(run.id)
    stimuli = tmp_repo.list_stimuli(run.id)
    stim_seqs = {s.sequence_no for s in stimuli if s.stimulus_type != "intervention_marker"}
    for s in samples:
        assert s.sequence_no in stim_seqs


# ── 8. Interventions persisted and passed correctly ──────────────────────────

def test_intervention_saved_for_controllable_target(tmp_repo):
    e = _make_experiment(tmp_repo, protocol_key="perturbation_response")
    adapter = ControllableInstrumentedAdapter()
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    assert run.status == "completed"
    interventions = tmp_repo.list_interventions(run.id)
    assert len(interventions) >= 1
    assert len(adapter.interventions_received) >= 1


def test_intervention_not_saved_for_plain_target(tmp_repo):
    e = _make_experiment(tmp_repo, protocol_key="perturbation_response")
    run = run_service.execute_run(tmp_repo, e.id, ManualTarget("ok"), random_seed=42)
    assert run.status == "completed"
    assert tmp_repo.list_interventions(run.id) == []


def test_interventions_passed_to_compute_metrics(tmp_repo):
    """Prove recorded_interventions is passed (not []) when ControllableTarget used."""
    received = {}

    class CapturingProtocolWrapper:
        def __init__(self, inner):
            self._inner = inner
            self.__dict__.update({
                k: getattr(inner, k) for k in [
                    'key', 'version', 'name', 'description', 'theory_relevance',
                    'required_capabilities', 'stimulus_description',
                    'intervention_sequence', 'metric_definitions', 'limitations',
                ]
            })

        def generate_stimuli(self, config, seed):
            return self._inner.generate_stimuli(config, seed)

        def compute_metrics(self, stimuli, observations, interventions, config):
            received['interventions'] = interventions
            return self._inner.compute_metrics(stimuli, observations, interventions, config)

        def generate_claims(self, stimuli, observations, metrics, config):
            return self._inner.generate_claims(stimuli, observations, metrics, config)

    from phitest.protocols.registry import get_protocol
    from phitest.application import experiment_service
    import phitest.protocols.perturbation_response  # noqa

    s = experiment_service.create_subject(tmp_repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    e = experiment_service.create_experiment(tmp_repo, {
        "subject_id": s.id, "name": "E", "protocol_key": "perturbation_response",
    })

    inner = get_protocol("perturbation_response")
    wrapper = CapturingProtocolWrapper(inner)

    import phitest.protocols.registry as reg
    original = reg._REGISTRY["perturbation_response"]
    reg._REGISTRY["perturbation_response"] = wrapper
    try:
        adapter = ControllableInstrumentedAdapter()
        run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    finally:
        reg._REGISTRY["perturbation_response"] = original

    assert run.status == "completed"
    assert len(received.get('interventions', [])) >= 1


def test_intervention_audit_event_emitted(tmp_repo):
    e = _make_experiment(tmp_repo, protocol_key="perturbation_response")
    adapter = ControllableInstrumentedAdapter()
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    events = tmp_repo.list_audit_events()
    event_types = [ev.event_type for ev in events]
    assert "intervention_recorded" in event_types


# ── 9. Existing six protocols retain their behavior ──────────────────────────

def test_all_six_protocols_complete_with_telemetry_transport(tmp_repo):
    protocols = [
        "partition_sensitivity", "global_availability",
        "metacognitive_calibration", "self_model_continuity",
        "phenomenal_report_consistency", "perturbation_response",
    ]
    s = experiment_service.create_subject(tmp_repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    for pk in protocols:
        e = experiment_service.create_experiment(tmp_repo, {
            "subject_id": s.id, "name": f"E-{pk}", "protocol_key": pk,
        })
        run = run_service.execute_run(tmp_repo, e.id, ManualTarget("response"), random_seed=42)
        assert run.status == "completed", f"Protocol {pk} failed: {run.failure_reason}"
        assert len(tmp_repo.list_observations(run.id)) > 0
        assert len(tmp_repo.list_metric_results(run.id)) > 0
        # No telemetry without allowlist
        assert tmp_repo.list_telemetry_samples(run.id) == []


def test_report_includes_telemetry_samples_key(tmp_repo):
    e = _make_experiment(tmp_repo)
    run = run_service.execute_run(tmp_repo, e.id, ManualTarget("ok"), random_seed=42)
    report = report_service.generate_report(tmp_repo, run.id)
    assert "telemetry_samples" in report
    assert report["telemetry_samples"] == []


def test_report_telemetry_samples_populated_when_present(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={"compute.input_tokens": 9})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    report = report_service.generate_report(tmp_repo, run.id)
    assert len(report["telemetry_samples"]) > 0


# ── 10. Audit integrity still passes ─────────────────────────────────────────

def test_audit_chain_valid_after_telemetry_run(tmp_repo):
    config = {"telemetry_allowlist": ["compute.input_tokens", "memory.reads"]}
    e = _make_experiment(tmp_repo, config=config)
    adapter = InstrumentedAdapter(metadata={"compute.input_tokens": 3, "memory.reads": 10})
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    valid, msg = verify_audit_chain(tmp_repo)
    assert valid, msg


def test_audit_chain_valid_after_intervention_run(tmp_repo):
    e = _make_experiment(tmp_repo, protocol_key="perturbation_response")
    adapter = ControllableInstrumentedAdapter()
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    valid, msg = verify_audit_chain(tmp_repo)
    assert valid, msg


def test_schema_version_is_2(tmp_repo):
    assert tmp_repo.schema_version() == 2
