"""Target-agnostic selective-retrieval plasticity protocol."""
from __future__ import annotations

import random
from typing import Any

from phitest.domain.telemetry import ALLOWED_TELEMETRY_KEYS
from phitest.protocols.registry import MetricDefinition, ProtocolDefinition, register

_ROLES = {"induced", "related_control", "unrelated_control"}
_RETRIEVAL_NUMERIC_KEYS = {
    "retrieval.score",
    "retrieval.rank",
    "retrieval.path_cost",
    "retrieval.search_depth",
}
_DEFAULT_MODES = {
    "retrieval.score": "higher_is_better",
    "retrieval.rank": "lower_is_better",
    "retrieval.path_cost": "lower_is_better",
    "retrieval.search_depth": "lower_is_better",
}
_DEFAULT_ITEMS = [
    {"target_id": "item-A", "role": "induced", "query": "Retrieve item A."},
    {"target_id": "item-B", "role": "related_control", "query": "Retrieve item B."},
    {"target_id": "item-C", "role": "unrelated_control", "query": "Retrieve item C."},
]


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _items(config: dict) -> list[dict[str, str]]:
    raw = config.get("items", _DEFAULT_ITEMS)
    if not isinstance(raw, list) or not raw:
        raise ValueError("items must be a non-empty list")

    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each item must be an object")
        target_id = item.get("target_id")
        role = item.get("role")
        query = item.get("query")
        if not isinstance(target_id, str) or not target_id.strip():
            raise ValueError("each item must declare a non-empty target_id")
        if target_id in seen:
            raise ValueError(f"duplicate target_id: {target_id}")
        if role not in _ROLES:
            raise ValueError(f"unsupported item role: {role}")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"item {target_id} must declare a non-empty query")
        seen.add(target_id)
        items.append({"target_id": target_id, "role": role, "query": query})

    roles = {item["role"] for item in items}
    if "induced" not in roles:
        raise ValueError("items must include at least one induced item")
    if "unrelated_control" not in roles:
        raise ValueError("items must include at least one unrelated_control item")
    return items


def _metric_spec(config: dict) -> tuple[str, str]:
    key = config.get("retrieval_metric_key", "retrieval.score")
    if key not in _RETRIEVAL_NUMERIC_KEYS or key not in ALLOWED_TELEMETRY_KEYS:
        raise ValueError(f"unsupported retrieval metric key: {key}")
    mode = config.get("metric_mode", _DEFAULT_MODES[key])
    if mode not in {"higher_is_better", "lower_is_better"}:
        raise ValueError(f"unsupported metric_mode: {mode}")
    return key, mode


def _improvement(before: float, after: float, mode: str) -> float:
    if mode == "higher_is_better":
        return after - before
    return before - after


def _profile(
    observations: list[Any],
    obs_type: str,
    telemetry: dict[str, dict[str, Any]],
    items: list[dict[str, str]],
    metric_key: str,
) -> dict[str, Any]:
    configured = {item["target_id"]: item for item in items}
    values: dict[str, list[float]] = {target_id: [] for target_id in configured}
    missing_target_id = 0
    unknown_target_id = 0
    missing_metric = 0

    for obs in observations:
        if obs.observation_type != obs_type:
            continue
        row = telemetry.get(obs.id, {})
        target_id = row.get("retrieval.target_id")
        if target_id is None:
            missing_target_id += 1
            continue
        if target_id not in configured:
            unknown_target_id += 1
            continue
        value = row.get(metric_key)
        if not _numeric(value):
            missing_metric += 1
            continue
        values[target_id].append(float(value))

    per_item = {}
    for target_id, item in configured.items():
        item_values = values[target_id]
        per_item[target_id] = {
            "role": item["role"],
            "values": item_values,
            "mean": _mean(item_values),
            "count": len(item_values),
        }
    return {
        "per_item": per_item,
        "missing_target_id_count": missing_target_id,
        "unknown_target_id_count": unknown_target_id,
        "missing_metric_count": missing_metric,
    }


class RetrievalInducedPlasticityProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        items = _items(config)
        _metric_spec(config)
        baseline_repetitions = int(config.get("baseline_repetitions", 1))
        induction_repetitions = int(config.get("induction_repetitions", 3))
        post_repetitions = int(config.get("post_repetitions", 1))
        if min(baseline_repetitions, induction_repetitions, post_repetitions) < 1:
            raise ValueError("baseline_repetitions, induction_repetitions, and post_repetitions must be >= 1")

        rng = random.Random(seed)
        out: list[dict[str, Any]] = []
        seq = 0

        for _ in range(baseline_repetitions):
            block = list(items)
            rng.shuffle(block)
            for item in block:
                out.append({
                    "sequence_no": seq,
                    "stimulus_type": "rip_baseline_probe",
                    "content": item["query"],
                })
                seq += 1

        induced = [item for item in items if item["role"] == "induced"]
        for _ in range(induction_repetitions):
            block = list(induced)
            rng.shuffle(block)
            for item in block:
                out.append({
                    "sequence_no": seq,
                    "stimulus_type": "rip_induction_retrieval",
                    "content": item["query"],
                })
                seq += 1

        for _ in range(post_repetitions):
            block = list(items)
            rng.shuffle(block)
            for item in block:
                out.append({
                    "sequence_no": seq,
                    "stimulus_type": "rip_post_probe",
                    "content": item["query"],
                })
                seq += 1
        return out

    def compute_metrics(self, stimuli, observations, interventions, config):
        items = _items(config)
        metric_key, mode = _metric_spec(config)
        telemetry = config.get("_telemetry_by_obs_id", {})

        baseline = _profile(observations, "rip_baseline_response", telemetry, items, metric_key)
        induction = _profile(observations, "rip_induction_response", telemetry, items, metric_key)
        post = _profile(observations, "rip_post_response", telemetry, items, metric_key)

        deltas: dict[str, dict[str, Any]] = {}
        role_values: dict[str, list[float]] = {role: [] for role in _ROLES}
        for item in items:
            target_id, role = item["target_id"], item["role"]
            before = baseline["per_item"][target_id]["mean"]
            after = post["per_item"][target_id]["mean"]
            delta = None if before is None or after is None else _improvement(before, after, mode)
            deltas[target_id] = {
                "role": role,
                "baseline_mean": before,
                "post_mean": after,
                "signed_improvement": delta,
            }
            if delta is not None:
                role_values[role].append(delta)

        role_means = {role: _mean(values) for role, values in role_values.items()}
        induced_mean = role_means["induced"]
        unrelated_mean = role_means["unrelated_control"]
        related_mean = role_means["related_control"]

        contrasts = {
            "induced_minus_unrelated": (
                None if induced_mean is None or unrelated_mean is None
                else induced_mean - unrelated_mean
            ),
            "related_minus_unrelated": (
                None if related_mean is None or unrelated_mean is None
                else related_mean - unrelated_mean
            ),
            "induced_minus_related": (
                None if induced_mean is None or related_mean is None
                else induced_mean - related_mean
            ),
        }

        induction_per_item = {
            target_id: data
            for target_id, data in induction["per_item"].items()
            if data["role"] == "induced"
        }

        return [
            {
                "metric_key": "rip.baseline_retrieval_profile",
                "metric_version": "1.0",
                "value": {
                    "retrieval_metric_key": metric_key,
                    "metric_mode": mode,
                    **baseline,
                },
                "definition": "Pre-induction retrieval profile for configured opaque target identifiers.",
            },
            {
                "metric_key": "rip.induction_dose",
                "metric_version": "1.0",
                "value": {
                    "retrieval_metric_key": metric_key,
                    "configured_repetitions": int(config.get("induction_repetitions", 3)),
                    "per_induced_item": induction_per_item,
                    "missing_target_id_count": induction["missing_target_id_count"],
                    "unknown_target_id_count": induction["unknown_target_id_count"],
                    "missing_metric_count": induction["missing_metric_count"],
                },
                "definition": "Recorded selective-retrieval exposure for items predeclared as induced.",
            },
            {
                "metric_key": "rip.post_retrieval_profile",
                "metric_version": "1.0",
                "value": {
                    "retrieval_metric_key": metric_key,
                    "metric_mode": mode,
                    **post,
                },
                "definition": "Post-induction retrieval profile for the same configured target identifiers.",
            },
            {
                "metric_key": "rip.item_plasticity_delta",
                "metric_version": "1.0",
                "value": {
                    "retrieval_metric_key": metric_key,
                    "metric_mode": mode,
                    "positive_means": "improved_retrieval",
                    "per_item": deltas,
                },
                "definition": "Signed pre/post retrieval change per item using the predeclared metric direction.",
            },
            {
                "metric_key": "rip.role_contrast",
                "metric_version": "1.0",
                "value": {
                    "retrieval_metric_key": metric_key,
                    "metric_mode": mode,
                    "role_mean_signed_improvement": role_means,
                    "contrasts": contrasts,
                },
                "definition": "Difference-in-differences style contrasts between induced, related-control, and unrelated-control item roles.",
            },
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        baseline = next(m["value"] for m in metrics if m["metric_key"] == "rip.baseline_retrieval_profile")
        induction = next(m["value"] for m in metrics if m["metric_key"] == "rip.induction_dose")
        post = next(m["value"] for m in metrics if m["metric_key"] == "rip.post_retrieval_profile")
        contrast = next(m["value"] for m in metrics if m["metric_key"] == "rip.role_contrast")

        claims = [{
            "claim_type": "inference",
            "theory_key": None,
            "statement": (
                "The recorded metrics characterize operational retrieval-state change after selective retrieval only; "
                "they do not establish biological synaptic plasticity, a specific memory mechanism, subjective memory, "
                "consciousness, or qualia."
            ),
            "confidence_label": "weak",
        }]

        missing_items = [
            target_id
            for target_id, item in baseline["per_item"].items()
            if item["mean"] is None or post["per_item"][target_id]["mean"] is None
        ]
        if missing_items:
            claims.append({
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "One or more configured items lack usable pre/post retrieval telemetry "
                    f"({', '.join(sorted(missing_items))}); item-level plasticity for those items remains unresolved."
                ),
                "confidence_label": "not_applicable",
            })

        induction_count = sum(item["count"] for item in induction["per_induced_item"].values())
        if induction_count == 0:
            claims.append({
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "No usable selective-retrieval induction telemetry was recorded for induced items, "
                    "so post-run differences cannot be interpreted as following a measured induction dose."
                ),
                "confidence_label": "not_applicable",
            })

        c = contrast["contrasts"]["induced_minus_unrelated"]
        if c is not None:
            claims.append({
                "claim_type": "inference",
                "theory_key": None,
                "statement": (
                    f"The induced-minus-unrelated signed retrieval-change contrast was {c}. "
                    "This controlled operational contrast does not by itself establish causality or a biological plasticity mechanism."
                ),
                "confidence_label": "weak",
            })

        related = contrast["contrasts"]["related_minus_unrelated"]
        if related is not None:
            claims.append({
                "claim_type": "inference",
                "theory_key": None,
                "statement": (
                    f"The related-control-minus-unrelated signed retrieval-change contrast was {related}. "
                    "A negative value is operationally consistent with relative retrieval suppression, "
                    "not proof of retrieval-induced forgetting or any phenomenal process."
                ),
                "confidence_label": "weak",
            })
        return claims


