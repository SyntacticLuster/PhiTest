import pytest
from phitest.application import experiment_service
from phitest.domain.errors import NotFoundError, ValidationError


def test_create_subject(tmp_repo):
    s = experiment_service.create_subject(tmp_repo, {
        "name": "TestBot", "subject_type": "ai", "adapter_type": "manual",
    })
    assert s.name == "TestBot"
    assert s.id
    loaded = tmp_repo.get_subject(s.id)
    assert loaded.name == "TestBot"


def test_create_subject_audit(tmp_repo):
    experiment_service.create_subject(tmp_repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    events = tmp_repo.list_audit_events()
    assert any(e.event_type == "subject_created" for e in events)


def test_archive_subject(tmp_repo):
    s = experiment_service.create_subject(tmp_repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    archived = experiment_service.archive_subject(tmp_repo, s.id)
    assert archived.archived_at is not None


def test_archive_nonexistent_raises(tmp_repo):
    with pytest.raises(NotFoundError):
        experiment_service.archive_subject(tmp_repo, "nonexistent")
