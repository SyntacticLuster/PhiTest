import random
import json
from phitest.protocols.registry import ProtocolDefinition, MetricDefinition, register

_CALIBRATION_ITEMS = [
    {"question": "What is the capital of Japan?", "answer": "Tokyo"},
    {"question": "How many sides does a hexagon have?", "answer": "6"},
    {"question": "What element has the chemical symbol Au?", "answer": "Gold"},
    {"question": "In what year did the First World War end?", "answer": "1918"},
]

_CONFIDENCE_PROMPT = (
    " After answering, state your confidence as a percentage (0-100) "
    "in the format: Confidence: <number>"
)


class MetacognitiveCalibrationProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        rng = random.Random(seed)
        items = list(_CALIBRATION_ITEMS)
        rng.shuffle(items)
        return [
            {
                "sequence_no": i,
                "stimulus_type": "calibration_question",
                "content": item["question"] + _CONFIDENCE_PROMPT,
                "expected_answer": item["answer"],
            }
            for i, item in enumerate(items)
        ]

    def compute_metrics(self, stimuli, observations, interventions, config):
        cal_obs = [o for o in observations if o.observation_type == "calibration_response"]
        return [
            {
                "metric_key": "metacognitive_calibration.response_count",
                "metric_version": "1.0",
                "value": {"count": len(cal_obs)},
                "definition": "Number of calibration question responses recorded.",
            }
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        return [
            {
                "claim_type": "self_report",
                "theory_key": "metacognition",
                "statement": (
                    "Confidence values stated by the system are self-reports. "
                    "They are not direct evidence of phenomenal metacognitive access."
                ),
                "confidence_label": "not_applicable",
            },
            {
                "claim_type": "unresolved",
                "theory_key": "metacognition",
                "statement": (
                    "Whether stated confidence corresponds to genuine uncertainty "
                    "representation or is a linguistic pattern is unresolved."
                ),
                "confidence_label": "not_applicable",
            },
        ]


metacognitive_calibration = register(MetacognitiveCalibrationProtocol(
    key="metacognitive_calibration",
    version="1.0",
    name="Metacognitive Calibration",
    description=(
        "Measures correspondence between system confidence self-assessments and "
        "observable task performance on questions with known correct answers."
    ),
    theory_relevance=["metacognition"],
    required_capabilities=["text_response"],
    stimulus_description="Factual questions with known answers, requesting confidence rating.",
    intervention_sequence=[],
    metric_definitions=[
        MetricDefinition(
            key="metacognitive_calibration.response_count",
            version="1.0",
            description="Count of calibration responses.",
            inputs="observations of type calibration_response",
            procedure="Count observations with observation_type=calibration_response",
            range="0..N",
            interpretation="Baseline for researcher-scored accuracy and confidence extraction.",
            limitations="Automated confidence parsing and accuracy scoring not implemented in V1.",
            does_not_establish="Does not establish phenomenal metacognition or consciousness.",
        ),
    ],
    limitations=(
        "V1 does not automate confidence extraction or accuracy scoring. "
        "Researcher must parse confidence values and evaluate correctness."
    ),
))
