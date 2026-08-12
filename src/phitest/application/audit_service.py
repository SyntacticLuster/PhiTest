import hashlib
import json
import uuid
from datetime import datetime, timezone

from phitest.domain.models import AuditEvent
from phitest.ports.repository import Repository


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(previous: str | None, payload: str) -> str:
    data = (previous or "") + payload
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def emit(
    repo: Repository,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
) -> AuditEvent:
    last = repo.get_last_audit_event()
    prev_hash = last.event_hash if last else None
    # Redact auth headers from payload
    safe_payload = {k: v for k, v in payload.items() if "auth" not in k.lower()}
    payload_json = json.dumps(safe_payload, sort_keys=True)
    event_hash = _hash(prev_hash, payload_json)
    event = AuditEvent(
        id=str(uuid.uuid4()),
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=payload_json,
        created_at=_now(),
        previous_event_hash=prev_hash,
        event_hash=event_hash,
    )
    repo.append_audit_event(event)
    return event


def verify_audit_chain(repo: Repository) -> tuple[bool, str]:
    events = repo.list_audit_events()
    if not events:
        return True, "Chain is empty."
    prev_hash = None
    for i, event in enumerate(events):
        expected = _hash(prev_hash, event.payload_json)
        if event.event_hash != expected:
            return False, f"Hash mismatch at event index {i} (id={event.id})."
        if event.previous_event_hash != prev_hash:
            return False, f"Previous hash mismatch at event index {i} (id={event.id})."
        prev_hash = event.event_hash
    return True, f"Chain valid. {len(events)} events verified."
