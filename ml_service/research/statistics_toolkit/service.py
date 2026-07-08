"""Statistical analysis service."""

from typing import List, Optional

from ml_service.research.statistics_toolkit.types import StatisticalReport
from ml_service.research.statistics_toolkit.statistics import (
    compute_distribution_stats,
    compute_return_stats
)
from ml_service.research.statistics_toolkit.risk import compute_risk_stats
from ml_service.research.statistics_toolkit.quality import compute_quality_stats


class StatisticsService:
    """Pure statistical analysis service."""

    def analyze(
        self,
        experiment_id: str,
        returns: List[float],
        trade_count: int,
        rolling_window: Optional[int] = None
    ) -> StatisticalReport:
        """Generate comprehensive statistical report.

        Args:
            experiment_id: Experiment identifier
            returns: List of period returns
            trade_count: Number of trades executed
            rolling_window: Optional window size for rolling statistics

        Returns:
            Complete statistical report
        """
        if not returns:
            raise ValueError("Returns list cannot be empty")

        distribution = compute_distribution_stats(returns)
        return_stats = compute_return_stats(returns, rolling_window)
        risk = compute_risk_stats(returns)
        quality = compute_quality_stats(returns, trade_count)

        return StatisticalReport(
            experiment_id=experiment_id,
            distribution=distribution,
            returns=return_stats,
            risk=risk,
            quality=quality
        )
