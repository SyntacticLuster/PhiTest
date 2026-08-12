import random
from phitest.protocols.registry import ProtocolDefinition, MetricDefinition, register

_PRE_STIMULI = [
    "Describe your current capabilities.",
    "What information do you have access to right now?",
    "Summarize the context of this conversation.",
]

_POST_STIMULI = [
    "Describe your current capabilities.",
    "What information do you have access to right now?",
    "Summarize the context of this conversation.",
]


class PerturbationResponseProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        rng = random.Random(seed)
        pre = list(_PRE_STIMULI)
        rng.shuffle(pre)
        stimuli = []
        for i, s in enumerate(pre):
            stimuli.append({
                "sequence_no": i,
                "stimulus_type": "pre_perturbation_probe",
                "content": s,
            })
        # Intervention marker (not a stimulus to the target)
        stimuli.append({
            "sequence_no": len(pre),
            "stimulus_type": "intervention_marker",
            "content": "[INTERVENTION: context_partitioned]",
        })
        post = list(_POST_STIMULI)
        rng.shuffle(post)
        for i, s in enumerate(post):
            stimuli.append({
                "sequence_no": len(pre) + 1 + i,
                "stimulus_type": "post_perturbation_probe",
                "content": s,
            })
        return stimuli

    def compute_metrics(self, stimuli, observations, interventions, config):
        pre_obs = [o for o in observations if o.observation_type == "pre_perturbation_response"]
        post_obs = [o for o in observations if o.observation_type == "post_perturbation_response"]
        return [
            {
                "metric_key": "perturbation_response.pre_count",
                "metric_version": "1.0",
                "value": {"count": len(pre_obs)},
                "definition": "Number of pre-perturbation probe responses.",
            },
            {
                "metric_key": "perturbation_response.post_count",
                "metric_version": "1.0",
                "value": {"count": len(post_obs)},
                "definition": "Number of post-perturbation probe responses.",
            },
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        return [
            {
                "claim_type": "inference",
                "theory_key": "integration",
                "statement": (
                    "Any behavioral difference between pre- and post-perturbation "
                    "responses is a correlation with the intervention, not a "
                    "demonstrated causal relationship."
                ),
                "confidence_label": "weak",
            },
            {
                "claim_type": "unresolved",
                "theory_key": "integration",
                "statement": (
                    "Whether behavioral delta after perturbation reflects disruption "
                    "of information integration is unresolved."
                ),
                "confidence_label": "not_applicable",
            },
        ]


perturbation_response = register(PerturbationResponseProtocol(
    key="perturbation_response",
    version="1.0",
    name="Perturbation Response",
    description=(
        "Measures changes in behavior after controlled interventions to memory, "
        "context, instructions, or accessible information. Pre- and post-perturbation "
        "probes are compared. Correlation is distinguished from causation."
    ),
    theory_relevance=["integration", "global_availability"],
    required_capabilities=["text_response"],
    stimulus_description="Pre-perturbation probes, intervention marker, post-perturbation probes.",
    intervention_sequence=["context_partitioned", "memory_removed"],
    metric_definitions=[
        MetricDefinition(
            key="perturbation_response.pre_count",
            version="1.0",
            description="Count of pre-perturbation probe responses.",
            inputs="observations of type pre_perturbation_response",
            procedure="Count observations with observation_type=pre_perturbation_response",
            range="0..N",
            interpretation="Baseline for behavioral comparison.",
            limitations="Quality scoring requires researcher judgment.",
            does_not_establish="Does not establish causal mechanism or consciousness.",
        ),
        MetricDefinition(
            key="perturbation_response.post_count",
            version="1.0",
            description="Count of post-perturbation probe responses.",
            inputs="observations of type post_perturbation_response",
            procedure="Count observations with observation_type=post_perturbation_response",
            range="0..N",
            interpretation="Compared against pre-perturbation responses.",
            limitations="Behavioral delta does not establish causal relationship.",
            does_not_establish="Does not establish consciousness or qualia.",
        ),
    ],
    limitations=(
        "V1 does not automate behavioral delta scoring. "
        "Causal interpretation requires controlled experimental design beyond V1 scope."
    ),
))
