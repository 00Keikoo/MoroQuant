"""Research Benchmark Interfaces - Sprint 3.9D-1

Abstract interface for comparing quantitative research reports.
"""

from abc import ABC, abstractmethod
from typing import List
from ml_service.research.reporting.models import ResearchReport
from ml_service.research.benchmark.models import BenchmarkResult


class ResearchBenchmark(ABC):
    """Abstract interface defining comparisons across multiple ResearchReports."""

    @abstractmethod
    def compare(self, reports: List[ResearchReport]) -> BenchmarkResult:
        """Compare a list of quantitative research reports and generate a BenchmarkResult.

        Args:
            reports: List of ResearchReports to benchmark.

        Returns:
            BenchmarkResult: The compiled benchmark comparison.
        """
        pass
