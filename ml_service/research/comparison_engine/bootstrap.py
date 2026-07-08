"""Bootstrap analysis for experiment comparison."""

from typing import List, Optional
import numpy as np

from .types import BootstrapResult


def run_bootstrap_analysis(
    returns_a: List[float],
    returns_b: List[float],
    n_iterations: int = 10000,
    confidence_level: float = 0.95,
    random_seed: Optional[int] = None
) -> BootstrapResult:
    """Run bootstrap simulation to estimate probability A beats B.

    Args:
        returns_a: Historical returns from experiment A
        returns_b: Historical returns from experiment B
        n_iterations: Number of bootstrap iterations
        confidence_level: Confidence level for interval (default 0.95)
        random_seed: Random seed for reproducibility

    Returns:
        BootstrapResult with confidence interval and win probability
    """

    if random_seed is not None:
        np.random.seed(random_seed)

    arr_a = np.array(returns_a)
    arr_b = np.array(returns_b)

    n_a = len(arr_a)
    n_b = len(arr_b)

    differences = []

    for _ in range(n_iterations):
        sample_a = np.random.choice(arr_a, size=n_a, replace=True)
        sample_b = np.random.choice(arr_b, size=n_b, replace=True)

        mean_a = np.mean(sample_a)
        mean_b = np.mean(sample_b)

        differences.append(mean_a - mean_b)

    differences_arr = np.array(differences)

    alpha = 1 - confidence_level
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    ci_lower = float(np.percentile(differences_arr, lower_percentile))
    ci_upper = float(np.percentile(differences_arr, upper_percentile))

    prob_a_beats_b = float(np.mean(differences_arr > 0))

    return BootstrapResult(
        confidence_interval_lower=ci_lower,
        confidence_interval_upper=ci_upper,
        probability_a_beats_b=prob_a_beats_b,
        n_iterations=n_iterations
    )
