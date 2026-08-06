"""Research Benchmark Implementation - Sprint 3.9D-1

Coordinates scores and sorts research models to generate a BenchmarkResult.
"""

from typing import List, Tuple
from ml_service.research.reporting.models import ResearchReport
from ml_service.research.benchmark.interfaces import ResearchBenchmark
from ml_service.research.benchmark.models import BenchmarkResult
from ml_service.research.benchmark.scoring import calculate_absolute_score


class DefaultResearchBenchmark(ResearchBenchmark):
    """Default implementation of ResearchBenchmark executing weighted composite scoring.

    Calculates scores and ranks reports deterministically.
    """

    def __init__(self, benchmark_id: str = "default_benchmark"):
        self.benchmark_id = benchmark_id

    def compare(self, reports: List[ResearchReport]) -> BenchmarkResult:
        """Compare multiple ResearchReports and rank them by composite score.

        Args:
            reports: List of ResearchReports to compare.

        Returns:
            BenchmarkResult: The compiled ranked comparison scorecard.
        """
        if not reports:
            raise ValueError("Cannot benchmark empty reports list")

        # 1. Compute scores for all reports
        scores_list = []
        for r in reports:
            score = calculate_absolute_score(r)
            scores_list.append((r.experiment_id, score))

        scores_dict = dict(scores_list)

        # 2. Determine ranking (sort descending by score, resolve ties alphabetically by experiment_id)
        sorted_reports = sorted(
            reports,
            key=lambda r: (-scores_dict[r.experiment_id], r.experiment_id)
        )

        ranking = tuple(r.experiment_id for r in sorted_reports)
        compared_experiments = tuple(r.experiment_id for r in reports)
        winner = ranking[0]

        # Convert scores to tuple representation
        scores = tuple(scores_list)

        # Extra summary metrics
        metrics = (
            ("average_cohort_score", sum(scores_dict.values()) / len(reports)),
            ("highest_score", scores_dict[winner]),
        )

        return BenchmarkResult(
            benchmark_id=self.benchmark_id,
            compared_experiments=compared_experiments,
            ranking=ranking,
            winner=winner,
            scores=scores,
            metrics=metrics
        )
