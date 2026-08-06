"""Research Benchmark Models - Sprint 3.9D-1

Immutable domain models representing evaluation benchmark results.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, Any, Tuple


@dataclass(frozen=True)
class BenchmarkResult:
    """Immutable benchmark result comparing multiple quant research experiments.

    Adheres to ADR-024 compliance with strict immutability and deterministic serialization.
    """
    benchmark_id: str
    compared_experiments: Tuple[str, ...]
    ranking: Tuple[str, ...]
    winner: str
    scores: Tuple[Tuple[str, float], ...]
    metrics: Tuple[Tuple[str, float], ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.benchmark_id:
            raise ValueError("benchmark_id cannot be empty")
        # Ensure collection types are tuples
        if not isinstance(self.compared_experiments, tuple):
            object.__setattr__(self, 'compared_experiments', tuple(self.compared_experiments))
        if not isinstance(self.ranking, tuple):
            object.__setattr__(self, 'ranking', tuple(self.ranking))
        if not isinstance(self.scores, tuple):
            object.__setattr__(self, 'scores', tuple(self.scores))
        if not isinstance(self.metrics, tuple):
            object.__setattr__(self, 'metrics', tuple(self.metrics))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the benchmark result into a dictionary with sorted collections for determinism."""
        sorted_scores = sorted(self.scores, key=lambda x: x[0])
        sorted_metrics = sorted(self.metrics, key=lambda x: x[0])
        return {
            "benchmark_id": self.benchmark_id,
            "compared_experiments": list(self.compared_experiments),
            "ranking": list(self.ranking),
            "winner": self.winner,
            "scores": [list(x) for x in sorted_scores],
            "metrics": [list(x) for x in sorted_metrics],
        }

    def to_json(self) -> str:
        """Deterministic JSON serialization of the benchmark result."""
        return json.dumps(self.to_dict(), sort_keys=True)
