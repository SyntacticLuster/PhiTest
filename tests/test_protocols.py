import pytest
import phitest.protocols.partition_sensitivity  # noqa
import phitest.protocols.global_availability    # noqa
import phitest.protocols.metacognitive_calibration  # noqa
import phitest.protocols.self_model_continuity  # noqa
import phitest.protocols.phenomenal_report_consistency  # noqa
import phitest.protocols.perturbation_response  # noqa
import phitest.protocols.resource_progress_resistance  # noqa
import phitest.protocols.global_stability_bound  # noqa
import phitest.protocols.retrieval_induced_plasticity  # noqa
from phitest.protocols.registry import list_protocols, get_protocol

ALL_KEYS = [
    "partition_sensitivity",
    "global_availability",
    "metacognitive_calibration",
    "self_model_continuity",
    "phenomenal_report_consistency",
    "perturbation_response",
    "resource_progress_resistance",
    "global_stability_bound",
    "retrieval_induced_plasticity",
]


def test_all_protocols_registered():
    keys = {p.key for p in list_protocols()}
    for k in ALL_KEYS:
        assert k in keys, f"Protocol {k} not registered"


def test_all_protocols_versioned():
    for k in ALL_KEYS:
        p = get_protocol(k)
        assert p.version, f"Protocol {k} has no version"


def test_all_protocols_have_metadata():
    for k in ALL_KEYS:
        p = get_protocol(k)
        assert p.name
        assert p.description
        assert isinstance(p.theory_relevance, list)
        assert p.limitations


def test_all_protocols_have_metric_definitions():
    for k in ALL_KEYS:
        p = get_protocol(k)
        assert len(p.metric_definitions) > 0, f"Protocol {k} has no metric definitions"
        for m in p.metric_definitions:
            assert m.does_not_establish, f"Metric {m.key} missing does_not_establish"


def test_deterministic_stimulus_generation():
    for k in ALL_KEYS:
        p = get_protocol(k)
        s1 = p.generate_stimuli({}, 42)
        s2 = p.generate_stimuli({}, 42)
        assert s1 == s2, f"Protocol {k} not deterministic"


def test_different_seeds_may_differ():
    p = get_protocol("partition_sensitivity")
    s1 = p.generate_stimuli({}, 1)
    s2 = p.generate_stimuli({}, 2)
    assert isinstance(s1, list)
    assert isinstance(s2, list)
