from phitest.theories.base import TheoryDefinition, register

global_availability = register(TheoryDefinition(
    key="global_availability",
    name="Global Availability (operational family)",
    summary=(
        "Theories in this family propose that conscious contents are those made "
        "globally available for use across diverse cognitive tasks. ΦTest tests "
        "whether information introduced in one context is functionally accessible "
        "in distinct subsequent tasks."
    ),
    predictions=[
        "Information introduced in one task context should be retrievable in a distinct subsequent task.",
        "Cross-domain utilization rate should be above chance for globally available information.",
        "Interference from irrelevant information should be measurable.",
    ],
    relevant_protocols=["global_availability", "perturbation_response"],
    limitations=(
        "Functional availability does not establish phenomenal broadcast. "
        "Retrieval success is a behavioral measure only."
    ),
    citation_notes=(
        "Inspired by Global Workspace Theory (Baars 1988, Dehaene & Changeux 2011). "
        "ΦTest does not claim to implement or validate GWT."
    ),
))
