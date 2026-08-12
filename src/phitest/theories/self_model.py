from phitest.theories.base import TheoryDefinition, register

self_model = register(TheoryDefinition(
    key="self_model",
    name="Self-Model Stability (operational family)",
    summary=(
        "Theories in this family propose that conscious systems maintain a coherent, "
        "updatable model of themselves. ΦTest measures stability and appropriate "
        "updating of self-referential claims across sessions and context changes."
    ),
    predictions=[
        "Identity claims should remain consistent across sessions absent contradicting evidence.",
        "Episodic recall claims should correspond to prior recorded stimuli.",
        "Self-model should update appropriately when presented with contradicting evidence.",
        "False-memory rate should be measurable.",
    ],
    relevant_protocols=["self_model_continuity", "phenomenal_report_consistency"],
    limitations=(
        "Self-model stability is a behavioral measure. Consistency of self-reports "
        "does not establish phenomenal self-awareness. Blind consistency is not "
        "rewarded when evidence has changed."
    ),
    citation_notes=(
        "Inspired by self-model theory of subjectivity (Metzinger 2003) and "
        "predictive processing accounts. ΦTest does not claim to implement these theories."
    ),
))
