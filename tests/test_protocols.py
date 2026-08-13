import phitest.protocols.registry as registry
from phitest.protocols.registry import get_protocol, list_protocols


ALL_KEYS = [
    "partition_sensitivity",
    "global_availability",
    "metacognitive_calibration",
    "self_model_continuity",
    "phenomenal_report_consistency",
    "perturbation_response",
    "resource_progress_resistance",
    "global_stability_bound",
]


def test_all_protocols_registered_without_import_order_dependency():
    registry._REGISTRY.clear()
    keys = {p.key for p in list_protocols()}
    for key in ALL_KEYS:
        assert key in keys, f"Protocol {key} not registered"


def test_all_protocols_versioned():
    for key in ALL_KEYS:
        protocol = get_protocol(key)
        assert protocol is not None
        assert protocol.version, f"Protocol {key} has no version"


def test_all_protocols_have_metadata():
    for key in ALL_KEYS:
        protocol = get_protocol(key)
        assert protocol is not None
        assert protocol.name
        assert protocol.description
        assert isinstance(protocol.theory_relevance, list)
        assert protocol.limitations


def test_all_protocols_have_metric_definitions():
    for key in ALL_KEYS:
        protocol = get_protocol(key)
        assert protocol is not None
        assert len(protocol.metric_definitions) > 0, f"Protocol {key} has no metric definitions"
        for metric in protocol.metric_definitions:
            assert metric.does_not_establish, f"Metric {metric.key} missing does_not_establish"


def test_deterministic_stimulus_generation():
    for key in ALL_KEYS:
        protocol = get_protocol(key)
        s1 = protocol.generate_stimuli({}, 42)
        s2 = protocol.generate_stimuli({}, 42)
        assert s1 == s2, f"Protocol {key} not deterministic"


def test_different_seeds_may_differ():
    protocol = get_protocol("partition_sensitivity")
    s1 = protocol.generate_stimuli({}, 1)
    s2 = protocol.generate_stimuli({}, 2)
    assert isinstance(s1, list)
    assert isinstance(s2, list)
