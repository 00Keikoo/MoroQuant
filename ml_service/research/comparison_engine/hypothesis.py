"""Hypothesis testing for experiment comparison."""

from typing import List
import numpy as np
from scipy import stats

from .types import HypothesisTestResult


def run_hypothesis_tests(
    returns_a: List[float],
    returns_b: List[float],
    alpha: float = 0.05
) -> HypothesisTestResult:
    """Run statistical hypothesis tests to compare two experiments.

    Args:
        returns_a: Returns from experiment A
        returns_b: Returns from experiment B
        alpha: Significance level (default 0.05)

    Returns:
        HypothesisTestResult with p-values and significance flags
    """

    arr_a = np.array(returns_a)
    arr_b = np.array(returns_b)

    t_stat, t_pvalue = stats.ttest_ind(arr_a, arr_b)

    u_stat, mw_pvalue = stats.mannwhitneyu(
        arr_a,
        arr_b,
        alternative='two-sided'
    )

    return HypothesisTestResult(
        t_test_pvalue=float(t_pvalue),
        mann_whitney_pvalue=float(mw_pvalue),
        t_test_significant=t_pvalue < alpha,
        mann_whitney_significant=mw_pvalue < alpha,
        alpha=alpha
    )
