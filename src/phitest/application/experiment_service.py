import uuid
from datetime import datetime, timezone

from phitest.domain.models import Subject, Experiment
from phitest.domain.errors import NotFoundError, ValidationError
from phitest.ports.repository import Repository
from phitest.application import audit_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_subject(repo: Repository, data: dict) -> Subject:
    subject = Subject(
        id=str(uuid.uuid4()),
        name=data["name"],
        description=data.get("description", ""),
        subject_type=data["subject_type"],
        adapter_type=data["adapter_type"],
        adapter_config_json=data.get("adapter_config_json", "{}"),
        created_at=_now(),
    )
    repo.save_subject(subject)
    audit_service.emit(repo, "subject_created", "subject", subject.id,
                       {"name": subject.name, "adapter_type": subject.adapter_type})
    return subject


def archive_subject(repo: Repository, subject_id: str) -> Subject:
    subject = repo.get_subject(subject_id)
    if subject is None:
        raise NotFoundError(f"Subject {subject_id} not found.")
    subject.archived_at = _now()
    repo.save_subject(subject)
    audit_service.emit(repo, "subject_archived", "subject", subject_id, {})
    return subject


def create_experiment(repo: Repository, data: dict) -> Experiment:
    from phitest.protocols.registry import get_protocol
    subject = repo.get_subject(data["subject_id"])
    if subject is None:
        raise NotFoundError(f"Subject {data['subject_id']} not found.")
    if get_protocol(data["protocol_key"]) is None:
        raise ValidationError(f"Unknown protocol: {data['protocol_key']}")
    experiment = Experiment(
        id=str(uuid.uuid4()),
        subject_id=data["subject_id"],
        name=data["name"],
        description=data.get("description", ""),
        protocol_key=data["protocol_key"],
        theory_keys_json=data.get("theory_keys_json", "[]"),
        configuration_json=data.get("configuration_json", "{}"),
        created_at=_now(),
        created_by=data.get("created_by", "researcher"),
        status="draft",
    )
    repo.save_experiment(experiment)
    audit_service.emit(repo, "experiment_created", "experiment", experiment.id,
                       {"name": experiment.name, "protocol_key": experiment.protocol_key})
    return experiment
