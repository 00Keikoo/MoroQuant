"""Pure risk metric calculations."""

import numpy as np
from typing import List

from ml_service.research.statistics_toolkit.types import RiskStats


def compute_var(returns: List[float], confidence: float = 0.95) -> float:
    """Compute Value at Risk at given confidence level."""
    arr = np.array(returns)
    return float(np.percentile(arr, (1 - confidence) * 100))


def compute_cvar(returns: List[float], confidence: float = 0.95) -> float:
    """Compute Conditional Value at Risk (Expected Shortfall)."""
    arr = np.array(returns)
    var = compute_var(returns, confidence)
    return float(np.mean(arr[arr <= var]))


def compute_downside_deviation(returns: List[float], target: float = 0.0) -> float:
    """Compute downside deviation relative to target."""
    arr = np.array(returns)
    downside = arr[arr < target] - target
    return float(np.sqrt(np.mean(downside ** 2))) if len(downside) > 0 else 0.0


def compute_risk_stats(returns: List[float]) -> RiskStats:
    """Compute comprehensive risk statistics."""
    arr = np.array(returns)

    return RiskStats(
        volatility=float(np.std(arr, ddof=1)),
        var_95=compute_var(returns, 0.95),
        cvar_95=compute_cvar(returns, 0.95),
        max_loss=float(np.min(arr)),
        downside_deviation=compute_downside_deviation(returns)
    )
