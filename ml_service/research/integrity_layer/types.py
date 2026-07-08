"""Types for research integrity validation."""

from dataclasses import dataclass
from typing import List
from enum import Enum


class RiskLevel(Enum):
    """Risk level for research integrity."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class BiasFlag:
    """Research bias detection flag."""
    bias_type: str
    severity: str
    description: str
    recommendation: str


@dataclass
class IntegrityReport:
    """Complete integrity validation report."""
    snapshot_valid: bool
    replay_valid: bool
    bias_flags: List[BiasFlag]
    risk_level: RiskLevel
    recommendations: List[str]

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'snapshot_valid': self.snapshot_valid,
            'replay_valid': self.replay_valid,
            'bias_flags': [
                {
                    'bias_type': flag.bias_type,
                    'severity': flag.severity,
                    'description': flag.description,
                    'recommendation': flag.recommendation
                }
                for flag in self.bias_flags
            ],
            'risk_level': self.risk_level.value,
            'recommendations': self.recommendations
        }
