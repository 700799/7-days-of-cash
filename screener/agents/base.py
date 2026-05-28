"""Base class for strategy agents.

An agent receives a metrics dict for a single stock plus optional benchmark
context and returns an AgentResult with a 0-100 score, conviction tier, and
explanatory reasons.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentResult:
    name: str
    score: float  # 0-100
    tier: str  # "strong" | "moderate" | "weak" | "skip"
    reasons: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "score": round(self.score, 1),
            "tier": self.tier,
            "reasons": self.reasons,
            "flags": self.flags,
        }


class BaseAgent(ABC):
    """Abstract strategy agent. Subclass and override `evaluate`."""

    name: str = "base"
    description: str = "Abstract base agent"

    def __init__(self, **config):
        self.config = config

    @abstractmethod
    def evaluate(
        self, metrics: Dict[str, Any], context: Dict[str, Any] | None = None
    ) -> AgentResult: ...

    @staticmethod
    def tier_for(score: float) -> str:
        if score >= 75:
            return "strong"
        if score >= 55:
            return "moderate"
        if score >= 35:
            return "weak"
        return "skip"

    @staticmethod
    def clip(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, v))
