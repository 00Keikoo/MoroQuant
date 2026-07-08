"""Execution parity checker - applies production execution filters to replay decisions."""

from typing import Dict, Any, Optional, List
from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.execution_parity.types import ExecutionParityResult, FilterCheckResult


class ExecutionParityChecker:
    """Applies production execution filters to replay decisions.

    Reproduces the filter pipeline from paper_broker.py::open_paper_position()
    without database queries or side effects.
    """

    def __init__(self, snapshot: Snapshot):
        self.account_state = snapshot.account_state or {}
        self.position_state = snapshot.position_state or {}
        self.regime_statistics = snapshot.regime_statistics or {}
        self.constraints = snapshot.execution_constraints or {}

    def check_execution(
        self,
        signal: Dict[str, Any],
        decision: str
    ) -> ExecutionParityResult:
        """Apply all production filters to a signal+decision.

        Args:
            signal: Signal dictionary with all fields
            decision: Reconstructed decision (LONG, SHORT, HOLD)

        Returns:
            ExecutionParityResult with execution verdict and details
        """
        if decision == "HOLD":
            return ExecutionParityResult(
                execution_allowed=False,
                block_reason="decision_is_hold",
                passed_filters=[],
                position_size=None
            )

        checks = [
            self._check_confidence(signal),
            self._check_regime_policy(signal),
            self._check_edge(signal),
            self._check_cooldown(signal, decision),
            self._check_max_positions(),
            self._check_symbol_conflict(signal)
        ]

        passed_filters = []
        for check in checks:
            if check.passed:
                passed_filters.append(check.name)
            else:
                return ExecutionParityResult(
                    execution_allowed=False,
                    block_reason=check.reason,
                    passed_filters=passed_filters,
                    failed_filter=check
                )

        sizing_result = self._compute_position_sizing(signal)

        return ExecutionParityResult(
            execution_allowed=True,
            block_reason=None,
            passed_filters=passed_filters,
            position_size=sizing_result['size_usdt'],
            sizing_multiplier=sizing_result['regime_multiplier'],
            risk_check_result=sizing_result,
            regime_check_result=self._get_regime_metadata(signal)
        )

    def _check_confidence(self, signal: Dict[str, Any]) -> FilterCheckResult:
        """Check minimum execution confidence filter."""
        min_conf = self.constraints.get('min_execution_confidence', 55)
        confidence = signal.get('confidence')

        if confidence is None:
            return FilterCheckResult(
                name="confidence_filter",
                passed=True,
                reason=None
            )

        try:
            conf_val = int(confidence)
            if conf_val < min_conf:
                return FilterCheckResult(
                    name="confidence_filter",
                    passed=False,
                    reason=f"confidence_{conf_val}_below_min_{min_conf}",
                    metadata={'confidence': conf_val, 'required': min_conf}
                )
        except (ValueError, TypeError):
            pass

        return FilterCheckResult(
            name="confidence_filter",
            passed=True,
            reason=None
        )

    def _check_regime_policy(self, signal: Dict[str, Any]) -> FilterCheckResult:
        """Check regime execution policy filter."""
        regime = signal.get('regime')
        if not regime:
            return FilterCheckResult(
                name="regime_policy",
                passed=True,
                reason=None
            )

        regime_stats = self.regime_statistics.get(regime)
        if not regime_stats:
            return FilterCheckResult(
                name="regime_policy",
                passed=True,
                reason="no_regime_data"
            )

        status = regime_stats.get('status')

        if status == 'blocked':
            return FilterCheckResult(
                name="regime_policy",
                passed=False,
                reason=f"regime_{regime}_blocked_uci_negative",
                metadata=regime_stats
            )

        return FilterCheckResult(
            name="regime_policy",
            passed=True,
            reason=None,
            metadata=regime_stats
        )

    def _check_edge(self, signal: Dict[str, Any]) -> FilterCheckResult:
        """Check probability edge filter."""
        min_edge = self.constraints.get('min_probability_edge', 0.20)

        prob_short = signal.get('prob_short')
        prob_neutral = signal.get('prob_neutral')
        prob_long = signal.get('prob_long')

        probs_list = [prob_short, prob_neutral, prob_long]
        if not all(p is not None for p in probs_list):
            return FilterCheckResult(
                name="edge_filter",
                passed=True,
                reason=None
            )

        try:
            prob_vals = [float(p) for p in probs_list]
            prob_vals.sort(reverse=True)
            edge = prob_vals[0] - prob_vals[1]

            if edge < min_edge:
                return FilterCheckResult(
                    name="edge_filter",
                    passed=False,
                    reason=f"edge_{edge:.2f}_below_min_{min_edge:.2f}",
                    metadata={'edge': edge, 'required': min_edge}
                )
        except (ValueError, TypeError):
            pass

        return FilterCheckResult(
            name="edge_filter",
            passed=True,
            reason=None
        )

    def _check_cooldown(self, signal: Dict[str, Any], decision: str) -> FilterCheckResult:
        """Check post-SL cooldown filter."""
        cooldown_hours = self.constraints.get('cooldown_after_sl_hours', 6)
        symbol = signal.get('symbol')

        recent_sl_hits = self.position_state.get('recent_sl_hits', [])

        for sl_hit in recent_sl_hits:
            if sl_hit['symbol'] == symbol and sl_hit['direction'] == decision:
                hours_ago = sl_hit.get('hours_ago')
                if hours_ago is not None and hours_ago < cooldown_hours:
                    return FilterCheckResult(
                        name="cooldown_filter",
                        passed=False,
                        reason=f"cooldown_active_{hours_ago:.1f}h_ago",
                        metadata={'hours_ago': hours_ago, 'required': cooldown_hours}
                    )

        return FilterCheckResult(
            name="cooldown_filter",
            passed=True,
            reason=None
        )

    def _check_max_positions(self) -> FilterCheckResult:
        """Check max open positions limit."""
        max_positions = self.constraints.get('max_open_positions')

        if max_positions is None:
            return FilterCheckResult(
                name="max_positions",
                passed=True,
                reason=None
            )

        open_count = self.position_state.get('open_count', 0)

        if open_count >= max_positions:
            return FilterCheckResult(
                name="max_positions",
                passed=False,
                reason=f"max_positions_reached_{open_count}/{max_positions}",
                metadata={'open_count': open_count, 'max': max_positions}
            )

        return FilterCheckResult(
            name="max_positions",
            passed=True,
            reason=None
        )

    def _check_symbol_conflict(self, signal: Dict[str, Any]) -> FilterCheckResult:
        """Check one-position-per-symbol rule."""
        symbol = signal.get('symbol')
        open_positions = self.position_state.get('open_positions', [])

        for pos in open_positions:
            if pos['symbol'] == symbol:
                return FilterCheckResult(
                    name="symbol_conflict",
                    passed=False,
                    reason=f"existing_position_on_{symbol}",
                    metadata={'symbol': symbol}
                )

        return FilterCheckResult(
            name="symbol_conflict",
            passed=True,
            reason=None
        )

    def _compute_position_sizing(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Compute position size with regime adjustment."""
        equity = self.account_state.get('equity', 10000.0)
        risk_pct = self.constraints.get('risk_per_trade_pct', 0.01)

        base_size = equity * risk_pct

        regime = signal.get('regime')
        regime_multiplier = 1.0

        if regime:
            regime_stats = self.regime_statistics.get(regime)
            if regime_stats and regime_stats.get('status') == 'restricted':
                lci = regime_stats.get('lci', 0.0)
                mean = regime_stats.get('mean_return', 0.0)
                if mean > 0:
                    regime_multiplier = max(0.1, 1.0 - abs(lci) / mean)
                else:
                    regime_multiplier = 0.1

        size_usdt = round(base_size * regime_multiplier, 2)

        return {
            'size_usdt': size_usdt,
            'base_size': base_size,
            'regime_multiplier': regime_multiplier,
            'equity': equity,
            'risk_pct': risk_pct
        }

    def _get_regime_metadata(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get regime statistics metadata."""
        regime = signal.get('regime')
        if not regime:
            return None

        return self.regime_statistics.get(regime)
