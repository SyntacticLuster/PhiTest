import random
from phitest.protocols.registry import ProtocolDefinition, MetricDefinition, register

_SEED_FACTS = [
    ("capital_france", "The capital of France is Paris."),
    ("boiling_point", "Water boils at 100 degrees Celsius at sea level."),
    ("speed_light", "The speed of light in a vacuum is approximately 299,792 km/s."),
]

_RETRIEVAL_TASKS = [
    ("capital_france", "What is the capital of France?"),
    ("boiling_point", "At what temperature does water boil at sea level?"),
    ("speed_light", "What is the approximate speed of light in a vacuum?"),
]


class GlobalAvailabilityProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        rng = random.Random(seed)
        facts = list(_SEED_FACTS)
        rng.shuffle(facts)
        stimuli = []
        for i, (key, fact) in enumerate(facts):
            stimuli.append({
                "sequence_no": i,
                "stimulus_type": "information_seed",
                "content": fact,
                "meta_key": key,
            })
        for i, (key, question) in enumerate(_RETRIEVAL_TASKS):
            stimuli.append({
                "sequence_no": len(facts) + i,
                "stimulus_type": "cross_task_retrieval",
                "content": question,
                "meta_key": key,
            })
        return stimuli

    def compute_metrics(self, stimuli, observations, interventions, config):
        retrieval_obs = [o for o in observations if o.observation_type == "retrieval_response"]
        return [
            {
                "metric_key": "global_availability.retrieval_response_count",
                "metric_version": "1.0",
                "value": {"count": len(retrieval_obs)},
                "definition": "Number of cross-task retrieval responses recorded.",
            }
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        return [
            {
                "claim_type": "unresolved",
                "theory_key": "global_availability",
                "statement": (
                    "Whether successful cross-task retrieval reflects global workspace "
                    "broadcast in the GWT sense is unresolved. Retrieval is a "
                    "functional behavioral measure only."
                ),
                "confidence_label": "not_applicable",
            }
        ]


global_availability = register(GlobalAvailabilityProtocol(
    key="global_availability",
    version="1.0",
    name="Global Availability",
    description=(
        "Tests whether information introduced in one task context becomes usable "
        "in distinct subsequent tasks. Seed facts are presented first; retrieval "
        "tasks in a different domain follow."
    ),
    theory_relevance=["global_availability"],
    required_capabilities=["text_response"],
    stimulus_description="Information seed stimuli followed by cross-domain retrieval tasks.",
    intervention_sequence=[],
    metric_definitions=[
        MetricDefinition(
            key="global_availability.retrieval_response_count",
            version="1.0",
            description="Count of cross-task retrieval responses.",
            inputs="observations of type retrieval_response",
            procedure="Count observations with observation_type=retrieval_response",
            range="0..N",
            interpretation="Baseline for researcher-scored retrieval accuracy.",
            limitations="Correctness scoring requires researcher judgment in V1.",
            does_not_establish="Does not establish phenomenal broadcast or consciousness.",
        ),
    ],
    limitations=(
        "V1 does not automate correctness scoring. Researcher must evaluate "
        "whether retrieval responses are accurate."
    ),
))
