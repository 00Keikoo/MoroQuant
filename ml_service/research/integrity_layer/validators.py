"""Validators for research integrity."""

import hashlib
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from .types import BiasFlag


class SnapshotIntegrityValidator:
    """Validates snapshot integrity and consistency."""

    def validate(self, snapshot: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate snapshot integrity.

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Check required fields
        required_fields = ['snapshot_id', 'timestamp', 'trades', 'signals']
        for field in required_fields:
            if field not in snapshot:
                issues.append(f"Missing required field: {field}")

        if issues:
            return False, issues

        # Validate timestamp format
        try:
            datetime.fromisoformat(snapshot['timestamp'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            issues.append(f"Invalid timestamp format: {snapshot.get('timestamp')}")

        # Validate data types
        if not isinstance(snapshot.get('trades'), list):
            issues.append("trades must be a list")
        if not isinstance(snapshot.get('signals'), list):
            issues.append("signals must be a list")

        # Check for empty required lists
        if isinstance(snapshot.get('trades'), list) and len(snapshot['trades']) == 0:
            issues.append("trades list is empty")
        if isinstance(snapshot.get('signals'), list) and len(snapshot['signals']) == 0:
            issues.append("signals list is empty")

        return len(issues) == 0, issues

    def compute_hash(self, snapshot: Dict[str, Any]) -> str:
        """Compute deterministic hash of snapshot."""
        # Sort keys for deterministic serialization
        snapshot_str = json.dumps(snapshot, sort_keys=True)
        return hashlib.sha256(snapshot_str.encode()).hexdigest()

    def check_determinism(self, snapshot: Dict[str, Any]) -> bool:
        """Check if snapshot serialization is deterministic."""
        hash1 = self.compute_hash(snapshot)
        hash2 = self.compute_hash(snapshot)
        return hash1 == hash2


class ReplayIntegrityValidator:
    """Validates replay determinism and consistency."""

    def validate_determinism(
        self,
        replay_result1: Dict[str, Any],
        replay_result2: Dict[str, Any]
    ) -> tuple[bool, float, List[str]]:
        """Validate that two replay runs produce identical results.

        Returns:
            (is_deterministic, reproducibility_score, issues)
        """
        issues = []

        if replay_result1['snapshot_id'] != replay_result2['snapshot_id']:
            issues.append("Snapshot IDs do not match")
            return False, 0.0, issues

        # Compare decisions
        decisions1 = replay_result1.get('decisions', [])
        decisions2 = replay_result2.get('decisions', [])

        if len(decisions1) != len(decisions2):
            issues.append(f"Decision count mismatch: {len(decisions1)} vs {len(decisions2)}")
            reproducibility_score = 0.0
        else:
            # Calculate reproducibility score
            matching = sum(1 for d1, d2 in zip(decisions1, decisions2) if d1 == d2)
            reproducibility_score = matching / len(decisions1) if len(decisions1) > 0 else 1.0

            if reproducibility_score < 1.0:
                issues.append(f"Only {matching}/{len(decisions1)} decisions match")

        is_deterministic = reproducibility_score == 1.0
        return is_deterministic, reproducibility_score, issues

    def check_no_live_db_dependency(self, replay_notes: List[str]) -> tuple[bool, List[str]]:
        """Check that replay doesn't depend on live database.

        Returns:
            (is_isolated, issues)
        """
        issues = []
        live_db_indicators = ['live_db', 'database_query', 'external_call', 'api_request']

        for note in replay_notes:
            note_lower = note.lower()
            for indicator in live_db_indicators:
                if indicator in note_lower:
                    issues.append(f"Live DB dependency detected: {note}")
                    break

        return len(issues) == 0, issues


class ResearchBiasDetector:
    """Detects research biases in experiment results."""

    def detect_biases(
        self,
        snapshot: Dict[str, Any],
        evaluation_result: Optional[Dict[str, Any]] = None
    ) -> List[BiasFlag]:
        """Detect research biases.

        Args:
            snapshot: The snapshot data
            evaluation_result: Optional evaluation results

        Returns:
            List of bias flags
        """
        flags = []

        # Check for empty dataset
        if not snapshot.get('trades') or len(snapshot['trades']) == 0:
            flags.append(BiasFlag(
                bias_type='empty_dataset',
                severity='HIGH',
                description='No trades in snapshot',
                recommendation='Ensure snapshot contains actual trade data'
            ))

        if not snapshot.get('signals') or len(snapshot['signals']) == 0:
            flags.append(BiasFlag(
                bias_type='missing_signals',
                severity='HIGH',
                description='No signals in snapshot',
                recommendation='Ensure snapshot contains signal data for analysis'
            ))

        # Check for insufficient sample size
        trade_count = len(snapshot.get('trades', []))
        if 0 < trade_count < 30:
            flags.append(BiasFlag(
                bias_type='insufficient_sample_size',
                severity='MEDIUM',
                description=f'Only {trade_count} trades - below minimum threshold of 30',
                recommendation='Collect more data for statistically significant results'
            ))

        # Check evaluation results if provided
        if evaluation_result:
            flags.extend(self._detect_evaluation_biases(evaluation_result))

        return flags

    def _detect_evaluation_biases(self, evaluation_result: Dict[str, Any]) -> List[BiasFlag]:
        """Detect biases in evaluation results."""
        flags = []

        strategy_scores = evaluation_result.get('strategy_scores', [])

        if not strategy_scores:
            flags.append(BiasFlag(
                bias_type='missing_evaluation',
                severity='HIGH',
                description='No strategy scores in evaluation result',
                recommendation='Run complete evaluation before drawing conclusions'
            ))
            return flags

        # Check for unrealistic perfect metrics
        for score in strategy_scores:
            if score.get('win_rate', 0) == 1.0:
                flags.append(BiasFlag(
                    bias_type='unrealistic_metrics',
                    severity='HIGH',
                    description=f'Perfect win rate (100%) for {score.get("config_id")}',
                    recommendation='Investigate overfitting or data leakage'
                ))

            if score.get('max_drawdown', 1) == 0:
                flags.append(BiasFlag(
                    bias_type='unrealistic_metrics',
                    severity='MEDIUM',
                    description=f'Zero drawdown for {score.get("config_id")}',
                    recommendation='Verify risk calculations are accurate'
                ))

        # Check for survivorship bias (only profitable strategies evaluated)
        all_profitable = all(
            score.get('total_return', 0) > 0
            for score in strategy_scores
        )
        if all_profitable and len(strategy_scores) > 1:
            flags.append(BiasFlag(
                bias_type='survivorship_bias',
                severity='HIGH',
                description='All strategies are profitable - possible survivorship bias',
                recommendation='Include failing strategies in analysis to avoid selection bias'
            ))

        return flags
