"""Types for statistical analysis toolkit."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DistributionStats:
    """Distribution statistics."""
    mean: float
    median: float
    std: float
    variance: float
    skew: float
    kurtosis: float


@dataclass
class ReturnStats:
    """Return statistics."""
    cumulative_return: float
    average_return: float
    volatility: float
    rolling_volatility: Optional[List[float]] = None


@dataclass
class RiskStats:
    """Risk statistics."""
    volatility: float
    var_95: float
    cvar_95: float
    max_loss: float
    downside_deviation: float


@dataclass
class QualityStats:
    """Sample quality statistics."""
    sample_size: int
    trade_count: int
    confidence_level: float
    warnings: List[str]


@dataclass
class StatisticalReport:
    """Complete statistical report for an experiment."""
    experiment_id: str
    distribution: DistributionStats
    returns: ReturnStats
    risk: RiskStats
    quality: QualityStats
