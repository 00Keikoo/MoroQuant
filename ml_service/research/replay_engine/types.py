"""Types for replay engine."""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ReplayResult:
    """Deterministic replay result with decision parity tracking."""
    snapshot_id: str
    decisions: List[Dict[str, Any]]
    signal_reproduction_rate: float
    execution_alignment_rate: float
    divergence_count: int
    notes: List[str]
    consistency_score: float
    divergence_score: float
    execution_parity_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert replay result to dictionary for JSON serialization."""
        return {
            'snapshot_id': self.snapshot_id,
            'decisions': self.decisions,
            'signal_reproduction_rate': self.signal_reproduction_rate,
            'execution_alignment_rate': self.execution_alignment_rate,
            'divergence_count': self.divergence_count,
            'notes': self.notes,
            'consistency_score': self.consistency_score,
            'divergence_score': self.divergence_score,
            'execution_parity_rate': self.execution_parity_rate
        }


@dataclass
class DecisionParityResult:
    """Enhanced replay result with full decision parity tracking."""
    snapshot_id: str
    decisions: List[Dict[str, Any]]
    signal_reproduction_rate: float
    execution_alignment_rate: float
    divergence_count: int
    notes: List[str]
    consistency_score: float
    divergence_score: float
    decision_parity_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision parity result to dictionary for JSON serialization."""
        return {
            'snapshot_id': self.snapshot_id,
            'decisions': self.decisions,
            'signal_reproduction_rate': self.signal_reproduction_rate,
            'execution_alignment_rate': self.execution_alignment_rate,
            'divergence_count': self.divergence_count,
            'notes': self.notes,
            'consistency_score': self.consistency_score,
            'divergence_score': self.divergence_score,
            'decision_parity_rate': self.decision_parity_rate
        }
