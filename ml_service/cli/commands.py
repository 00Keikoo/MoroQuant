"""CLI commands for ML trading system."""

import click
from typing import Optional

from ..utils.logger import setup_logger, get_logger
from ..utils.config import get_config
from ..data.database import get_database
from ..data.ingestion import (
    ingest_binance_symbol,
    ingest_yfinance_symbol,
    fetch_all,
)

setup_logger()
logger = get_logger()


@click.group()
def cli():
    """ML Trading Intelligence System CLI"""
    pass


@cli.command()
@click.option("--symbol", help="Trading symbol (e.g., BTCUSDT)")
@click.option("--timeframe", help="Timeframe (e.g., 1h)")
@click.option("--days", default=30, help="Days of history to fetch")
@click.option("--all", "fetch_all_flag", is_flag=True, help="Fetch all configured symbols")
@click.option("--source", type=click.Choice(["binance", "yfinance", "both"]), default="both")
@click.option("--full-history", is_flag=True, help="Fetch from beginning regardless of DB state")
def fetch(symbol: Optional[str], timeframe: Optional[str], days: int, fetch_all_flag: bool, source: str, full_history: bool):
    """Fetch OHLCV data from Binance and/or Yahoo Finance."""

    if fetch_all_flag:
        logger.info(f"Fetching all configured symbols (last {days} days)")
        stats = fetch_all(days_back=days)

        click.echo("\n" + "="*60)
        click.echo("INGESTION SUMMARY")
        click.echo("="*60)

        for source_name, source_stats in stats.items():
            click.echo(f"\n{source_name.upper()}:")
            for sym, timeframes in source_stats.items():
                click.echo(f"  {sym}:")
                for tf, result in timeframes.items():
                    if "error" in result:
                        click.echo(f"    {tf}: ERROR - {result['error']}")
                    else:
                        click.echo(f"    {tf}: {result['inserted']} inserted, {result['skipped']} skipped")

        click.echo("="*60 + "\n")

        db = get_database()
        db.print_db_info()
        return

    if not symbol or not timeframe:
        click.echo("Error: --symbol and --timeframe are required (or use --all)")
        return

    config = get_config()

    if source in ["binance", "both"]:
        if symbol in config.data_sources.binance.symbols:
            inserted, skipped = ingest_binance_symbol(symbol, timeframe, days, fetch_from_beginning=full_history)
            click.echo(f"\nBinance {symbol} {timeframe}: {inserted} inserted, {skipped} skipped")
        else:
            click.echo(f"Warning: {symbol} not in Binance config")

    if source in ["yfinance", "both"]:
        if symbol in config.data_sources.yfinance.symbols:
            inserted, skipped = ingest_yfinance_symbol(symbol, timeframe, days)
            click.echo(f"\nyfinance {symbol} {timeframe}: {inserted} inserted, {skipped} skipped")
        else:
            click.echo(f"Warning: {symbol} not in yfinance config")

    db = get_database()
    db.print_db_info()


@cli.command("db-info")
def db_info():
    """Show database statistics."""
    db = get_database()
    db.print_db_info()


