"""Regime Execution Policy.

Implements the statistical framework defined in:
docs/research/regime_execution_policy.md

This module provides the decision logic to determine whether execution
should be permitted, restricted, or blocked for a given market regime
based on bootstrap confidence intervals of historical trade returns.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox

_DB_PATH: Path = Path(__file__).parent.parent / "storage" / "database.db"


def _get_connection():
    """Get database connection with Row factory."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@dataclass
class ExecutionDecision:
    """Output from regime execution policy evaluation.

    Attributes:
        execution_permitted: Whether execution is allowed
        sizing_multiplier: Risk allocation scaling factor [0.0, 1.0]
        statistical_metadata: Computed statistics (N_r, mean, LCI, UCI, etc.)
    """
    execution_permitted: bool
    sizing_multiplier: float
    statistical_metadata: Dict
    block_reason: Optional[str] = None


def _is_structurally_blocked(regime: str, conn: sqlite3.Connection) -> bool:
    """Check if regime is manually flagged as structurally untradable.

    Per Section 6: structural blocks are static overrides for regimes
    that cannot be traded due to system design limits.
    """
    try:
        row = conn.execute(
            "SELECT 1 FROM regime_blocks WHERE regime = ? AND is_active = 1",
            (regime,)
        ).fetchone()
        return row is not None
    except sqlite3.OperationalError:
        return False


def _load_regime_trade_returns(regime: str, conn: sqlite3.Connection) -> List[float]:
    """Load historical R-multiple returns for a given regime.

    Per Section 4: Trade Return is normalized by initial risk at entry (R-multiple).
    Formula: x_i = (P_exit - P_entry) / (P_entry - P_SL) × Direction
    """
    rows = conn.execute(
        """
        SELECT entry_price, current_price, stop_loss, direction, realized_pnl, size_usdt
        FROM paper_positions
        WHERE status != 'OPEN'
          AND regime = ?
          AND stop_loss IS NOT NULL
          AND entry_price > 0
          AND current_price > 0
        ORDER BY closed_at DESC
        """,
        (regime,)
    ).fetchall()

    returns = []
    for r in rows:
        entry = r["entry_price"]
        exit_price = r["current_price"]
        sl = r["stop_loss"]
        direction = r["direction"]

        initial_risk = abs(entry - sl)
        if initial_risk == 0:
            continue

        price_move = exit_price - entry
        if direction == "SHORT":
            price_move = -price_move

        r_multiple = price_move / initial_risk
        returns.append(r_multiple)

    return returns


def _compute_newey_west_adjustment(returns: np.ndarray, sample_size: int) -> float:
    """Compute Newey-West standard error multiplier if autocorrelation is significant.

    Per Section 5.2: If Ljung-Box Q-statistic at lag 1 has p < 0.05,
    apply Newey-West correction.
    """
    if len(returns) < 3:
        return 1.0

    try:
        lb_result = acorr_ljungbox(returns, lags=[1], return_df=False)
        p_value = lb_result[1][0]

        if p_value >= 0.05:
            return 1.0

        L = int(np.floor(4 * (sample_size / 100) ** (2/9)))
        L = max(1, L)

        adjustment_factor = 1.0
        for k in range(1, L + 1):
            if k >= len(returns):
                break
            rho_k = np.corrcoef(returns[:-k], returns[k:])[0, 1]
            weight = 1 - k / (L + 1)
            adjustment_factor += 2 * weight * rho_k

        return np.sqrt(max(1.0, adjustment_factor))

    except Exception:
        return 1.0


def _bootstrap_confidence_interval(
    returns: List[float],
    alpha: float = 0.05,
    n_bootstrap: int = 1000
) -> tuple[float, float, float]:
    """Compute non-parametric bootstrap confidence intervals.

    Per Section 5.3: Percentile Bootstrap Method with B=1000 replicates.
    Returns (sample_mean, LCI_r, UCI_r)
    """
    returns_array = np.array(returns)
    sample_mean = float(np.mean(returns_array))
    n = len(returns_array)

    bootstrap_means = []
    rng = np.random.RandomState(42)

    for _ in range(n_bootstrap):
        bootstrap_sample = rng.choice(returns_array, size=n, replace=True)
        bootstrap_means.append(np.mean(bootstrap_sample))

    bootstrap_means = np.sort(bootstrap_means)

    lower_percentile = alpha / 2
    upper_percentile = 1 - alpha / 2

    lci_idx = int(n_bootstrap * lower_percentile)
    uci_idx = int(n_bootstrap * upper_percentile)

    lci = float(bootstrap_means[lci_idx])
    uci = float(bootstrap_means[uci_idx])

    return sample_mean, lci, uci


