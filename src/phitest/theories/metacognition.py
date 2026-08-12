from phitest.theories.base import TheoryDefinition, register

metacognition = register(TheoryDefinition(
    key="metacognition",
    name="Metacognitive Access (operational family)",
    summary=(
        "Theories in this family propose that conscious states are those accessible "
        "to higher-order monitoring and reporting. ΦTest measures correspondence "
        "between stated confidence and observable performance."
    ),
    predictions=[
        "A system with metacognitive access should show calibrated confidence relative to accuracy.",
        "Overconfidence or underconfidence rates should be measurable and stable.",
        "Self-correction rate should correlate with accuracy improvement.",
    ],
    relevant_protocols=["metacognitive_calibration"],
    limitations=(
        "Calibration is a behavioral measure. It does not establish that the system "
        "has phenomenal access to its own states. Self-reports are labeled as "
        "self-report behavior, not phenomenal evidence."
    ),
    citation_notes=(
        "Inspired by Higher-Order Thought theories (Rosenthal 1997, Lau & Rosenthal 2011). "
        "ΦTest does not claim to implement or validate HOT theory."
    ),
))
