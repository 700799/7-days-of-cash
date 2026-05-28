"""Strategy agent registry.

Each agent scores a stock 0-100 based on its specialty. The orchestrator
aggregates scores to produce a composite ranking, but every agent's score
is also displayed individually so traders can pick their style.
"""

from .base import AgentResult, BaseAgent
from .breakout import BreakoutAgent
from .mean_reversion import MeanReversionAgent
from .momentum import MomentumAgent
from .relative_strength import RelativeStrengthAgent
from .volume_surge import VolumeSurgeAgent

AGENTS = {
    "momentum": MomentumAgent,
    "breakout": BreakoutAgent,
    "volume_surge": VolumeSurgeAgent,
    "relative_strength": RelativeStrengthAgent,
    "mean_reversion": MeanReversionAgent,
}


def build_agents(names=None, **kwargs):
    if names is None:
        names = list(AGENTS.keys())
    return [AGENTS[n](**kwargs) for n in names if n in AGENTS]


__all__ = [
    "BaseAgent",
    "AgentResult",
    "AGENTS",
    "build_agents",
    "MomentumAgent",
    "BreakoutAgent",
    "VolumeSurgeAgent",
    "RelativeStrengthAgent",
    "MeanReversionAgent",
]