def evaluate_regime_execution_policy(
    regime: str,
    signal_id: Optional[int] = None,
    confidence: Optional[int] = None
) -> ExecutionDecision:
    """Evaluate whether execution should be permitted for a given regime.

    Implements the Hybrid Execution Policy from Section 6:
    1. Check structural block (static override)
    2. Check sample size >= 100 for dynamic review
    3. If UCI_r < 0: BLOCK
    4. If LCI_r < 0: RESTRICT (scale sizing)
    5. Otherwise: PERMIT

    Args:
        regime: Market regime classification
        signal_id: Optional signal identifier for logging
        confidence: Optional model confidence score

    Returns:
        ExecutionDecision with permission, sizing, and metadata
    """
    conn = _get_connection()

    try:
        if _is_structurally_blocked(regime, conn):
            return ExecutionDecision(
                execution_permitted=False,
                sizing_multiplier=0.0,
                statistical_metadata={
                    "regime": regime,
                    "reason": "structural_block",
                },
                block_reason="structural_block"
            )

        returns = _load_regime_trade_returns(regime, conn)
        n_r = len(returns)

        if n_r < 100:
            return ExecutionDecision(
                execution_permitted=True,
                sizing_multiplier=1.0,
                statistical_metadata={
                    "regime": regime,
                    "sample_size": n_r,
                    "reason": "insufficient_data",
                },
            )

        sample_mean, lci, uci = _bootstrap_confidence_interval(returns)

        returns_array = np.array(returns)
        std_dev = float(np.std(returns_array, ddof=1))
        se = std_dev / np.sqrt(n_r)

        nw_multiplier = _compute_newey_west_adjustment(returns_array, n_r)
        se_adjusted = se * nw_multiplier

        metadata = {
            "regime": regime,
            "sample_size": n_r,
            "mean_return": sample_mean,
            "std_dev": std_dev,
            "standard_error": se,
            "se_adjusted": se_adjusted,
            "lci": lci,
            "uci": uci,
            "alpha": 0.05,
            "bootstrap_replicates": 1000,
        }

        if uci < 0.0:
            return ExecutionDecision(
                execution_permitted=False,
                sizing_multiplier=0.0,
                statistical_metadata=metadata,
                block_reason="uci_negative"
            )

        if lci < 0.0:
            sizing_multiplier = max(0.1, 1.0 - abs(lci) / sample_mean) if sample_mean > 0 else 0.1
            return ExecutionDecision(
                execution_permitted=True,
                sizing_multiplier=float(sizing_multiplier),
                statistical_metadata=metadata,
            )

        return ExecutionDecision(
            execution_permitted=True,
            sizing_multiplier=1.0,
            statistical_metadata=metadata,
        )

    finally:
        conn.close()


def get_regime_statistics(regime: str) -> Dict:
    """Get current statistical summary for a regime.

    Utility function for monitoring and dashboard display.
    """
    conn = _get_connection()

    try:
        returns = _load_regime_trade_returns(regime, conn)
        n_r = len(returns)

        if n_r == 0:
            return {
                "regime": regime,
                "sample_size": 0,
                "status": "no_data",
            }

        if n_r < 100:
            return {
                "regime": regime,
                "sample_size": n_r,
                "status": "insufficient_data",
                "mean_return": float(np.mean(returns)),
            }

        sample_mean, lci, uci = _bootstrap_confidence_interval(returns)

        if uci < 0.0:
            status = "blocked"
        elif lci < 0.0:
            status = "restricted"
        else:
            status = "permitted"

        return {
            "regime": regime,
            "sample_size": n_r,
            "status": status,
            "mean_return": sample_mean,
            "lci": lci,
            "uci": uci,
        }

    finally:
        conn.close()
