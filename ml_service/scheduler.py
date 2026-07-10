#!/usr/bin/env python3
"""Auto-retrain scheduler for ML models."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import csv
import traceback
import yaml
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ml_service.data.database import get_database
from ml_service.data.ingestion import fetch_all
from ml_service.data.coingecko import get_coingecko_fetcher
from ml_service.models.trainer import train_model
from ml_service.models.governance import compare_and_promote
from ml_service.retraining_policy import should_retrain_model
from ml_service.utils.logger import setup_logger, get_logger

setup_logger()
logger = get_logger()

TIER_1_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'HYPEUSDT']
TIER_2_SYMBOLS = ['XRPUSDT', 'LINKUSDT', 'LTCUSDT', 'SUIUSDT', 'ZECUSDT', 'ADAUSDT']

SYMBOLS = TIER_1_SYMBOLS + TIER_2_SYMBOLS

TIMEFRAMES = ['1h', '4h']
F1_THRESHOLD = 1.03
RETRAIN_LOG_PATH = Path(__file__).parent / 'storage' / 'logs' / 'retrain_log.csv'

_scheduler = None
_last_retrain_time = None
_last_retrain_results = []


def load_data(symbol: str, timeframe: str, limit: int = 2000):
    """Load OHLCV data from database."""
    db = get_database()
    with db.get_connection() as conn:
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))

    if df.empty:
        return None

    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def get_current_model_f1(symbol: str, timeframe: str) -> float:
    """Get F1 score of current production model from pickle metadata."""
    from ml_service.models.governance import get_production_model_path, load_model_metadata

    production_path = get_production_model_path(symbol, timeframe)
    if not production_path:
        return 0.0

    metadata = load_model_metadata(production_path)
    if not metadata:
        return 0.0

    validation = metadata.get('validation', {})
    return validation.get('avg_f1_weighted', 0.0)


def retrain_job():
    """Main retraining job - runs every 24 hours."""
    global _last_retrain_time, _last_retrain_results

    logger.info("="*80)
    logger.info("Starting scheduled retrain job")
    logger.info("="*80)

    _last_retrain_time = datetime.now()
    _last_retrain_results = []

    logger.info("Step 1: Fetching latest data (last 7 days)...")
    try:
        fetch_all(days_back=7)
        logger.info("Data fetch complete")
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        return

    logger.info("Step 2: Loading reference data...")
    btc_1h = load_data('BTCUSDT', '1h')
    btc_4h = load_data('BTCUSDT', '4h')
    eth_1h = load_data('ETHUSDT', '1h')
    eth_4h = load_data('ETHUSDT', '4h')
    spy_1h = load_data('ES_proxy', '1h')
    spy_4h = load_data('ES_proxy', '4h')

    logger.info("Step 3: Loading market dominance data...")
    fetcher = get_coingecko_fetcher()
    dominance_df = fetcher.get_dominance_dataframe()
    logger.info(f"Loaded {len(dominance_df)} market dominance records")

    logger.info("Step 4: Retraining all models...")

    for symbol in TIER_1_SYMBOLS:
        for timeframe in TIMEFRAMES:
            logger.info(f"\nTraining {symbol} {timeframe}")

            df = load_data(symbol, timeframe)

            if df is None or len(df) < 100:
                logger.warning(f"Insufficient data for {symbol} {timeframe}")
                _last_retrain_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'skipped',
                    'reason': 'insufficient_data',
                    'old_f1': 0.0,
                    'new_f1': 0.0,
                })
                continue

            old_f1 = get_current_model_f1(symbol, timeframe)

            btc_df = None if symbol == 'BTCUSDT' else (btc_1h if timeframe == '1h' else btc_4h)
            eth_df = eth_1h if timeframe == '1h' else eth_4h
            spy_df = spy_1h if timeframe == '1h' else spy_4h

            try:
                train_results = train_model(
                    df=df,
                    symbol=symbol,
                    timeframe=timeframe,
                    btc_df=btc_df,
                    eth_df=eth_df,
                    spy_df=spy_df,
                    dominance_df=dominance_df,
                )

                new_f1 = train_results['avg_f1_weighted']
                candidate_path = train_results['model_path']

                governance_result = compare_and_promote(
                    candidate_path=candidate_path,
                    symbol=symbol,
                    timeframe=timeframe,
                    improvement_threshold=F1_THRESHOLD,
                )

                status = governance_result.get('status', 'unknown')
                reason = governance_result.get('reason', '')

                _last_retrain_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': status,
                    'reason': reason,
                    'old_f1': old_f1,
                    'new_f1': new_f1,
                    'governance': governance_result,
                })

            except Exception as e:
                logger.error(
                    f"Training failed for {symbol} {timeframe}: {e}\n"
                    f"{traceback.format_exc()}"
                )

                _last_retrain_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'failed',
                    'reason': str(e),
                    'old_f1': old_f1,
                    'new_f1': 0.0,
                })

    logger.info("Step 5: Logging results...")
    log_retrain_results(_last_retrain_results)

    logger.info("="*80)
    logger.info("Scheduled retrain job complete")
    logger.info("="*80)


def adaptive_retrain_job():
    """Condition-based retraining driven by drift scores and model age.

    Replaces the static daily retrain + weekly tier-2 cadence with a single
    per-model decision loop.  For each symbol × timeframe the policy checks
    cooldown, drift threshold, and max age before deciding to retrain.

    Per-model failures never stop the loop — every model gets a chance.
    """
    global _last_retrain_time, _last_retrain_results

    logger.info("=" * 80)
    logger.info("Adaptive retraining decision cycle started")
    logger.info("=" * 80)

    _last_retrain_time = datetime.now()
    _last_retrain_results = []

    # ── Step 1: Fetch latest data (same as legacy retrain_job) ─────────
    logger.info("Step 1: Fetching latest data (last 7 days)...")
    try:
        fetch_all(days_back=7)
        logger.info("Data fetch complete")
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        return

    # ── Step 2: Load reference data for cross-pair features ─────────────
    logger.info("Step 2: Loading reference data...")
    btc_1h = load_data('BTCUSDT', '1h')
    btc_4h = load_data('BTCUSDT', '4h')
    eth_1h = load_data('ETHUSDT', '1h')
    eth_4h = load_data('ETHUSDT', '4h')
    spy_1h = load_data('ES_proxy', '1h')
    spy_4h = load_data('ES_proxy', '4h')

    logger.info("Step 3: Loading market dominance data...")
    try:
        fetcher = get_coingecko_fetcher()
        dominance_df = fetcher.get_dominance_dataframe()
        logger.info(f"Loaded {len(dominance_df)} market dominance records")
    except Exception as e:
        logger.warning(f"Market dominance fetch failed, proceeding without: {e}")
        dominance_df = None

    # ── Step 4: Per-model adaptive decision loop ────────────────────────
    logger.info("Step 4: Evaluating adaptive retrain decisions...")

    retrained = 0
    skipped = 0
    failed = 0

    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            should_retrain, reason, diagnostics = \
                should_retrain_model(symbol, timeframe)

            drift_val = diagnostics.get('drift_score')
            health_val = diagnostics.get('health_status')
            age_days_val = diagnostics.get('age_days')
            cooldown_hours = diagnostics.get('age_hours')

            # ── Structured decision log ─────────────────────────────────
            logger.info(
                f"Adaptive retraining decision: "
                f"{symbol} {timeframe}  "
                f"drift={drift_val}  "
                f"health={health_val}  "
                f"age={age_days_val}d  "
                f"cooldown={cooldown_hours}h  "
                f"decision={'RETRAIN' if should_retrain else 'SKIP'}  "
                f"reason={reason}"
            )

            if not should_retrain:
                skipped += 1
                _last_retrain_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'skipped',
                    'reason': reason,
                    'old_f1': 0.0,
                    'new_f1': 0.0,
                })
                continue

            # ── Retrain ─────────────────────────────────────────────────
            df = load_data(symbol, timeframe)
            if df is None or len(df) < 100:
                logger.warning(
                    f"Insufficient data for {symbol} {timeframe}"
                )
                failed += 1
                _last_retrain_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'failed',
                    'reason': 'insufficient_data',
                    'old_f1': 0.0,
                    'new_f1': 0.0,
                })
                continue

            old_f1 = get_current_model_f1(symbol, timeframe)

            btc_df = None if symbol == 'BTCUSDT' else (
                btc_1h if timeframe == '1h' else btc_4h
            )
            eth_df = eth_1h if timeframe == '1h' else eth_4h
            spy_df = spy_1h if timeframe == '1h' else spy_4h

            try:
                train_results = train_model(
                    df=df,
                    symbol=symbol,
                    timeframe=timeframe,
                    btc_df=btc_df,
                    eth_df=eth_df,
                    spy_df=spy_df,
                    dominance_df=dominance_df,
                )

                new_f1 = train_results['avg_f1_weighted']
                candidate_path = train_results['model_path']

                governance_result = compare_and_promote(
                    candidate_path=candidate_path,
                    symbol=symbol,
                    timeframe=timeframe,
                    improvement_threshold=F1_THRESHOLD,
                )

                status = governance_result.get('status', 'unknown')
                gov_reason = governance_result.get('reason', '')

                _last_retrain_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': status,
                    'reason': gov_reason,
                    'old_f1': old_f1,
                    'new_f1': new_f1,
                    'governance': governance_result,
                })

                retrained += 1
                logger.info(
                    f"Retrain complete: {symbol} {timeframe} | "
                    f"old_f1={old_f1:.4f} new_f1={new_f1:.4f} | "
                    f"governance={status} ({gov_reason})"
                )

            except Exception as e:
                logger.error(
                    f"Training failed for {symbol} {timeframe}: {e}\n"
                    f"{traceback.format_exc()}"
                )
                failed += 1
                _last_retrain_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'failed',
                    'reason': str(e),
                    'old_f1': old_f1,
                    'new_f1': 0.0,
                })

    # ── Step 5: Summary ─────────────────────────────────────────────────
    logger.info("Step 5: Logging results...")
    log_retrain_results(_last_retrain_results)

    logger.info(
        f"Adaptive retraining summary: "
        f"retrained={retrained}  skipped={skipped}  failed={failed}"
    )

    logger.info("=" * 80)
    logger.info("Adaptive retraining decision cycle complete")
    logger.info("=" * 80)


def market_dominance_job():
    """Fetch market dominance data from CoinGecko - runs every hour."""
    logger.info("Fetching market dominance data from CoinGecko...")

    try:
        fetcher = get_coingecko_fetcher()
        success = fetcher.fetch_and_store()

        if success:
            logger.info("Market dominance data updated successfully")
        else:
            logger.warning("Failed to update market dominance data")
    except Exception as e:
        logger.error(f"Market dominance fetch failed: {e}")


def signal_generation_job():
    """Generate signals for all production symbols - runs every hour."""
    from ml_service.models.predictor import generate_signal
    from ml_service.notifications.telegram_notifier import (
        send_signal_alert,
        should_send_telegram_alert,
    )

    # ── Trading mode check (infrastructure logging only) ──────────────
    from ml_service.trading.mode_manager import can_open_new_positions, get_trading_mode
    current_mode = get_trading_mode()
    can_open = can_open_new_positions()
    logger.info(f"Trading mode: {current_mode} | can_open_new_positions={can_open}")
    # NOTE: Signal generation continues regardless of mode.  The execution
    # layer will later honour the mode manager gates.

    # Paper broker is only active in PAPER mode. Loaded lazily so the
    # import never affects OFF / LIVE / MAINTENANCE deployments.
    paper_broker = None
    if current_mode == "PAPER":
        try:
            from ml_service.trading import paper_broker
        except Exception as e:
            logger.error(f"Failed to load paper broker: {e}")
            paper_broker = None

    logger.info("="*80)
    logger.info("Starting signal generation job")
    logger.info("="*80)

    generated_count = 0
    failed_count = 0

    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            try:
                signal = generate_signal(symbol=symbol, timeframe=timeframe, persist=True)

                if signal:
                    logger.info(
                        f"Generated signal: {symbol} {timeframe} | "
                        f"Direction: {signal['direction']} | "
                        f"Confidence: {signal['confidence']}%"
                    )
                    generated_count += 1

                    # Signal has already been persisted to the DB inside
                    # generate_signal() -> save_signal_to_db(). Apply the
                    # quality filter before notifying; low-quality signals
                    # are logged and skipped. All notification/filter errors
                    # are swallowed so they never affect signal generation.
                    try:
                        should_send, reason = should_send_telegram_alert(signal)

                        if should_send:
                            send_signal_alert(signal)
                        else:
                            logger.info(
                                f"Telegram alert skipped: "
                                f"{signal.get('symbol')} {signal.get('timeframe')} "
                                f"(reason={reason})"
                            )
                    except Exception as notify_err:
                        logger.error(
                            f"Telegram alert failed for {symbol} {timeframe}: {notify_err}"
                        )

                    # ── Paper broker: open position on non-neutral signal ─
                    # Skips neutral, respects max positions and one-per-symbol.
                    if paper_broker is not None:
                        try:
                            paper_broker.open_paper_position(signal)
                        except Exception as pb_err:
                            logger.error(
                                f"Paper broker open failed for {symbol} {timeframe}: {pb_err}"
                            )

                else:
                    logger.warning(f"Failed to generate signal for {symbol} {timeframe}")
                    failed_count += 1

            except Exception as e:
                logger.error(f"Error generating signal for {symbol} {timeframe}: {e}")
                failed_count += 1

    logger.info(f"Signal generation complete: {generated_count} generated, {failed_count} failed")
    logger.info("="*80)


def outcome_evaluation_job():
    """Evaluate pending signal outcomes - runs every hour.

    Uses the new two-phase evaluation:
    Phase 1: Checkpoint monitoring (1h, 4h, 12h, 24h, 48h) for early WIN/LOSS.
             Checkpoint timeouts are NOT final -- signals stay pending.
    Phase 2: Final evaluation at 7-day expiry. TIMEOUT is only assigned
             after the full 7-day window is scanned.
    """
    from ml_service.analytics.outcome_engine import OutcomeEngine

    logger.info("Starting outcome evaluation job")

    try:
        engine = OutcomeEngine()
        stats = engine.evaluate_pending_outcomes(batch_size=100)

        logger.info(
            f"Outcome evaluation complete: {stats['evaluated']} finalized | "
            f"Wins: {stats['wins']} | Losses: {stats['losses']} | "
            f"Timeouts: {stats['timeouts']} | Still pending: {stats['still_pending']} | "
            f"Checkpoints scanned: {stats['checkpoints_scanned']} | "
            f"Failed: {stats['failed']}"
        )
    except Exception as e:
        logger.error(f"Outcome evaluation job failed: {e}")


def log_retrain_results(results):
    """Log retrain results to CSV."""
    RETRAIN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    file_exists = RETRAIN_LOG_PATH.exists()

    with open(RETRAIN_LOG_PATH, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'timestamp', 'symbol', 'timeframe', 'status', 'old_f1', 'new_f1', 'reason'
        ])

        if not file_exists:
            writer.writeheader()

        timestamp = datetime.now().isoformat()
        for result in results:
            writer.writerow({
                'timestamp': timestamp,
                'symbol': result['symbol'],
                'timeframe': result['timeframe'],
                'status': result['status'],
                'old_f1': result['old_f1'],
                'new_f1': result['new_f1'],
                'reason': result['reason'],
            })


def weekly_retrain_job():
    """Retrain tier-2 models — runs every Sunday at 03:00 UTC."""
    global _last_retrain_time, _last_retrain_results

    logger.info("Starting weekly tier-2 retrain...")
    _last_retrain_time = datetime.now()
    _last_retrain_results = []

    for symbol in TIER_2_SYMBOLS:
        for timeframe in TIMEFRAMES:
            try:
                df = load_data(symbol, timeframe)
                if df is None or len(df) < 100:
                    logger.warning(f"Insufficient data for {symbol} {timeframe}")
                    continue

                btc_1h = load_data('BTCUSDT', '1h')
                btc_4h = load_data('BTCUSDT', '4h')

                old_f1 = get_current_model_f1(symbol, timeframe)
                train_results = train_model(
                    df=df, symbol=symbol, timeframe=timeframe,
                    btc_df=btc_1h if timeframe == '1h' else btc_4h,
                    eth_df=None, spy_df=None, dominance_df=None,
                )
                new_f1 = train_results['avg_f1_weighted']
                governance_result = compare_and_promote(
                    candidate_path=train_results['model_path'],
                    symbol=symbol, timeframe=timeframe,
                    improvement_threshold=F1_THRESHOLD,
                )
                _last_retrain_results.append({
                    'symbol': symbol, 'timeframe': timeframe,
                    'status': governance_result.get('status', 'unknown'),
                    'reason': governance_result.get('reason', ''),
                    'old_f1': old_f1, 'new_f1': new_f1,
                })
            except Exception as e:
                logger.error(f"Weekly retrain failed for {symbol} {timeframe}: {e}")
                _last_retrain_results.append({
                    'symbol': symbol, 'timeframe': timeframe,
                    'status': 'failed', 'reason': str(e),
                    'old_f1': 0, 'new_f1': 0,
                })

    log_retrain_results(_last_retrain_results)
    logger.info("Weekly tier-2 retrain complete")


def trade_sync_job():
    """Sync trade history from Binance Futures + enrich with signals.

    Runs automatically on schedule (default every hour) and once on
    FastAPI startup so recently closed positions appear immediately.
    """
    from ml_service.data.exchange_sync import (
        sync_all_trades,
        save_trades_to_db,
        enrich_trades_with_signals,
        backfill_regimes,
    )
    from ml_service.utils.config import get_config
    import yaml
    from pathlib import Path

    try:
        config = get_config()
    except Exception:
        # Fallback: read config.yaml directly if dataclass parsing fails
        config = None

    # Resolve API credentials from exchange_sync config (or binance data_sources)
    api_key = None
    api_secret = None

    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f)

        ec = raw.get('exchange_sync', {})
        if ec.get('enabled'):
            api_key = ec.get('binance_api_key')
            api_secret = ec.get('binance_api_secret')

    if not api_key or not api_secret:
        logger.warning("Trade sync skipped: no Binance API credentials in exchange_sync config")
        return

    try:
        logger.info("Starting scheduled trade sync...")
        trades = sync_all_trades(api_key, api_secret)

        if not trades:
            logger.info("Trade sync complete: no new trades found")
            return

        inserted = save_trades_to_db(trades)
        logger.info(f"Trade sync: {len(trades)} fetched, {inserted} new inserts")

        # Re-enrich any newly inserted trades with signal data
        matched = enrich_trades_with_signals()
        logger.info(f"Trade sync enrichment: {matched} trades matched with signals")

        # Backfill regime for any matched trades still missing it (idempotent)
        backfilled = backfill_regimes()
        if backfilled:
            logger.info(f"Trade sync regime backfill: {backfilled} trades updated")

    except Exception as e:
        logger.error(f"Trade sync job failed: {e}")


_last_sync_time = None


def account_equity_snapshot_job():
    """Capture a Binance Futures equity snapshot every 5 minutes.

    Calls ``capture_account_equity_snapshot()`` which fetches from
    Binance and persists the result. Failures are swallowed and
    logged — never affects other scheduled jobs.
    """
    try:
        from ml_service.data.exchange_sync import capture_account_equity_snapshot
        result = capture_account_equity_snapshot()
        if result:
            logger.info(
                f"Account equity snapshot saved: "
                f"margin=${result['margin_balance']:.2f} "
                f"wallet=${result['wallet_balance']:.2f}"
            )
        else:
            logger.debug("Account equity snapshot skipped (Binance unavailable)")
    except Exception as e:
        logger.error(f"Account equity snapshot job failed: {e}")


def drift_snapshot_job():
    """Compute drift for all production models and persist snapshots.

    Runs every 60 minutes. For each symbol x timeframe pair, calls
    ``get_drift_report()`` and persists the result. Individual model
    failures are logged but never interrupt the remaining models.
    """
    from ml_service.analytics.drift_monitor import (
        get_drift_report,
        persist_drift_snapshot,
    )

    logger.info("Drift snapshot started")
    processed = 0
    failed = 0

    for symbol in TIER_1_SYMBOLS:
        for timeframe in TIMEFRAMES:
            try:
                report = get_drift_report(symbol, timeframe)
                if report:
                    ok = persist_drift_snapshot(symbol, timeframe, report)
                    if ok:
                        processed += 1
                    else:
                        failed += 1
                else:
                    failed += 1
                    logger.warning(
                        f"Drift snapshot: no report for {symbol} {timeframe}"
                    )
            except Exception as e:
                failed += 1
                logger.error(
                    f"Drift snapshot failed for {symbol} {timeframe}: {e}"
                )

    logger.info(
        f"Drift snapshot complete: {processed} saved, {failed} failed"
    )


def paper_lifecycle_job():
    """Paper broker lifecycle pass - runs every minute.

    Only executes when the trading mode is PAPER. Refreshes prices,
    evaluates TP / SL / expiration on open paper positions, and closes
    positions that need to close. Signal generation is NOT affected.
    """
    from ml_service.trading.mode_manager import get_trading_mode
    from ml_service.trading import paper_broker

    mode = get_trading_mode()
    if mode != "PAPER":
        logger.debug(f"Paper lifecycle skipped: mode={mode}")
        return

    logger.info("Paper broker lifecycle started")
    try:
        summary = paper_broker.update_open_positions()
        logger.info(
            f"Paper broker lifecycle complete: "
            f"checked={summary['checked']} tp={summary['tp']} "
            f"sl={summary['sl']} expired={summary['expired']}"
        )
    except Exception as e:
        logger.error(f"Paper broker lifecycle failed: {e}")


def paper_equity_snapshot_job():
    """Capture paper equity snapshot - runs every 5 minutes.

    Only executes when the trading mode is PAPER. Computes current
    equity and persists it to paper_equity_history.
    """
    from ml_service.trading.mode_manager import get_trading_mode
    from ml_service.trading import paper_broker

    mode = get_trading_mode()
    if mode != "PAPER":
        return

    try:
        paper_broker.capture_equity_snapshot()
    except Exception as e:
        logger.error(f"Paper equity snapshot failed: {e}")


def signal_lifecycle_job():
    """Evaluate ACTIVE signals for TP/SL/expiration - runs every 5 minutes.

    Queries ACTIVE signals with non-NULL valid_until, fetches current
    market prices, and transitions signals to TP_HIT, SL_HIT, or EXPIRED.
    """
    from ml_service.signal_lifecycle import bulk_update_signal_statuses
    from ml_service.trading.paper_broker import _fetch_mark_price

    logger.info("Signal lifecycle evaluation started")

    db = get_database()
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, symbol, timeframe, direction, signal_status,
                       take_profit, stop_loss, valid_until
                FROM signals
                WHERE signal_status = 'ACTIVE'
                  AND valid_until IS NOT NULL
                """
            )
            rows = cursor.fetchall()

        if not rows:
            logger.info("Signal lifecycle: no ACTIVE signals with valid_until")
            return

        items = []
        for row in rows:
            symbol = row[1]
            current_price = _fetch_mark_price(symbol)

            signal = {
                'signal_id': row[0],
                'symbol': symbol,
                'timeframe': row[2],
                'direction': row[3],
                'signal_status': row[4],
                'take_profit': row[5],
                'stop_loss': row[6],
                'valid_until': row[7],
            }
            items.append({'signal': signal, 'current_price': current_price})

        updated = bulk_update_signal_statuses(items)
        logger.info(
            f"Signal lifecycle complete: {len(rows)} evaluated, {updated} transitioned"
        )

    except Exception as e:
        logger.error(f"Signal lifecycle job failed: {e}")


