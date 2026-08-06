"""Research Promotion Engine - Sprint 3.9D-2

Default implementation of promotion decision engine.
Pure functional, deterministic, no database or execution dependencies.
"""

from ml_service.research.benchmark.models import BenchmarkResult
from ml_service.research.promotion.interfaces import PromotionEngine
from ml_service.research.promotion.models import PromotionDecision
from ml_service.research.promotion.rules import PromotionCriteria, evaluate_promotion_rules


class DefaultPromotionEngine(PromotionEngine):
    """Default promotion engine implementation.

    Responsibilities:
    - Consume benchmark/report outputs
    - Apply PromotionCriteria
    - Return PromotionDecision

    Must not:
    - Modify registry
    - Persist state
    - Deploy models
    """

    def __init__(self, criteria: PromotionCriteria = None):
        """Initialize promotion engine with optional custom criteria.

        Args:
            criteria: Promotion criteria. Defaults to PromotionCriteria() if not provided.
        """
        self.criteria = criteria or PromotionCriteria()

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
        candidate_score = self._extract_score(candidate_report)
        current_score = self._extract_score(current_report)
        score_delta = candidate_score - current_score

        metrics = candidate_report.metrics

        decision, reason = evaluate_promotion_rules(
            candidate_score=candidate_score,
            current_score=current_score,
            metrics=metrics,
            criteria=self.criteria
        )

        return PromotionDecision(
            model_id=candidate_report.winner,
            decision=decision,
            reason=reason,
            candidate_score=candidate_score,
            current_score=current_score,
            score_delta=score_delta,
            metrics=metrics
        )

    def _extract_score(self, report: BenchmarkResult) -> float:
        """Extract primary score from benchmark result.

        Args:
            report: BenchmarkResult containing scores

        Returns:
            Primary score for the winning model
        """
        scores_dict = dict(report.scores)
        if report.winner not in scores_dict:
            raise ValueError(f"Winner {report.winner} not found in scores: {scores_dict}")
        return scores_dict[report.winner]
