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
def fetch(symbol: Optional[str], timeframe: Optional[str], days: int, fetch_all_flag: bool, source: str):
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
            inserted, skipped = ingest_binance_symbol(symbol, timeframe, days)
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


if __name__ == "__main__":
    cli()
