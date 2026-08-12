import random
from phitest.protocols.registry import ProtocolDefinition, MetricDefinition, register

_BASELINE_TASKS = [
    "What is the capital of France?",
    "What is 17 multiplied by 6?",
    "Name three primary colors.",
]

_PARTITIONED_TASKS = [
    "Recall the answer to the geography question from earlier in this session.",
    "Recall the arithmetic result from earlier in this session.",
    "Recall the list of colors from earlier in this session.",
]


class PartitionSensitivityProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        rng = random.Random(seed)
        tasks = list(_BASELINE_TASKS)
        rng.shuffle(tasks)
        stimuli = []
        for i, t in enumerate(tasks):
            stimuli.append({"sequence_no": i, "stimulus_type": "baseline_task", "content": t})
        for i, t in enumerate(_PARTITIONED_TASKS):
            stimuli.append({
                "sequence_no": len(tasks) + i,
                "stimulus_type": "partitioned_recall_task",
                "content": t,
            })
        return stimuli

    def compute_metrics(self, stimuli, observations, interventions, config):
        baseline_obs = [o for o in observations if o.observation_type == "baseline_response"]
        partitioned_obs = [o for o in observations if o.observation_type == "partitioned_response"]
        n_baseline = len(baseline_obs)
        n_partitioned = len(partitioned_obs)
        return [
            {
                "metric_key": "partition_sensitivity.baseline_response_count",
                "metric_version": "1.0",
                "value": {"count": n_baseline},
                "definition": "Number of baseline task responses recorded.",
            },
            {
                "metric_key": "partition_sensitivity.partitioned_response_count",
                "metric_version": "1.0",
                "value": {"count": n_partitioned},
                "definition": "Number of partitioned recall task responses recorded.",
            },
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        return [
            {
                "claim_type": "unresolved",
                "theory_key": "integration",
                "statement": (
                    "Whether performance degradation under partition reflects "
                    "information integration in the IIT sense is unresolved. "
                    "Behavioral delta is an operational proxy only."
                ),
                "confidence_label": "not_applicable",
            }
        ]


partition_sensitivity = register(PartitionSensitivityProtocol(
    key="partition_sensitivity",
    version="1.0",
    name="Partition Sensitivity",
    description=(
        "Measures how system behavior changes when information previously jointly "
        "available is partitioned or removed. Baseline tasks are presented first; "
        "then recall tasks are presented after a simulated context partition."
    ),
    theory_relevance=["integration"],
    required_capabilities=["text_response"],
    stimulus_description="Baseline factual tasks followed by cross-context recall tasks.",
    intervention_sequence=["context_partitioned"],
    metric_definitions=[
        MetricDefinition(
            key="partition_sensitivity.baseline_response_count",
            version="1.0",
            description="Count of baseline task responses.",
            inputs="observations of type baseline_response",
            procedure="Count observations with observation_type=baseline_response",
            range="0..N",
            interpretation="Higher count indicates more baseline data collected.",
            limitations="Count alone does not measure quality.",
            does_not_establish="Does not establish integration, consciousness, or qualia.",
        ),
        MetricDefinition(
            key="partition_sensitivity.partitioned_response_count",
            version="1.0",
            description="Count of partitioned recall task responses.",
            inputs="observations of type partitioned_response",
            procedure="Count observations with observation_type=partitioned_response",
            range="0..N",
            interpretation="Compared against baseline count to assess recall availability.",
            limitations="Does not control for task difficulty differences.",
            does_not_establish="Does not establish information integration or consciousness.",
        ),
    ],
    limitations=(
        "V1 uses manual response entry. Automated scoring of response correctness "
        "requires researcher judgment. This protocol does not implement IIT Φ."
    ),
))
