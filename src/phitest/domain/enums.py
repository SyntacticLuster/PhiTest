from enum import Enum


class ExperimentStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    running = "running"
    completed = "completed"
    failed = "failed"
    archived = "archived"


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ClaimType(str, Enum):
    observation = "observation"
    operational_metric = "operational_metric"
    theory_prediction = "theory_prediction"
    inference = "inference"
    self_report = "self_report"
    unresolved = "unresolved"


class ConfidenceLabel(str, Enum):
    not_applicable = "not_applicable"
    weak = "weak"
    moderate = "moderate"
    strong = "strong"


class InterventionType(str, Enum):
    memory_removed = "memory_removed"
    context_partitioned = "context_partitioned"
    instruction_changed = "instruction_changed"
    information_withheld = "information_withheld"
    noise_injected = "noise_injected"
    cross_session_reset = "cross_session_reset"
