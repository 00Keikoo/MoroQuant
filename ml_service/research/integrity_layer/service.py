"""Research integrity validation service."""

from typing import Dict, Any, Optional, List

from .types import IntegrityReport, RiskLevel, BiasFlag
from .validators import (
    SnapshotIntegrityValidator,
    ReplayIntegrityValidator,
    ResearchBiasDetector
)


class IntegrityService:
    """Pure validation service for research integrity."""

    def __init__(self):
        self.snapshot_validator = SnapshotIntegrityValidator()
        self.replay_validator = ReplayIntegrityValidator()
        self.bias_detector = ResearchBiasDetector()

    def validate_snapshot(
        self,
        snapshot: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """Validate snapshot integrity.

        Args:
            snapshot: Snapshot data to validate

        Returns:
            (is_valid, list_of_issues)
        """
        return self.snapshot_validator.validate(snapshot)

    def validate_replay_determinism(
        self,
        replay_result1: Dict[str, Any],
        replay_result2: Dict[str, Any]
    ) -> tuple[bool, float, List[str]]:
        """Validate replay determinism.

        Args:
            replay_result1: First replay result
            replay_result2: Second replay result

        Returns:
            (is_deterministic, reproducibility_score, issues)
        """
        return self.replay_validator.validate_determinism(
            replay_result1,
            replay_result2
        )

    def generate_integrity_report(
        self,
        snapshot: Dict[str, Any],
        replay_result: Optional[Dict[str, Any]] = None,
        replay_result_2: Optional[Dict[str, Any]] = None,
        evaluation_result: Optional[Dict[str, Any]] = None
    ) -> IntegrityReport:
        """Generate complete integrity report.

        Args:
            snapshot: Snapshot data
            replay_result: First replay result (optional)
            replay_result_2: Second replay result for determinism check (optional)
            evaluation_result: Evaluation result (optional)

        Returns:
            Complete integrity report
        """
        # Validate snapshot
        snapshot_valid, snapshot_issues = self.snapshot_validator.validate(snapshot)

        # Validate replay if provided
        replay_valid = True
        replay_issues = []
        reproducibility_score = 1.0

        if replay_result and replay_result_2:
            replay_valid, reproducibility_score, replay_issues = \
                self.replay_validator.validate_determinism(replay_result, replay_result_2)
        elif replay_result:
            # Check for live DB dependency
            replay_notes = replay_result.get('notes', [])
            no_live_db, db_issues = self.replay_validator.check_no_live_db_dependency(replay_notes)
            replay_valid = no_live_db
            replay_issues = db_issues

        # Detect biases
        bias_flags = self.bias_detector.detect_biases(snapshot, evaluation_result)

        # Determine risk level
        risk_level = self._determine_risk_level(
            snapshot_valid,
            replay_valid,
            bias_flags,
            reproducibility_score
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            snapshot_valid,
            snapshot_issues,
            replay_valid,
            replay_issues,
            bias_flags,
            reproducibility_score
        )

        return IntegrityReport(
            snapshot_valid=snapshot_valid,
            replay_valid=replay_valid,
            bias_flags=bias_flags,
            risk_level=risk_level,
            recommendations=recommendations
        )

    def _determine_risk_level(
        self,
        snapshot_valid: bool,
        replay_valid: bool,
        bias_flags: List[BiasFlag],
        reproducibility_score: float
    ) -> RiskLevel:
        """Determine overall risk level."""
        if not snapshot_valid or not replay_valid:
            return RiskLevel.HIGH

        high_severity_biases = sum(1 for flag in bias_flags if flag.severity == 'HIGH')
        if high_severity_biases > 0:
            return RiskLevel.HIGH

        if reproducibility_score < 0.95:
            return RiskLevel.HIGH

        medium_severity_biases = sum(1 for flag in bias_flags if flag.severity == 'MEDIUM')
        if medium_severity_biases > 0:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _generate_recommendations(
        self,
        snapshot_valid: bool,
        snapshot_issues: List[str],
        replay_valid: bool,
        replay_issues: List[str],
        bias_flags: List[BiasFlag],
        reproducibility_score: float
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if not snapshot_valid:
            recommendations.append(f"Fix snapshot issues: {', '.join(snapshot_issues)}")

        if not replay_valid:
            recommendations.append(f"Fix replay issues: {', '.join(replay_issues)}")

        if reproducibility_score < 1.0:
            recommendations.append(
                f"Improve reproducibility (current: {reproducibility_score:.2%})"
            )

        for flag in bias_flags:
            if flag.severity == 'HIGH':
                recommendations.append(flag.recommendation)

        if not recommendations:
            recommendations.append("All integrity checks passed - research is trustworthy")

        return recommendations