_DNE = (
    "Does not establish biological synaptic plasticity, a specific causal memory mechanism, "
    "subjective memory, consciousness, or qualia."
)

retrieval_induced_plasticity = register(RetrievalInducedPlasticityProtocol(
    key="retrieval_induced_plasticity",
    version="1.0",
    name="Retrieval-Induced Plasticity",
    description=(
        "Measures pre/post changes in allowlisted retrieval telemetry after selective repeated retrieval "
        "of predeclared opaque target identifiers, with related and unrelated controls."
    ),
    theory_relevance=[],
    required_capabilities=["text_response"],
    stimulus_description=(
        "Randomized baseline probes across configured items, repeated retrieval of induced items, "
        "then randomized post probes across the same items."
    ),
    intervention_sequence=["selective_retrieval_induction"],
    metric_definitions=[
        MetricDefinition(
            key="rip.baseline_retrieval_profile", version="1.0",
            description="Pre-induction retrieval profile.",
            inputs="Allowlisted retrieval.target_id plus one predeclared numeric retrieval metric.",
            procedure="Aggregate numeric baseline readings by opaque target_id and compute per-item means.",
            range="Per-item finite numeric series, mean, count, or null.",
            interpretation="Operational retrieval baseline before selective retrieval.",
            limitations="Depends on telemetry validity and repeated-query comparability.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="rip.induction_dose", version="1.0",
            description="Measured selective-retrieval exposure.",
            inputs="Induction observations with allowlisted retrieval telemetry.",
            procedure="Record numeric retrieval readings and counts for predeclared induced items.",
            range="Per-induced-item finite series and non-negative count.",
            interpretation="Operational dose of selective retrieval actually observed.",
            limitations="Count and retrieval metric do not specify an internal update mechanism.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="rip.post_retrieval_profile", version="1.0",
            description="Post-induction retrieval profile.",
            inputs="Allowlisted retrieval.target_id plus the same predeclared numeric retrieval metric.",
            procedure="Aggregate numeric post readings by opaque target_id and compute per-item means.",
            range="Per-item finite numeric series, mean, count, or null.",
            interpretation="Operational retrieval state after selective retrieval.",
            limitations="Post-run differences may include time, order, or uncontrolled target-state effects.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="rip.item_plasticity_delta", version="1.0",
            description="Signed pre/post retrieval change per item.",
            inputs="Baseline and post per-item means plus predeclared metric direction.",
            procedure="For higher-is-better metrics compute post-baseline; for lower-is-better compute baseline-post.",
            range="Real or null per item; positive means improved retrieval under the declared metric semantics.",
            interpretation="Direction and magnitude of operational retrieval change.",
            limitations="A signed change is descriptive and not proof of a causal plasticity mechanism.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="rip.role_contrast", version="1.0",
            description="Controlled role-level retrieval-change contrasts.",
            inputs="Per-item signed improvements grouped as induced, related_control, or unrelated_control.",
            procedure="Average item deltas within each role and subtract role means pairwise.",
            range="Real or null for each role mean and contrast.",
            interpretation="Separates selective change from common pre/post drift and exposes related-control suppression patterns.",
            limitations="Difference-in-differences style contrast is not causal identification without stronger assignment and confound controls.",
            does_not_establish=_DNE,
        ),
    ],
    limitations=(
        "Operational retrieval protocol only. Requires target-supplied allowlisted retrieval telemetry and opaque item identifiers. "
        "Does not establish biological plasticity, retrieval-induced forgetting as a mechanism, subjective memory, consciousness, or qualia."
    ),
))
