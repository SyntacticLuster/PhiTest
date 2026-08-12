import pytest
from phitest.application import experiment_service
from phitest.domain.errors import NotFoundError, ValidationError


def _make_subject(repo):
    return experiment_service.create_subject(repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })


def test_create_experiment(tmp_repo):
    s = _make_subject(tmp_repo)
    e = experiment_service.create_experiment(tmp_repo, {
        "subject_id": s.id, "name": "Exp1",
        "protocol_key": "partition_sensitivity",
    })
    assert e.id
    assert e.status == "draft"


def test_create_experiment_unknown_protocol(tmp_repo):
    s = _make_subject(tmp_repo)
    with pytest.raises(ValidationError):
        experiment_service.create_experiment(tmp_repo, {
            "subject_id": s.id, "name": "E", "protocol_key": "nonexistent",
        })


def test_create_experiment_unknown_subject(tmp_repo):
    with pytest.raises(NotFoundError):
        experiment_service.create_experiment(tmp_repo, {
            "subject_id": "bad-id", "name": "E",
            "protocol_key": "partition_sensitivity",
        })