@cli.command()
@click.option("--symbol", required=True, help="Trading symbol")
@click.option("--timeframe", required=True, help="Timeframe")
@click.option("--retrain", is_flag=True, help="Force retrain even if model exists")
def train(symbol: str, timeframe: str, retrain: bool):
    """Train ML model for a symbol/timeframe."""
    from ..models.trainer import train_model as train_ml_model
    from ..data.database import get_database
    import pandas as pd

    click.echo(f"\nTraining model for {symbol} {timeframe}...")

    db = get_database()
    with db.get_connection() as conn:
        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp ASC
        """
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe))

    if df.empty:
        click.echo(f"\n❌ No data found for {symbol} {timeframe}")
        return

    click.echo(f"Loaded {len(df)} candles")

    btc_df = None
    spy_df = None

    with db.get_connection() as conn:
        try:
            btc_query = """
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = 'BTCUSDT' AND timeframe = ?
                ORDER BY timestamp ASC
            """
            btc_df = pd.read_sql_query(btc_query, conn, params=(timeframe,))
            if not btc_df.empty:
                click.echo(f"Loaded {len(btc_df)} BTC candles for correlation")
        except Exception as e:
            click.echo(f"Warning: Could not load BTC data for correlation: {e}")

        try:
            spy_query = """
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = 'ES_proxy' AND timeframe = ?
                ORDER BY timestamp ASC
            """
            spy_df = pd.read_sql_query(spy_query, conn, params=(timeframe,))
            if not spy_df.empty:
                click.echo(f"Loaded {len(spy_df)} ES_proxy candles for correlation")
        except Exception as e:
            click.echo(f"Warning: Could not load ES_proxy data for correlation: {e}")

    try:
        results = train_ml_model(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            btc_df=btc_df if btc_df is not None and not btc_df.empty else None,
            spy_df=spy_df if spy_df is not None and not spy_df.empty else None,
            forward_periods=12,
            long_threshold=0.005,
            short_threshold=-0.005,
        )

        click.echo("\n" + "=" * 80)
        click.echo("TRAINING COMPLETE")
        click.echo("=" * 80)
        click.echo(f"Model: {results['model_type']}")
        click.echo(f"Folds: {results['n_folds']}")
        click.echo(f"\nF1 Scores:")
        click.echo(f"  Short:   {results['avg_f1_short']:.3f}")
        click.echo(f"  Neutral: {results['avg_f1_neutral']:.3f}")
        click.echo(f"  Long:    {results['avg_f1_long']:.3f}")
        click.echo(f"  Weighted: {results['avg_f1_weighted']:.3f}")
        click.echo(f"\nModel saved: {results['model_path']}")
        click.echo("=" * 80 + "\n")

    except Exception as e:
        click.echo(f"\n❌ Training failed: {str(e)}")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option("--symbol", required=True, help="Trading symbol")
@click.option("--timeframe", required=True, help="Timeframe")
@click.option("--explain", is_flag=True, help="Show feature importance")
def signal(symbol: str, timeframe: str, explain: bool):
    """Generate trading signal for a symbol/timeframe."""
    from ..models.predictor import generate_signal as gen_signal
    import json

    click.echo(f"\nGenerating signal for {symbol} {timeframe}...")

    result = gen_signal(symbol=symbol, timeframe=timeframe)

    if result is None:
        click.echo("\n❌ Failed to generate signal")
        click.echo("Possible reasons:")
        click.echo("  - No trained model found (run 'train' command first)")
        click.echo("  - Insufficient data in database")
        return

    click.echo("\n" + "=" * 80)
    click.echo("SIGNAL GENERATED")
    click.echo("=" * 80)
    click.echo(f"Symbol:     {result['symbol']} {result['timeframe']}")
    click.echo(f"Direction:  {result['direction'].upper()}")
    click.echo(f"Confidence: {result['confidence']}%")
    click.echo(f"Price:      ${result['price']:,.2f}")
    click.echo(f"Regime:     {result['regime']}")
    click.echo(f"Model:      {result['model_type']}")

    if explain or result['top_features']:
        click.echo(f"\nTop 5 Features:")
        for feature, importance in result['top_features'].items():
            click.echo(f"  {feature:30s}: {importance:.4f}")

    click.echo(f"\nGenerated at: {result['generated_at']}")
    click.echo("=" * 80 + "\n")


@cli.command()
@click.option("--symbol", help="Trading symbol (e.g., BTCUSDT)")
@click.option("--timeframe", help="Timeframe (e.g., 1h, 4h)")
@click.option("--trials", default=50, help="Number of Optuna trials (default: 50)")
@click.option("--all", "tune_all", is_flag=True, help="Tune all configured symbols")
def tune(symbol: Optional[str], timeframe: Optional[str], trials: int, tune_all: bool):
    """Tune hyperparameters for XGBoost and LightGBM models."""
    from ..models.tuner import (
        tune_hyperparameters,
        save_tuned_params,
        get_baseline_f1,
    )
    from ..models.trainer import prepare_features, create_target_variable, get_feature_columns
    from ..data.database import get_database
    from ..utils.config import get_config
    import pandas as pd

    if tune_all:
        config = get_config()
        symbols = config.data_sources.binance.symbols
        timeframes = ['1h', '4h']

        click.echo(f"\nTuning hyperparameters for all symbols...")
        click.echo(f"Symbols: {', '.join(symbols)}")
        click.echo(f"Timeframes: {', '.join(timeframes)}")
        click.echo(f"Trials per model: {trials}")
        click.echo("\n" + "=" * 80)

        results_summary = []

        for sym in symbols:
            for tf in timeframes:
                click.echo(f"\nTuning {sym} {tf}...")

                try:
                    db = get_database()
                    with db.get_connection() as conn:
                        query = """
                            SELECT timestamp, open, high, low, close, volume
                            FROM ohlcv
                            WHERE symbol = ? AND timeframe = ?
                            ORDER BY timestamp ASC
                        """
                        df = pd.read_sql_query(query, conn, params=(sym, tf))

                    if df.empty:
                        click.echo(f"  ❌ No data found for {sym} {tf}")
                        results_summary.append({
                            'symbol': sym,
                            'timeframe': tf,
                            'status': 'no_data',
                        })
                        continue

                    df = prepare_features(df, symbol=sym)
                    df = create_target_variable(df)
                    feature_cols = get_feature_columns(df)

                    df_clean = df[feature_cols + ['target']].dropna()
                    clean_size = len(df_clean)

                    if clean_size < 300:
                        min_train_size = int(clean_size * 0.7)
                        test_size = int(clean_size * 0.15)
                        step_size = test_size
                    else:
                        min_train_size = 400
                        test_size = 50
                        step_size = 50

                    baseline_xgb = get_baseline_f1(df, feature_cols, 'xgboost', min_train_size, test_size, step_size)
                    result_xgb = tune_hyperparameters(df, feature_cols, 'xgboost', trials, min_train_size, test_size, step_size)

                    baseline_lgb = get_baseline_f1(df, feature_cols, 'lightgbm', min_train_size, test_size, step_size)
                    result_lgb = tune_hyperparameters(df, feature_cols, 'lightgbm', trials, min_train_size, test_size, step_size)

                    if result_xgb['best_f1'] >= result_lgb['best_f1']:
                        best_result = result_xgb
                        baseline = baseline_xgb
                    else:
                        best_result = result_lgb
                        baseline = baseline_lgb

                    save_tuned_params(best_result, sym, tf)

                    improvement = ((best_result['best_f1'] - baseline) / baseline) * 100

                    click.echo(f"  ✓ Best model: {best_result['model_type']}")
                    click.echo(f"    Baseline F1: {baseline:.4f}")
                    click.echo(f"    Tuned F1:    {best_result['best_f1']:.4f}")
                    click.echo(f"    Improvement: {improvement:+.2f}%")
                    click.echo(f"    Time:        {best_result['elapsed_seconds']:.1f}s")

                    results_summary.append({
                        'symbol': sym,
                        'timeframe': tf,
                        'status': 'success',
                        'model_type': best_result['model_type'],
                        'baseline_f1': baseline,
                        'tuned_f1': best_result['best_f1'],
                        'improvement_pct': improvement,
                    })

                except Exception as e:
                    click.echo(f"  ❌ Error: {str(e)}")
                    results_summary.append({
                        'symbol': sym,
                        'timeframe': tf,
                        'status': 'error',
                    })

        click.echo("\n" + "=" * 80)
        click.echo("TUNING SUMMARY")
        click.echo("=" * 80)
        click.echo(f"{'Symbol':<12} {'TF':<4} {'Model':<10} {'Baseline':<10} {'Tuned':<10} {'Improv %':<10}")
        click.echo("-" * 80)

        for r in results_summary:
            if r['status'] == 'success':
                click.echo(
                    f"{r['symbol']:<12} {r['timeframe']:<4} {r['model_type']:<10} "
                    f"{r['baseline_f1']:<10.4f} {r['tuned_f1']:<10.4f} {r['improvement_pct']:>+9.2f}"
                )
            else:
                click.echo(f"{r['symbol']:<12} {r['timeframe']:<4} {r['status'].upper()}")

        click.echo("=" * 80 + "\n")
        return

    if not symbol or not timeframe:
        click.echo("Error: --symbol and --timeframe are required (or use --all)")
        return

    click.echo(f"\nTuning hyperparameters for {symbol} {timeframe}...")
    click.echo(f"Trials: {trials}")

    try:
        db = get_database()
        with db.get_connection() as conn:
            query = """
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp ASC
            """
            df = pd.read_sql_query(query, conn, params=(symbol, timeframe))

        if df.empty:
            click.echo(f"\n❌ No data found for {symbol} {timeframe}")
            return

        click.echo(f"Loaded {len(df)} candles")

        df = prepare_features(df, symbol=symbol)
        df = create_target_variable(df)
        feature_cols = get_feature_columns(df)

        df_clean = df[feature_cols + ['target']].dropna()
        clean_size = len(df_clean)

        if clean_size < 300:
            min_train_size = int(clean_size * 0.7)
            test_size = int(clean_size * 0.15)
            step_size = test_size
        else:
            min_train_size = 400
            test_size = 50
            step_size = 50

        click.echo(f"\nTuning XGBoost...")
        baseline_xgb = get_baseline_f1(df, feature_cols, 'xgboost', min_train_size, test_size, step_size)
        result_xgb = tune_hyperparameters(df, feature_cols, 'xgboost', trials, min_train_size, test_size, step_size)

        click.echo(f"\nTuning LightGBM...")
        baseline_lgb = get_baseline_f1(df, feature_cols, 'lightgbm', min_train_size, test_size, step_size)
        result_lgb = tune_hyperparameters(df, feature_cols, 'lightgbm', trials, min_train_size, test_size, step_size)

        if result_xgb['best_f1'] >= result_lgb['best_f1']:
            best_result = result_xgb
            baseline = baseline_xgb
        else:
            best_result = result_lgb
            baseline = baseline_lgb

        save_tuned_params(best_result, symbol, timeframe)

        improvement = ((best_result['best_f1'] - baseline) / baseline) * 100

        click.echo("\n" + "=" * 80)
        click.echo("TUNING COMPLETE")
        click.echo("=" * 80)
        click.echo(f"Symbol:      {symbol} {timeframe}")
        click.echo(f"Best Model:  {best_result['model_type']}")
        click.echo(f"Trials:      {trials}")
        click.echo(f"\nBaseline F1: {baseline:.4f}")
        click.echo(f"Tuned F1:    {best_result['best_f1']:.4f}")
        click.echo(f"Improvement: {improvement:+.2f}%")
        click.echo(f"\nTime taken:  {best_result['elapsed_seconds']:.1f}s")
        click.echo(f"\nBest Parameters:")
        for param, value in best_result['best_params'].items():
            click.echo(f"  {param:20s}: {value}")
        click.echo("=" * 80 + "\n")

    except Exception as e:
        click.echo(f"\n❌ Tuning failed: {str(e)}")
        import traceback
        traceback.print_exc()


@cli.command("optimize-tp-sl")
@click.option("--symbol", help="Trading symbol (e.g., BTCUSDT)")
@click.option("--timeframe", help="Timeframe (e.g., 1h, 4h)")
@click.option("--all", "optimize_all", is_flag=True, help="Optimize all symbols with backtest data")
def optimize_tp_sl(symbol: Optional[str], timeframe: Optional[str], optimize_all: bool):
    """Optimize TP/SL multipliers based on backtest history."""
    from ..models.tp_sl_optimizer import optimize_tp_sl, save_optimized_params
    from ..utils.config import get_config
    from pathlib import Path

    if optimize_all:
        backtest_dir = Path(__file__).parent.parent / "storage" / "backtest"
        if not backtest_dir.exists():
            click.echo("\n❌ No backtest directory found. Run backtests first:")
            click.echo("  python cli.py backtest --all")
            return

        trade_files = list(backtest_dir.glob("*_trades.csv"))
        if not trade_files:
            click.echo("\n❌ No backtest data found. Run backtests first:")
            click.echo("  python cli.py backtest --all")
            return

        symbol_tf_pairs = set()
        for f in trade_files:
            parts = f.stem.replace("_trades", "").rsplit("_", 1)
            if len(parts) == 2:
                symbol_tf_pairs.add((parts[0], parts[1]))

        click.echo(f"\nOptimizing TP/SL for {len(symbol_tf_pairs)} symbol/timeframe pairs...")
        click.echo("=" * 80)

        results_summary = []

        for sym, tf in sorted(symbol_tf_pairs):
            click.echo(f"\n{sym} {tf}:")

            try:
                result = optimize_tp_sl(sym, tf)

                if result is None:
                    click.echo("  ❌ Insufficient data for optimization")
                    results_summary.append({
                        'symbol': sym,
                        'timeframe': tf,
                        'status': 'failed',
                    })
                    continue

                save_optimized_params(result, sym, tf)

                click.echo(f"  ✓ TP Multiplier:  {result['tp_multiplier']}x ATR (default: 3.0x)")
                click.echo(f"  ✓ SL Multiplier:  {result['sl_multiplier']}x ATR (default: 1.5x)")
                click.echo(f"  ✓ Optimal Hold:   {result['optimal_hold_candles']} candles (default: 12)")
                click.echo(f"  ✓ Win Rate:       {result['win_rate_at_these_levels']:.1%}")
                click.echo(f"  ✓ Sample Size:    {result['sample_size']} trades")

                results_summary.append({
                    'symbol': sym,
                    'timeframe': tf,
                    'status': 'success',
                    'tp_mult': result['tp_multiplier'],
                    'sl_mult': result['sl_multiplier'],
                    'hold': result['optimal_hold_candles'],
                    'win_rate': result['win_rate_at_these_levels'],
                })

            except Exception as e:
                click.echo(f"  ❌ Error: {str(e)}")
                results_summary.append({
                    'symbol': sym,
                    'timeframe': tf,
                    'status': 'error',
                })

        click.echo("\n" + "=" * 80)
        click.echo("OPTIMIZATION SUMMARY")
        click.echo("=" * 80)
        click.echo(f"{'Symbol':<12} {'TF':<4} {'TP Mult':<9} {'SL Mult':<9} {'Hold':<6} {'Win %':<8}")
        click.echo("-" * 80)

        for r in results_summary:
            if r['status'] == 'success':
                click.echo(
                    f"{r['symbol']:<12} {r['timeframe']:<4} "
                    f"{r['tp_mult']:<9.2f} {r['sl_mult']:<9.2f} "
                    f"{r['hold']:<6} {r['win_rate']*100:<7.1f}"
                )
            else:
                click.echo(f"{r['symbol']:<12} {r['timeframe']:<4} {r['status'].upper()}")

        click.echo("=" * 80 + "\n")
        return

    if not symbol or not timeframe:
        click.echo("Error: --symbol and --timeframe are required (or use --all)")
        return

    click.echo(f"\nOptimizing TP/SL for {symbol} {timeframe}...")

    try:
        result = optimize_tp_sl(symbol, timeframe)

        if result is None:
            click.echo("\n❌ Optimization failed")
            click.echo("Possible reasons:")
            click.echo("  - No backtest data found (run backtest first)")
            click.echo("  - Insufficient trades in backtest history")
            click.echo(f"\nRun backtest first:")
            click.echo(f"  python cli.py backtest --symbol {symbol} --timeframe {timeframe}")
            return

        save_optimized_params(result, symbol, timeframe)

        click.echo("\n" + "=" * 80)
        click.echo("TP/SL OPTIMIZATION COMPLETE")
        click.echo("=" * 80)
        click.echo(f"Symbol:           {symbol} {timeframe}")
        click.echo(f"\nOptimized Values:")
        click.echo(f"  TP Multiplier:  {result['tp_multiplier']}x ATR (default: 3.0x)")
        click.echo(f"  SL Multiplier:  {result['sl_multiplier']}x ATR (default: 1.5x)")
        click.echo(f"  Optimal Hold:   {result['optimal_hold_candles']} candles (default: 12)")
        click.echo(f"  Risk:Reward:    1:{result['tp_multiplier']/result['sl_multiplier']:.1f}")
        click.echo(f"\nStatistics:")
        click.echo(f"  Win Rate:       {result['win_rate_at_these_levels']:.1%}")
        click.echo(f"  Sample Size:    {result['sample_size']} trades")
        click.echo(f"  TP Range:       {result['tp_multiplier_p25']:.2f}x - {result['tp_multiplier_p75']:.2f}x (25th-75th percentile)")
        click.echo(f"  SL Range:       {result['sl_multiplier_p25']:.2f}x - {result['sl_multiplier_p75']:.2f}x (25th-75th percentile)")
        click.echo(f"\nLast Updated:   {result['last_updated']}")
        click.echo("=" * 80 + "\n")

    except Exception as e:
        click.echo(f"\n❌ Optimization failed: {str(e)}")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option("--start", "action", flag_value="start", help="Start the scheduler")
@click.option("--status", "action", flag_value="status", help="Show scheduler status")
def scheduler(action: str):
    """Manage the auto-retrain scheduler."""
    from ..scheduler import start_scheduler, get_scheduler_status
    import json

    if action == "start":
        click.echo("Starting auto-retrain scheduler...")
        start_scheduler()
        click.echo("✓ Scheduler started - will retrain models every 24 hours")
        click.echo("\nKeep this process running. Press Ctrl+C to stop.")

        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n\nStopping scheduler...")
            from ..scheduler import stop_scheduler
            stop_scheduler()
            click.echo("✓ Scheduler stopped")

    elif action == "status":
        status = get_scheduler_status()

        click.echo("\n" + "=" * 80)
        click.echo("SCHEDULER STATUS")
        click.echo("=" * 80)
        click.echo(f"Running: {'Yes' if status['running'] else 'No'}")

        if status['last_retrain']:
            click.echo(f"Last retrain: {status['last_retrain']}")
        else:
            click.echo("Last retrain: Never")

        if status['running'] and status['next_retrain']:
            click.echo(f"Next retrain: {status['next_retrain']}")

        if status['results']:
            click.echo("\nLast Retrain Results:")
            click.echo(f"{'Symbol':<12} {'TF':<4} {'Status':<10} {'Old F1':<10} {'New F1':<10}")
            click.echo("-" * 80)
            for r in status['results']:
                click.echo(f"{r['symbol']:<12} {r['timeframe']:<4} {r['status']:<10} {r['old_f1']:<10.4f} {r['new_f1']:<10.4f}")

        click.echo("=" * 80 + "\n")

    else:
        click.echo("Error: Use --start or --status")


@cli.command()
@click.option("--symbol", help="Trading symbol (e.g., BTCUSDT)")
@click.option("--timeframe", help="Timeframe (e.g., 1h, 4h)")
@click.option("--all", "backtest_all", is_flag=True, help="Backtest all trained models")
def backtest(symbol: Optional[str], timeframe: Optional[str], backtest_all: bool):
    """Run backtests on historical data with walk-forward validation."""
    from ..backtester import run_backtest, print_backtest_summary
    from ..utils.config import get_config

    if backtest_all:
        config = get_config()

        symbols = config.data_sources.binance.symbols
        timeframes = ['1h', '4h']

        click.echo(f"\nRunning backtests for all symbol/timeframe combinations...")
        click.echo(f"Symbols: {', '.join(symbols)}")
        click.echo(f"Timeframes: {', '.join(timeframes)}")
        click.echo("\n" + "=" * 80)

        results_summary = []

        for sym in symbols:
            for tf in timeframes:
                click.echo(f"\nBacktesting {sym} {tf}...")

                try:
                    results = run_backtest(symbol=sym, timeframe=tf)

                    if results is None:
                        click.echo(f"  ❌ Failed (no model or insufficient data)")
                        results_summary.append({
                            'symbol': sym,
                            'timeframe': tf,
                            'status': 'failed',
                        })
                    else:
                        print_backtest_summary(results)
                        results_summary.append({
                            'symbol': sym,
                            'timeframe': tf,
                            'status': 'success',
                            'metrics': results['metrics'],
                        })

                except Exception as e:
                    click.echo(f"  ❌ Error: {str(e)}")
                    results_summary.append({
                        'symbol': sym,
                        'timeframe': tf,
                        'status': 'error',
                    })

        click.echo("\n" + "=" * 80)
        click.echo("BACKTEST SUMMARY - ALL SYMBOLS")
        click.echo("=" * 80)
        click.echo(f"{'Symbol':<12} {'TF':<4} {'Return %':<10} {'Win %':<8} {'Trades':<8} {'Sharpe':<8}")
        click.echo("-" * 80)

        for r in results_summary:
            if r['status'] == 'success':
                m = r['metrics']
                click.echo(
                    f"{r['symbol']:<12} {r['timeframe']:<4} "
                    f"{m['total_return_pct']:>9.2f} {m['win_rate_pct']:>7.2f} "
                    f"{m['total_trades']:>7} {m['sharpe_ratio']:>7.2f}"
                )
            else:
                click.echo(f"{r['symbol']:<12} {r['timeframe']:<4} {r['status'].upper()}")

        click.echo("=" * 80 + "\n")
        return

    if not symbol or not timeframe:
        click.echo("Error: --symbol and --timeframe are required (or use --all)")
        return

    click.echo(f"\nRunning backtest for {symbol} {timeframe}...")

    try:
        results = run_backtest(symbol=symbol, timeframe=timeframe)

        if results is None:
            click.echo("\n❌ Backtest failed")
            click.echo("Possible reasons:")
            click.echo("  - No trained model found (run 'train' command first)")
            click.echo("  - Insufficient historical data (need at least 200 candles)")
            return

        print_backtest_summary(results)

        click.echo(f"Equity curve saved: storage/backtest/{symbol}_{timeframe}_equity.json")
        click.echo(f"Trade log saved: storage/backtest/{symbol}_{timeframe}_trades.csv")

    except Exception as e:
        click.echo(f"\n❌ Backtest error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    cli()
