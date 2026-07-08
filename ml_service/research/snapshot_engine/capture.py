"""Capture functions for creating snapshots."""

import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import asdict

from ml_service.repositories.trade_repository import TradeRepository
from ml_service.repositories.signal_repository import SignalRepository
from ml_service.research.snapshot_engine.types import Snapshot


def capture_snapshot(symbol: Optional[str] = None, db_path: Optional[str] = None) -> Snapshot:
    """Capture current system state as a deterministic snapshot.

    Args:
        symbol: Optional symbol filter
        db_path: Optional database path for repositories

    Returns:
        Snapshot object containing trades, signals, and enriched state
    """
    trade_repo = TradeRepository(db_path=db_path)
    signal_repo = SignalRepository(db_path=db_path)

    timestamp = datetime.utcnow().isoformat()

    trade_positions = trade_repo.find_all(symbol=symbol, limit=10000)
    trades = [asdict(pos) for pos in trade_positions]

    all_signals = signal_repo.find_recent(symbol=symbol, limit=10000)
    signals_raw = [asdict(sig) for sig in all_signals]

    signals = _enrich_signals(signals_raw, trades)

    signal_state = _capture_signal_state(signals, trades)
    feature_state = _capture_feature_state(signals)
    regime_state = _capture_regime_state(signals, trades)
    risk_state = _capture_risk_state(trades)
    execution_state = _capture_execution_state(trades)

    account_state = _capture_account_state(db_path)
    position_state = _capture_position_state(db_path)
    execution_constraints = _capture_execution_constraints()
    regime_statistics = _capture_regime_statistics(db_path)

    market_state = None
    model_state = None

    snapshot_content = {
        'timestamp': timestamp,
        'trades': trades,
        'signals': signals,
        'account_state': account_state,
        'market_state': market_state,
        'model_state': model_state,
        'signal_state': signal_state,
        'feature_state': feature_state,
        'regime_state': regime_state,
        'risk_state': risk_state,
        'execution_state': execution_state
    }

    snapshot_id = _generate_snapshot_id(snapshot_content)

    return Snapshot(
        snapshot_id=snapshot_id,
        timestamp=timestamp,
        trades=trades,
        signals=signals,
        account_state=account_state,
        market_state=market_state,
        model_state=model_state,
        signal_state=signal_state,
        feature_state=feature_state,
        regime_state=regime_state,
        risk_state=risk_state,
        execution_state=execution_state,
        position_state=position_state,
        execution_constraints=execution_constraints,
        regime_statistics=regime_statistics
    )


