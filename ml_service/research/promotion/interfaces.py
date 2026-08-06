"""Research Promotion Interfaces - Sprint 3.9D-2

Abstract interface for promotion decision engine.
"""

from abc import ABC, abstractmethod
from ml_service.research.benchmark.models import BenchmarkResult
from ml_service.research.promotion.models import PromotionDecision


class PromotionEngine(ABC):
    """Abstract interface defining promotion evaluation logic."""

    @abstractmethod
    def evaluate(
        self,
        candidate_report: BenchmarkResult,
        current_report: BenchmarkResult
    ) -> PromotionDecision:
        """Evaluate promotion decision by comparing candidate vs current benchmark results.

        Args:
            candidate_report: Benchmark result for the candidate model
            current_report: Benchmark result for the current production model

        Returns:
            PromotionDecision: The immutable promotion recommendation
        """
        pass
