from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class Subject(BaseModel):
    id: str
    name: str
    description: str = ""
    subject_type: str
    adapter_type: str
    adapter_config_json: str = "{}"
    created_at: datetime
    archived_at: datetime | None = None


class Experiment(BaseModel):
    id: str
    subject_id: str
    name: str
    description: str = ""
    protocol_key: str
    theory_keys_json: str = "[]"
    configuration_json: str = "{}"
    created_at: datetime
    created_by: str = "researcher"
    status: str = "draft"


class Run(BaseModel):
    id: str
    experiment_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "pending"
    random_seed: int | None = None
    protocol_version: str
    target_adapter: str
    failure_reason: str | None = None


class Stimulus(BaseModel):
    id: str
    run_id: str
    sequence_no: int
    stimulus_type: str
    content: str
    content_sha256: str
    created_at: datetime


class Observation(BaseModel):
    id: str
    run_id: str
    stimulus_id: str | None = None
    sequence_no: int
    observation_type: str
    content: str
    content_sha256: str
    created_at: datetime


class Intervention(BaseModel):
    id: str
    run_id: str
    sequence_no: int
    intervention_type: str
    configuration_json: str = "{}"
    rationale: str = ""
    created_at: datetime


class MetricResult(BaseModel):
    id: str
    run_id: str
    metric_key: str
    metric_version: str
    value_json: str
    definition: str
    computed_at: datetime


class EvidenceClaim(BaseModel):
    id: str
    run_id: str
    claim_type: str
    theory_key: str | None = None
    statement: str
    evidence_json: str = "{}"
    confidence_label: str = "not_applicable"
    created_at: datetime


class AuditEvent(BaseModel):
    id: str
    event_type: str
    entity_type: str
    entity_id: str
    payload_json: str
    created_at: datetime
    previous_event_hash: str | None = None
    event_hash: str


class TargetResponse(BaseModel):
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime
