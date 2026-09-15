"""M3 Opportunity AI: structured analysis over post-filter items.

Public surface for the analysis layer. The provider is replaceable and the
default is deterministic and offline so the pipeline runs without any API key.
"""

from __future__ import annotations

from innovation_radar.analysis.calibration import (
    CalibrationResult,
    calibrate,
)
from innovation_radar.analysis.engine import AnalysisReport, analyze_items
from innovation_radar.analysis.models import (
    AnalyzedItem,
    OpportunityAnalysis,
    Recommendation,
    SignalType,
    Traction,
)
from innovation_radar.analysis.provider import (
    HeuristicProvider,
    OpportunityProvider,
    ProviderContext,
)


def build_provider(name: str) -> OpportunityProvider:
    """Return a provider instance for a configured provider name.

    New backends (a real LLM provider, for example) register here without
    changing the engine or the CLI, keeping the vendor out of the architecture.
    """

    if name == HeuristicProvider.name:
        return HeuristicProvider()
    raise ValueError(f"unknown analysis provider: {name!r}")


__all__ = [
    "AnalysisReport",
    "analyze_items",
    "calibrate",
    "CalibrationResult",
    "AnalyzedItem",
    "OpportunityAnalysis",
    "Recommendation",
    "SignalType",
    "Traction",
    "HeuristicProvider",
    "OpportunityProvider",
    "ProviderContext",
    "build_provider",
]
