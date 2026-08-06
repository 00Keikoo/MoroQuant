"""Research Reporting Interfaces - Sprint 3.9C-6

Abstract interfaces defining analytics capabilities for quantitative research results.
"""

from abc import ABC, abstractmethod
from typing import List
from ml_service.research.evaluation.models import EvaluationResult
from ml_service.research.reporting.models import ResearchReport


class ResearchAnalytics(ABC):
    """Abstract interface for compiling EvaluationResult arrays into immutable ResearchReport artifacts."""

    @abstractmethod
    def evaluate(self, results: List[EvaluationResult], experiment_id: str) -> ResearchReport:
        """Analyze a list of evaluation results and return an immutable ResearchReport.

        Args:
            results: List of individual evaluation scorecards.
            experiment_id: Unique identifier for the experiment/model configuration.

        Returns:
            ResearchReport: The compiled immutable research analytics scorecard.
        """
        pass