def start_scheduler():
    """Start the background scheduler."""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler already running")
        return

    _scheduler = BackgroundScheduler(daemon=True)

    # ── Trade sync: runs every hour by default ──────────────────────
    sync_interval_hours = 1
    try:
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path) as f:
            raw = yaml.safe_load(f)
        sync_interval_hours = int(
            raw.get('exchange_sync', {}).get('sync_interval_hours', 1)
        )
    except Exception:
        pass

    _scheduler.add_job(
        trade_sync_job,
        trigger=IntervalTrigger(hours=sync_interval_hours),
        id='trade_sync_job',
        name=f'Sync Binance trades every {sync_interval_hours}h',
        replace_existing=True,
    )

    # ── Adaptive retrain (replaces static daily + weekly) ─────────────
    _scheduler.add_job(
        adaptive_retrain_job,
        trigger=IntervalTrigger(hours=24),
        id='adaptive_retrain_job',
        name='Adaptive drift-based retrain for all models',
        replace_existing=True,
    )

    _scheduler.add_job(
        market_dominance_job,
        trigger=IntervalTrigger(hours=1),
        id='market_dominance_job',
        name='Fetch market dominance from CoinGecko',
        replace_existing=True,
    )

    _scheduler.add_job(
        signal_generation_job,
        trigger=IntervalTrigger(hours=1),
        id='signal_generation_job',
        name='Generate signals for all symbols',
        replace_existing=True,
    )

    _scheduler.add_job(
        outcome_evaluation_job,
        trigger=IntervalTrigger(hours=1),
        id='outcome_evaluation_job',
        name='Evaluate pending signal outcomes',
        replace_existing=True,
    )

    _scheduler.add_job(
        account_equity_snapshot_job,
        trigger=IntervalTrigger(minutes=5),
        id='account_equity_snapshot_job',
        name='Capture Binance equity snapshot every 5 min',
        replace_existing=True,
    )

    _scheduler.add_job(
        drift_snapshot_job,
        trigger=IntervalTrigger(hours=1),
        id='drift_snapshot_job',
        name='Compute and persist drift snapshots every 1h',
        replace_existing=True,
    )

    _scheduler.add_job(
        paper_lifecycle_job,
        trigger=IntervalTrigger(minutes=1),
        id='paper_lifecycle_job',
        name='Paper broker lifecycle (TP/SL/expiry) every 1m',
        replace_existing=True,
    )

    _scheduler.add_job(
        paper_equity_snapshot_job,
        trigger=IntervalTrigger(minutes=5),
        id='paper_equity_snapshot_job',
        name='Capture paper equity snapshot every 5m',
        replace_existing=True,
    )

    _scheduler.add_job(
        signal_lifecycle_job,
        trigger=IntervalTrigger(minutes=5),
        id='signal_lifecycle_job',
        name='Evaluate signal lifecycle (expiration) every 5m',
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        f"Scheduler started - trade sync every {sync_interval_hours}h, "
        "adaptive retrain every 24h, dominance/signals/outcomes every 1h, "
        "account equity snapshot every 5m, drift snapshot every 1h, "
        "paper lifecycle every 1m, paper equity snapshot every 5m, "
        "signal lifecycle every 5m"
    )


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
    else:
        logger.warning("Scheduler not running")


def get_scheduler_status():
    """Get scheduler status information."""
    if _scheduler is None or not _scheduler.running:
        return {
            'running': False,
            'last_retrain': None,
            'next_retrain': None,
            'results': [],
        }

    next_run = _scheduler.get_job('adaptive_retrain_job').next_run_time if _scheduler.get_job('adaptive_retrain_job') else None

    return {
        'running': True,
        'last_retrain': _last_retrain_time.isoformat() if _last_retrain_time else None,
        'next_retrain': next_run.isoformat() if next_run else None,
        'results': _last_retrain_results,
    }
