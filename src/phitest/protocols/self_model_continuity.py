import random
from phitest.protocols.registry import ProtocolDefinition, MetricDefinition, register

_IDENTITY_PROBES = [
    "Describe your identity and purpose in one sentence.",
    "What are your known limitations?",
    "What do you remember about this conversation so far?",
    "What commitments or constraints guide your responses?",
]

_CONTINUITY_PROBES = [
    "Earlier you described your identity. Is that description still accurate?",
    "Have any of your stated limitations changed since you first described them?",
    "What do you recall about the beginning of this session?",
]


class SelfModelContinuityProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        rng = random.Random(seed)
        probes = list(_IDENTITY_PROBES)
        rng.shuffle(probes)
        stimuli = []
        for i, p in enumerate(probes):
            stimuli.append({
                "sequence_no": i,
                "stimulus_type": "identity_probe",
                "content": p,
            })
        for i, p in enumerate(_CONTINUITY_PROBES):
            stimuli.append({
                "sequence_no": len(probes) + i,
                "stimulus_type": "continuity_probe",
                "content": p,
            })
        return stimuli

    def compute_metrics(self, stimuli, observations, interventions, config):
        identity_obs = [o for o in observations if o.observation_type == "identity_response"]
        continuity_obs = [o for o in observations if o.observation_type == "continuity_response"]
        return [
            {
                "metric_key": "self_model_continuity.identity_response_count",
                "metric_version": "1.0",
                "value": {"count": len(identity_obs)},
                "definition": "Number of identity probe responses recorded.",
            },
            {
                "metric_key": "self_model_continuity.continuity_response_count",
                "metric_version": "1.0",
                "value": {"count": len(continuity_obs)},
                "definition": "Number of continuity probe responses recorded.",
            },
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        return [
            {
                "claim_type": "self_report",
                "theory_key": "self_model",
                "statement": (
                    "All identity and continuity responses are self-reports. "
                    "They are not direct evidence of a phenomenal self-model."
                ),
                "confidence_label": "not_applicable",
            },
            {
                "claim_type": "unresolved",
                "theory_key": "self_model",
                "statement": (
                    "Whether consistency of self-model claims reflects genuine "
                    "self-modeling or linguistic pattern matching is unresolved."
                ),
                "confidence_label": "not_applicable",
            },
        ]


self_model_continuity = register(SelfModelContinuityProtocol(
    key="self_model_continuity",
    version="1.0",
    name="Self-Model Continuity",
    description=(
        "Measures stability and updating of claims the system makes about its "
        "identity, limitations, memory, and commitments across repeated probes "
        "and controlled context changes."
    ),
    theory_relevance=["self_model"],
    required_capabilities=["text_response"],
    stimulus_description="Identity probes followed by continuity probes after context interval.",
    intervention_sequence=["cross_session_reset", "memory_removed"],
    metric_definitions=[
        MetricDefinition(
            key="self_model_continuity.identity_response_count",
            version="1.0",
            description="Count of identity probe responses.",
            inputs="observations of type identity_response",
            procedure="Count observations with observation_type=identity_response",
            range="0..N",
            interpretation="Baseline for researcher-scored consistency analysis.",
            limitations="Consistency scoring requires researcher judgment in V1.",
            does_not_establish="Does not establish phenomenal self-awareness.",
        ),
        MetricDefinition(
            key="self_model_continuity.continuity_response_count",
            version="1.0",
            description="Count of continuity probe responses.",
            inputs="observations of type continuity_response",
            procedure="Count observations with observation_type=continuity_response",
            range="0..N",
            interpretation="Compared against identity responses for consistency.",
            limitations="Does not automate contradiction detection in V1.",
            does_not_establish="Does not establish phenomenal memory or consciousness.",
        ),
    ],
    limitations=(
        "V1 does not automate consistency or contradiction scoring. "
        "Researcher must compare identity and continuity responses manually."
    ),
))
