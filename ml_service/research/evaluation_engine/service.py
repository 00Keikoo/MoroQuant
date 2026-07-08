"""Service layer for evaluation engine."""

from ml_service.research.experiment_engine.types import ExperimentResult
from ml_service.research.evaluation_engine.engine import evaluate_experiment
from ml_service.research.evaluation_engine.types import EvaluationResult


class EvaluationService:
    """Service for evaluating experiment results."""

    def evaluate(self, experiment_result: ExperimentResult) -> EvaluationResult:
        """Evaluate experiment and rank strategies.

        Args:
            experiment_result: Complete experiment result

        Returns:
            EvaluationResult with ranked strategies
        """
        return evaluate_experiment(experiment_result)

    def get_top_strategy(self, evaluation_result: EvaluationResult) -> str:
        """Get the best performing strategy ID.

        Args:
            evaluation_result: Evaluation result

        Returns:
            Best strategy config_id
        """
        return evaluation_result.best_strategy_id

    def get_strategy_score(
        self,
        evaluation_result: EvaluationResult,
        config_id: str
    ) -> float:
        """Get final score for a specific strategy.

        Args:
            evaluation_result: Evaluation result
            config_id: Strategy config ID

        Returns:
            Final score for the strategy, or 0.0 if not found
        """
        for score in evaluation_result.strategy_scores:
            if score.config_id == config_id:
                return score.final_score
        return 0.0
