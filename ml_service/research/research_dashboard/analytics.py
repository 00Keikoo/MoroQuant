"""Analytics layer for research dashboard comparisons and aggregations."""

from typing import List, Dict, Any

from ml_service.research.research_dashboard.repository import ResearchDashboardRepository
from ml_service.research.research_dashboard.dashboard_types import ComparisonResult


class ResearchAnalytics:
    """Stateless analytics computations for experiment comparison."""

    def __init__(self, repository: ResearchDashboardRepository):
        self.repository = repository

    def compare_experiments(self, experiment_ids: List[str]) -> ComparisonResult:
        """Generate side-by-side comparison matrix of metrics and parameters."""
        if len(experiment_ids) < 2:
            raise ValueError("At least 2 experiments required for comparison")

        metrics_comparison: Dict[str, Dict[str, float]] = {}
        parameter_differentials: Dict[str, Dict[str, Any]] = {}

        for exp_id in experiment_ids:
            results = self.repository.get_experiment_results(exp_id)
            configs = self.repository.get_experiment_configs(exp_id)

            if results:
                best_result = max(results, key=lambda r: r['sharpe'])

                if 'sharpe_ratio' not in metrics_comparison:
                    metrics_comparison['sharpe_ratio'] = {}
                metrics_comparison['sharpe_ratio'][exp_id] = best_result['sharpe']

                if 'max_drawdown' not in metrics_comparison:
                    metrics_comparison['max_drawdown'] = {}
                metrics_comparison['max_drawdown'][exp_id] = best_result['max_drawdown']

                if 'total_return' not in metrics_comparison:
                    metrics_comparison['total_return'] = {}
                metrics_comparison['total_return'][exp_id] = best_result['pnl']

            if configs:
                first_config = configs[0]

                if 'threshold_long' not in parameter_differentials:
                    parameter_differentials['threshold_long'] = {}
                parameter_differentials['threshold_long'][exp_id] = first_config['threshold_long']

                if 'threshold_short' not in parameter_differentials:
                    parameter_differentials['threshold_short'] = {}
                parameter_differentials['threshold_short'][exp_id] = first_config['threshold_short']

        return ComparisonResult(
            compared_ids=experiment_ids,
            metrics_comparison=metrics_comparison,
            parameter_differentials=parameter_differentials
        )

    def rank_by_metric(self, experiment_ids: List[str], metric: str) -> List[str]:
        """Rank experiments by a specific metric."""
        scores = []

        for exp_id in experiment_ids:
            results = self.repository.get_experiment_results(exp_id)
            if results:
                best_result = max(results, key=lambda r: r.get('sharpe', 0.0))
                metric_value = best_result.get(metric, 0.0)
                scores.append((exp_id, metric_value))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [exp_id for exp_id, _ in scores]
