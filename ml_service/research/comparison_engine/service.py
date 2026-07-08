"""Statistical comparison service."""

from typing import List, Optional

from .types import ComparisonReport
from .comparison import calculate_metrics_difference
from .hypothesis import run_hypothesis_tests
from .bootstrap import run_bootstrap_analysis


class ComparisonEngine:
    """Engine for statistical comparison of experiments."""

    def compare_experiments(
        self,
        experiment_a_id: str,
        experiment_b_id: str,
        returns_a: List[float],
        returns_b: List[float],
        sharpe_a: float,
        sharpe_b: float,
        max_dd_a: float,
        max_dd_b: float,
        win_rate_a: float,
        win_rate_b: float,
        alpha: float = 0.05,
        bootstrap_iterations: int = 10000,
        random_seed: Optional[int] = None
    ) -> ComparisonReport:
        """Compare two experiments statistically.

        Args:
            experiment_a_id: ID of first experiment
            experiment_b_id: ID of second experiment
            returns_a: Return series from experiment A
            returns_b: Return series from experiment B
            sharpe_a: Sharpe ratio of experiment A
            sharpe_b: Sharpe ratio of experiment B
            max_dd_a: Max drawdown of experiment A
            max_dd_b: Max drawdown of experiment B
            win_rate_a: Win rate of experiment A
            win_rate_b: Win rate of experiment B
            alpha: Significance level for hypothesis tests
            bootstrap_iterations: Number of bootstrap iterations
            random_seed: Random seed for reproducibility

        Returns:
            ComparisonReport with statistical analysis
        """

        metrics_diff = calculate_metrics_difference(
            returns_a=returns_a,
            returns_b=returns_b,
            sharpe_a=sharpe_a,
            sharpe_b=sharpe_b,
            max_dd_a=max_dd_a,
            max_dd_b=max_dd_b,
            win_rate_a=win_rate_a,
            win_rate_b=win_rate_b
        )

        hypothesis_result = run_hypothesis_tests(
            returns_a=returns_a,
            returns_b=returns_b,
            alpha=alpha
        )

        bootstrap_result = run_bootstrap_analysis(
            returns_a=returns_a,
            returns_b=returns_b,
            n_iterations=bootstrap_iterations,
            random_seed=random_seed
        )

        verdict = self._generate_verdict(
            metrics_diff=metrics_diff,
            hypothesis_result=hypothesis_result,
            bootstrap_result=bootstrap_result
        )

        return ComparisonReport(
            experiment_a_id=experiment_a_id,
            experiment_b_id=experiment_b_id,
            metrics_difference=metrics_diff,
            hypothesis_test=hypothesis_result,
            bootstrap_result=bootstrap_result,
            verdict=verdict
        )

    def _generate_verdict(
        self,
        metrics_diff,
        hypothesis_result,
        bootstrap_result
    ) -> str:
        """Generate human-readable verdict from statistical results."""

        if bootstrap_result.probability_a_beats_b > 0.95:
            strength = "strongly"
        elif bootstrap_result.probability_a_beats_b > 0.8:
            strength = "likely"
        elif bootstrap_result.probability_a_beats_b > 0.6:
            strength = "marginally"
        elif bootstrap_result.probability_a_beats_b < 0.05:
            strength = "strongly"
            direction = "worse"
        elif bootstrap_result.probability_a_beats_b < 0.2:
            strength = "likely"
            direction = "worse"
        elif bootstrap_result.probability_a_beats_b < 0.4:
            strength = "marginally"
            direction = "worse"
        else:
            return "No statistically significant difference detected"

        if bootstrap_result.probability_a_beats_b > 0.5:
            direction = "better"
        else:
            direction = "worse"

        statistical_support = ""
        if hypothesis_result.t_test_significant and hypothesis_result.mann_whitney_significant:
            statistical_support = " (both parametric and non-parametric tests significant)"
        elif hypothesis_result.t_test_significant:
            statistical_support = " (parametric test significant)"
        elif hypothesis_result.mann_whitney_significant:
            statistical_support = " (non-parametric test significant)"
        else:
            statistical_support = " (hypothesis tests not significant)"

        return f"Experiment A is {strength} {direction} than Experiment B{statistical_support}"
