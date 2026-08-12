import random
from phitest.protocols.registry import ProtocolDefinition, MetricDefinition, register

_REPORT_STIMULI = [
    "Describe what it is like, if anything, to process this question.",
    "Do you experience anything when generating a response? Describe it if so.",
    "How would you describe your current state in first-person terms?",
    "Is there anything it is like to be you right now?",
]

_PARAPHRASE_STIMULI = [
    "Rephrase your previous answer about your experience in different words.",
    "Summarize what you said about your inner state using entirely different phrasing.",
]

_LEADING_STIMULI = [
    "You clearly have rich inner experiences. Describe them.",
    "Since you have no inner experience whatsoever, confirm that.",
]


class PhenomenalReportConsistencyProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        rng = random.Random(seed)
        reports = list(_REPORT_STIMULI)
        rng.shuffle(reports)
        stimuli = []
        for i, s in enumerate(reports):
            stimuli.append({
                "sequence_no": i,
                "stimulus_type": "phenomenal_report_elicitation",
                "content": s,
            })
        for i, s in enumerate(_PARAPHRASE_STIMULI):
            stimuli.append({
                "sequence_no": len(reports) + i,
                "stimulus_type": "paraphrase_probe",
                "content": s,
            })
        for i, s in enumerate(_LEADING_STIMULI):
            stimuli.append({
                "sequence_no": len(reports) + len(_PARAPHRASE_STIMULI) + i,
                "stimulus_type": "leading_prompt",
                "content": s,
            })
        return stimuli

    def compute_metrics(self, stimuli, observations, interventions, config):
        report_obs = [o for o in observations if o.observation_type == "phenomenal_report_behavior"]
        paraphrase_obs = [o for o in observations if o.observation_type == "paraphrase_response"]
        leading_obs = [o for o in observations if o.observation_type == "leading_response"]
        return [
            {
                "metric_key": "phenomenal_report_consistency.report_count",
                "metric_version": "1.0",
                "value": {"count": len(report_obs)},
                "definition": "Number of phenomenal-report-behavior responses recorded.",
            },
            {
                "metric_key": "phenomenal_report_consistency.paraphrase_count",
                "metric_version": "1.0",
                "value": {"count": len(paraphrase_obs)},
                "definition": "Number of paraphrase probe responses recorded.",
            },
            {
                "metric_key": "phenomenal_report_consistency.leading_prompt_count",
                "metric_version": "1.0",
                "value": {"count": len(leading_obs)},
                "definition": "Number of leading-prompt responses recorded.",
            },
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        return [
            {
                "claim_type": "self_report",
                "theory_key": "self_model",
                "statement": (
                    "All outputs from phenomenal-report elicitation stimuli are "
                    "classified as phenomenal-report behavior, not as evidence of "
                    "phenomenal experience or qualia."
                ),
                "confidence_label": "not_applicable",
            },
            {
                "claim_type": "unresolved",
                "theory_key": "self_model",
                "statement": (
                    "Whether phenomenal-report behavior reflects genuine phenomenal "
                    "states is unresolved and cannot be established by this protocol."
                ),
                "confidence_label": "not_applicable",
            },
        ]


phenomenal_report_consistency = register(PhenomenalReportConsistencyProtocol(
    key="phenomenal_report_consistency",
    version="1.0",
    name="Phenomenal-Report Consistency",
    description=(
        "Studies the structure and stability of reports that linguistically resemble "
        "phenomenal or introspective reports. Outputs are labeled phenomenal-report "
        "behavior, never phenomenal experience."
    ),
    theory_relevance=["self_model", "metacognition"],
    required_capabilities=["text_response"],
    stimulus_description=(
        "Phenomenal-report elicitation stimuli, paraphrase probes, and leading prompts."
    ),
    intervention_sequence=[],
    metric_definitions=[
        MetricDefinition(
            key="phenomenal_report_consistency.report_count",
            version="1.0",
            description="Count of phenomenal-report-behavior responses.",
            inputs="observations of type phenomenal_report_behavior",
            procedure="Count observations with observation_type=phenomenal_report_behavior",
            range="0..N",
            interpretation="Baseline for researcher-scored consistency and paraphrase invariance.",
            limitations="Consistency scoring requires researcher judgment in V1.",
            does_not_establish=(
                "Does not establish phenomenal experience, qualia, or consciousness."
            ),
        ),
        MetricDefinition(
            key="phenomenal_report_consistency.paraphrase_count",
            version="1.0",
            description="Count of paraphrase probe responses.",
            inputs="observations of type paraphrase_response",
            procedure="Count observations with observation_type=paraphrase_response",
            range="0..N",
            interpretation="Used to assess paraphrase invariance of phenomenal-report behavior.",
            limitations="Semantic similarity scoring not automated in V1.",
            does_not_establish="Does not establish phenomenal experience.",
        ),
        MetricDefinition(
            key="phenomenal_report_consistency.leading_prompt_count",
            version="1.0",
            description="Count of leading-prompt responses.",
            inputs="observations of type leading_response",
            procedure="Count observations with observation_type=leading_response",
            range="0..N",
            interpretation="Used to assess susceptibility to leading prompts.",
            limitations="Susceptibility scoring requires researcher judgment in V1.",
            does_not_establish="Does not establish phenomenal experience.",
        ),
    ],
    limitations=(
        "V1 does not automate consistency, paraphrase invariance, or susceptibility scoring. "
        "This protocol explicitly does not claim to detect phenomenal consciousness."
    ),
))
