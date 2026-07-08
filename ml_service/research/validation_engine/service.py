"""Research validation service."""

from typing import List, Callable

from .types import (
    SplitMetrics,
    ValidationReport,
    TimeSeriesSplit,
    WalkForwardWindow
)
from .splitter import create_time_series_split, filter_by_period
from .walk_forward import create_walk_forward_windows, evaluate_walk_forward
from .overfit import calculate_overfit_score
from .stability import calculate_stability_score


class ValidationEngine:
    """Validation layer for experiment generalization testing."""

    def __init__(
        self,
        overfit_threshold: float = 0.3,
        stability_threshold: float = 0.5
    ):
        self.overfit_threshold = overfit_threshold
        self.stability_threshold = stability_threshold

    def validate_experiment(
        self,
        experiment_id: str,
        timestamps: List[str],
        evaluate_fn: Callable[[str, str], SplitMetrics],
        train_ratio: float = 0.6,
        validation_ratio: float = 0.2,
        test_ratio: float = 0.2
    ) -> ValidationReport:
        """
        Validate experiment results for generalization.

        Args:
            experiment_id: Experiment identifier
            timestamps: List of timestamp strings
            evaluate_fn: Function that evaluates metrics for a time period
            train_ratio: Training set ratio
            validation_ratio: Validation set ratio
            test_ratio: Test set ratio

        Returns:
            ValidationReport with all validation metrics
        """
        split = create_time_series_split(
            timestamps,
            train_ratio,
            validation_ratio,
            test_ratio
        )

        train_metrics = evaluate_fn(split.train_start, split.train_end)
        validation_metrics = evaluate_fn(split.validation_start, split.validation_end)
        test_metrics = evaluate_fn(split.test_start, split.test_end)

        overfit_analysis = calculate_overfit_score(
            train_metrics,
            validation_metrics,
            self.overfit_threshold
        )

        warnings = []
        if overfit_analysis.is_overfit:
            warnings.append(
                f"Overfitting detected: {overfit_analysis.overfit_score:.3f} > {self.overfit_threshold}"
            )

        final_verdict = self._determine_verdict(overfit_analysis, None, warnings)

        return ValidationReport(
            experiment_id=experiment_id,
            train_metrics=train_metrics,
            validation_metrics=validation_metrics,
            test_metrics=test_metrics,
            overfit_score=overfit_analysis.overfit_score,
            stability_score=0.0,
            warnings=warnings,
            final_verdict=final_verdict,
            overfit_analysis=overfit_analysis
        )

    def validate_with_walk_forward(
        self,
        experiment_id: str,
        timestamps: List[str],
        evaluate_fn: Callable[[str, str], SplitMetrics],
        train_window_days: int = 90,
        test_window_days: int = 30,
        step_days: int = 30,
        train_ratio: float = 0.6,
        validation_ratio: float = 0.2,
        test_ratio: float = 0.2
    ) -> ValidationReport:
        """
        Validate with both time series split and walk-forward analysis.

        Args:
            experiment_id: Experiment identifier
            timestamps: List of timestamp strings
            evaluate_fn: Function that evaluates metrics for a time period
            train_window_days: Training window size in days
            test_window_days: Test window size in days
            step_days: Step size for walk-forward
            train_ratio: Training set ratio for initial split
            validation_ratio: Validation set ratio for initial split
            test_ratio: Test set ratio for initial split

        Returns:
            ValidationReport with all validation metrics including stability
        """
        split = create_time_series_split(
            timestamps,
            train_ratio,
            validation_ratio,
            test_ratio
        )

        train_metrics = evaluate_fn(split.train_start, split.train_end)
        validation_metrics = evaluate_fn(split.validation_start, split.validation_end)
        test_metrics = evaluate_fn(split.test_start, split.test_end)

        windows = create_walk_forward_windows(
            timestamps,
            train_window_days,
            test_window_days,
            step_days
        )

        evaluated_windows = evaluate_walk_forward(windows, evaluate_fn)

        overfit_analysis = calculate_overfit_score(
            train_metrics,
            validation_metrics,
            self.overfit_threshold
        )

        stability_analysis = calculate_stability_score(
            evaluated_windows,
            self.stability_threshold
        )

        warnings = []
        if overfit_analysis.is_overfit:
            warnings.append(
                f"Overfitting detected: {overfit_analysis.overfit_score:.3f} > {self.overfit_threshold}"
            )
        if not stability_analysis.is_stable:
            warnings.append(
                f"Low stability: {stability_analysis.stability_score:.3f} < {self.stability_threshold}"
            )

        final_verdict = self._determine_verdict(
            overfit_analysis,
            stability_analysis,
            warnings
        )

        return ValidationReport(
            experiment_id=experiment_id,
            train_metrics=train_metrics,
            validation_metrics=validation_metrics,
            test_metrics=test_metrics,
            overfit_score=overfit_analysis.overfit_score,
            stability_score=stability_analysis.stability_score,
            warnings=warnings,
            final_verdict=final_verdict,
            overfit_analysis=overfit_analysis,
            stability_analysis=stability_analysis,
            walk_forward_windows=evaluated_windows
        )

    def _determine_verdict(
        self,
        overfit_analysis,
        stability_analysis,
        warnings: List[str]
    ) -> str:
        """Determine final validation verdict."""
        if not warnings:
            return "PASS: Results likely generalize"

        if overfit_analysis.is_overfit and stability_analysis and not stability_analysis.is_stable:
            return "FAIL: Overfitting and instability detected"

        if overfit_analysis.is_overfit:
            return "FAIL: Overfitting detected"

        if stability_analysis and not stability_analysis.is_stable:
            return "WARN: Low stability across periods"

        return "WARN: Some concerns detected"
