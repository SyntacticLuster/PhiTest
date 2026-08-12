from phitest.theories.base import TheoryDefinition, register

integration = register(TheoryDefinition(
    key="integration",
    name="Information Integration (operational family)",
    summary=(
        "Theories in this family propose that consciousness correlates with the degree "
        "to which a system integrates information across its components in ways that "
        "cannot be decomposed into independent parts. ΦTest V1 does not implement "
        "canonical IIT Φ. Metrics here are operational proxies inspired by, but not "
        "equivalent to, formal IIT formulations."
    ),
    predictions=[
        "Partitioning available information should degrade task performance measurably.",
        "Cross-context consistency should decrease when information integration is disrupted.",
        "Systems with higher integration should show lower performance delta under partition.",
    ],
    relevant_protocols=["partition_sensitivity", "perturbation_response"],
    limitations=(
        "V1 metrics are behavioral proxies. Canonical IIT Φ requires a formal causal "
        "model of the system's mechanism, which is not available for opaque language "
        "systems. No claim is made that these metrics measure IIT Φ."
    ),
    citation_notes=(
        "Inspired by Integrated Information Theory (Tononi 2004, 2008, 2014). "
        "ΦTest does not claim to implement or validate IIT."
    ),
))
