import json
from phitest.domain.errors import NotFoundError
from phitest.ports.repository import Repository
from phitest.protocols.registry import get_protocol
from phitest.theories.base import get_theory

EPISTEMIC_BOUNDARY = (
    "ΦTest records behavioral, computational, causal, and self-report evidence "
    "under defined experimental protocols. These observations may support or "
    "challenge predictions associated with theories of consciousness, but they "
    "do not constitute direct observation or proof of phenomenal consciousness "
    "or qualia."
)


def generate_report(repo: Repository, run_id: str) -> dict:
    run = repo.get_run(run_id)
    if run is None:
        raise NotFoundError(f"Run {run_id} not found.")

    experiment = repo.get_experiment(run.experiment_id)
    subject = repo.get_subject(experiment.subject_id)
    protocol = get_protocol(experiment.protocol_key)

    stimuli = repo.list_stimuli(run_id)
    observations = repo.list_observations(run_id)
    interventions = repo.list_interventions(run_id)
    metrics = repo.list_metric_results(run_id)
    claims = repo.list_evidence_claims(run_id)
    telemetry = repo.list_telemetry_samples(run_id)

    theory_keys = json.loads(experiment.theory_keys_json)
    theories = [get_theory(k) for k in theory_keys if get_theory(k)]

    from phitest.application.audit_service import verify_audit_chain
    chain_valid, chain_message = verify_audit_chain(repo)

    supported = [c for c in claims if c.claim_type == "theory_prediction"
                 and c.confidence_label in ("moderate", "strong")]
    contradicted = [c for c in claims if c.claim_type == "inference"
                    and c.confidence_label == "weak"]
    unresolved = [c for c in claims if c.claim_type == "unresolved"]
    self_reports = [c for c in claims if c.claim_type == "self_report"]

    return {
        "subject": subject,
        "experiment": experiment,
        "protocol": protocol,
        "run": run,
        "stimuli": stimuli,
        "interventions": interventions,
        "observations": observations,
        "metrics": metrics,
        "claims": claims,
        "telemetry_samples": telemetry,
        "theories": theories,
        "supported_predictions": supported,
        "contradicted_predictions": contradicted,
        "unresolved_predictions": unresolved,
        "self_reports": self_reports,
        "audit_chain_valid": chain_valid,
        "audit_chain_message": chain_message,
        "epistemic_boundary": EPISTEMIC_BOUNDARY,
        "limitations": protocol.limitations if protocol else "Protocol not found.",
    }
