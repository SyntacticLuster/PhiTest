"""IIT / integrated information extension point.

V1 does not implement canonical IIT Φ. This module defines the extension
protocol for future mathematically specified implementations.

IIT proposes formal relationships involving integrated information (Φ).
Different formulations (IIT 2.0, 3.0, 4.0) use different mathematical
definitions. Calculating Φ requires a formal causal model of the system's
mechanism, which is not available for opaque language systems.

ΦTest V1 therefore does not claim to calculate canonical IIT Φ.
Integration-related V1 metrics are operational proxies and are named as such.
"""
from typing import Protocol, runtime_checkable
from phitest.domain.models import MetricResult


@runtime_checkable
class IntegratedInformationMetric(Protocol):
    """Extension point for future IIT Φ implementations."""
    metric_key: str
    version: str

    def compute(self, system_model: object, state: object) -> MetricResult:
        """Compute an integrated information metric given a system model and state."""
        ...