def _enrich_signals(signals_raw: List[Dict[str, Any]], trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich signals with probability and regime data from trades.

    Args:
        signals_raw: Raw signal dictionaries
        trades: Trade dictionaries

    Returns:
        Enriched signal dictionaries with prob_long, prob_short, prob_neutral, regime, features
    """
    trade_map = {t.get('signal_id'): t for t in trades if t.get('signal_id') is not None}

    enriched = []
    for signal in signals_raw:
        sig = signal.copy()
        signal_id = sig.get('id')

        corresponding_trade = trade_map.get(signal_id)
        if corresponding_trade:
            sig['prob_long'] = corresponding_trade.get('prob_long')
            sig['prob_short'] = corresponding_trade.get('prob_short')
            sig['prob_neutral'] = corresponding_trade.get('prob_neutral')
            sig['regime'] = corresponding_trade.get('regime')
        else:
            sig['prob_long'] = sig.get('prob_long')
            sig['prob_short'] = sig.get('prob_short')
            sig['prob_neutral'] = sig.get('prob_neutral')
            sig['regime'] = sig.get('regime')

        features_json = sig.get('features_json')
        if features_json:
            try:
                sig['features'] = json.loads(features_json)
            except (json.JSONDecodeError, TypeError):
                sig['features'] = None
        else:
            sig['features'] = None

        enriched.append(sig)

    return enriched


def _capture_signal_state(signals: List[Dict[str, Any]], trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Capture signal-level state metadata.

    Args:
        signals: Enriched signal dictionaries
        trades: Trade dictionaries

    Returns:
        Signal state summary
    """
    total_signals = len(signals)
    signals_with_probs = sum(1 for s in signals if s.get('prob_long') is not None)
    signals_executed = len([t for t in trades if t.get('signal_id') is not None])

    return {
        'total_signals': total_signals,
        'signals_with_probabilities': signals_with_probs,
        'signals_executed': signals_executed,
        'execution_rate': signals_executed / total_signals if total_signals > 0 else 0.0
    }


def _capture_feature_state(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Capture feature-level state metadata.

    Args:
        signals: Enriched signal dictionaries

    Returns:
        Feature state summary
    """
    signals_with_features = sum(1 for s in signals if s.get('features') is not None)

    feature_keys = set()
    for signal in signals:
        features = signal.get('features')
        if features and isinstance(features, dict):
            feature_keys.update(features.keys())

    return {
        'signals_with_features': signals_with_features,
        'unique_feature_keys': sorted(list(feature_keys)) if feature_keys else []
    }


def _capture_regime_state(signals: List[Dict[str, Any]], trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Capture regime distribution across signals and trades.

    Args:
        signals: Enriched signal dictionaries
        trades: Trade dictionaries

    Returns:
        Regime state summary
    """
    signal_regimes = [s.get('regime') for s in signals if s.get('regime') is not None]
    trade_regimes = [t.get('regime') for t in trades if t.get('regime') is not None]

    signal_regime_dist = {}
    for regime in signal_regimes:
        signal_regime_dist[regime] = signal_regime_dist.get(regime, 0) + 1

    trade_regime_dist = {}
    for regime in trade_regimes:
        trade_regime_dist[regime] = trade_regime_dist.get(regime, 0) + 1

    return {
        'signal_regime_distribution': signal_regime_dist,
        'trade_regime_distribution': trade_regime_dist,
        'signals_with_regime': len(signal_regimes),
        'trades_with_regime': len(trade_regimes)
    }


def _capture_risk_state(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Capture risk metrics from trades.

    Args:
        trades: Trade dictionaries

    Returns:
        Risk state summary
    """
    open_trades = [t for t in trades if t.get('status') == 'OPEN']
    closed_trades = [t for t in trades if t.get('status') != 'OPEN']

    total_exposure = sum(t.get('size_usdt', 0.0) for t in open_trades)
    total_realized_pnl = sum(t.get('realized_pnl', 0.0) for t in closed_trades)

    trades_with_sl = sum(1 for t in trades if t.get('stop_loss') is not None)
    trades_with_tp = sum(1 for t in trades if t.get('take_profit') is not None)

    return {
        'open_positions': len(open_trades),
        'closed_positions': len(closed_trades),
        'total_exposure_usdt': total_exposure,
        'total_realized_pnl': total_realized_pnl,
        'trades_with_stop_loss': trades_with_sl,
        'trades_with_take_profit': trades_with_tp
    }


def _capture_execution_state(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Capture execution-level state metadata.

    Args:
        trades: Trade dictionaries

    Returns:
        Execution state summary
    """
    execution_policies = [t.get('execution_policy') for t in trades if t.get('execution_policy') is not None]

    policy_dist = {}
    for policy in execution_policies:
        policy_dist[policy] = policy_dist.get(policy, 0) + 1

    skip_reasons = [t.get('skip_reason') for t in trades if t.get('skip_reason') is not None]
    skip_reason_dist = {}
    for reason in skip_reasons:
        skip_reason_dist[reason] = skip_reason_dist.get(reason, 0) + 1

    return {
        'execution_policy_distribution': policy_dist,
        'skip_reason_distribution': skip_reason_dist,
        'trades_with_execution_edge': sum(1 for t in trades if t.get('execution_edge') is not None)
    }


def _capture_account_state(db_path: Optional[str]) -> Dict[str, Any]:
    """Capture paper account state for execution replay.

    Args:
        db_path: Optional database path

    Returns:
        Account state with balance, equity, unrealized_pnl
    """
    import sqlite3
    from pathlib import Path

    if db_path:
        conn = sqlite3.connect(db_path)
    else:
        db_file = Path(__file__).parent.parent.parent / "storage" / "database.db"
        conn = sqlite3.connect(str(db_file))

    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            "SELECT balance, equity, unrealized_pnl, updated_at FROM paper_account WHERE id = 1"
        ).fetchone()

        if row:
            return {
                'balance': row['balance'],
                'equity': row['equity'],
                'unrealized_pnl': row['unrealized_pnl'],
                'updated_at': row['updated_at']
            }
        else:
            return {
                'balance': 10000.0,
                'equity': 10000.0,
                'unrealized_pnl': 0.0,
                'updated_at': None
            }
    except Exception:
        return {
            'balance': 10000.0,
            'equity': 10000.0,
            'unrealized_pnl': 0.0,
            'updated_at': None
        }
    finally:
        conn.close()


def _capture_position_state(db_path: Optional[str]) -> Dict[str, Any]:
    """Capture position state for cooldown and conflict checks.

    Args:
        db_path: Optional database path

    Returns:
        Position state with open positions and recent SL hits
    """
    import sqlite3
    from pathlib import Path

    if db_path:
        conn = sqlite3.connect(db_path)
    else:
        db_file = Path(__file__).parent.parent.parent / "storage" / "database.db"
        conn = sqlite3.connect(str(db_file))

    conn.row_factory = sqlite3.Row

    try:
        open_rows = conn.execute(
            "SELECT symbol, direction, status FROM paper_positions WHERE status = 'OPEN'"
        ).fetchall()

        open_positions = [
            {'symbol': r['symbol'], 'direction': r['direction'], 'status': r['status']}
            for r in open_rows
        ]

        sl_rows = conn.execute(
            """
            SELECT symbol, direction, closed_at,
                   (julianday('now') - julianday(closed_at)) * 24 AS hours_ago
            FROM paper_positions
            WHERE status = 'SL_HIT'
            ORDER BY closed_at DESC
            LIMIT 100
            """
        ).fetchall()

        recent_sl_hits = [
            {
                'symbol': r['symbol'],
                'direction': r['direction'],
                'closed_at': r['closed_at'],
                'hours_ago': r['hours_ago']
            }
            for r in sl_rows
        ]

        return {
            'open_positions': open_positions,
            'recent_sl_hits': recent_sl_hits,
            'open_count': len(open_positions)
        }
    except Exception:
        return {
            'open_positions': [],
            'recent_sl_hits': [],
            'open_count': 0
        }
    finally:
        conn.close()


def _capture_execution_constraints() -> Dict[str, Any]:
    """Capture execution constraint parameters from paper_broker.

    Returns:
        Execution constraints dictionary
    """
    from ml_service.trading import paper_broker

    return {
        'starting_balance': paper_broker.STARTING_BALANCE,
        'max_open_positions': paper_broker.MAX_OPEN_POSITIONS,
        'risk_per_trade_pct': paper_broker.RISK_PER_TRADE_PCT,
        'position_expiry_hours': paper_broker.POSITION_EXPIRY_HOURS,
        'min_execution_confidence': paper_broker.MIN_EXECUTION_CONFIDENCE,
        'min_probability_edge': paper_broker.MIN_PROBABILITY_EDGE,
        'cooldown_after_sl_hours': paper_broker.COOLDOWN_AFTER_SL_HOURS,
        'execution_policy': paper_broker.EXECUTION_POLICY,
        'break_even_at_r': paper_broker.BREAK_EVEN_AT_R,
        'trail_at_r': paper_broker.TRAIL_AT_R,
        'trail_distance_r': paper_broker.TRAIL_DISTANCE_R
    }


def _capture_regime_statistics(db_path: Optional[str]) -> Dict[str, Any]:
    """Capture regime execution policy statistics for all regimes.

    Args:
        db_path: Optional database path

    Returns:
        Per-regime statistics dictionary
    """
    import sqlite3
    from pathlib import Path
    from ml_service.trading.regime_execution_policy import get_regime_statistics

    if db_path:
        conn = sqlite3.connect(db_path)
    else:
        db_file = Path(__file__).parent.parent.parent / "storage" / "database.db"
        conn = sqlite3.connect(str(db_file))

    conn.row_factory = sqlite3.Row

    try:
        regime_rows = conn.execute(
            "SELECT DISTINCT regime FROM paper_positions WHERE regime IS NOT NULL"
        ).fetchall()

        regimes = [r['regime'] for r in regime_rows]

        regime_stats = {}
        for regime in regimes:
            try:
                stats = get_regime_statistics(regime)
                regime_stats[regime] = stats
            except Exception:
                regime_stats[regime] = {
                    'regime': regime,
                    'sample_size': 0,
                    'status': 'error'
                }

        return regime_stats
    except Exception:
        return {}
    finally:
        conn.close()


def _generate_snapshot_id(snapshot_content: Dict[str, Any]) -> str:
    """Generate deterministic snapshot ID from sorted JSON content.

    Args:
        snapshot_content: Full snapshot content dictionary

    Returns:
        SHA256 hash as hex string
    """
    sorted_json = json.dumps(snapshot_content, sort_keys=True, default=str)
    return hashlib.sha256(sorted_json.encode()).hexdigest()
