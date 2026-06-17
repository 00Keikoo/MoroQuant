"""API routes for ML trading system."""

from fastapi import APIRouter, Query, Body
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml_service.models.predictor import generate_signal, calculate_tp_sl
from ml_service.data.database import get_database
from ml_service.services.crypto_price_service import get_crypto_service
from ml_service.services.proxy_price_service import get_proxy_service

router = APIRouter()


class ClosedTrade(BaseModel):
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    leverage: float
    size_usdt: float
    pnl: float
    pnl_pct: float
    opened_at: str
    closed_at: str
    notes: Optional[str] = None

CRYPTO_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'HYPEUSDT', 'ADAUSDT', 'XRPUSDT', 'LINKUSDT', 'LTCUSDT', 'ZECUSDT', 'SUIUSDT']
PROXY_SYMBOLS = ['ES_proxy', 'NQ_proxy', 'GC_proxy', 'CL_proxy', 'ZB_proxy']


@router.get("/signals")
async def get_signal(
    symbol: str = Query(..., description="Trading symbol (e.g., BTCUSDT)"),
    timeframe: str = Query(..., description="Timeframe (e.g., 1h)"),
    confidence_threshold: float = Query(0.60, description="Minimum confidence threshold (0.0-1.0)", ge=0.0, le=1.0)
) -> Dict:
    """Generate fresh trading signal for a symbol/timeframe with confidence filtering."""
    signal = generate_signal(
        symbol=symbol,
        timeframe=timeframe,
        confidence_threshold=confidence_threshold
    )

    if signal is None:
        return {
            "error": "Failed to generate signal",
            "symbol": symbol,
            "timeframe": timeframe,
            "message": "No trained model found or insufficient data"
        }

    # Always fetch fresh price and recalculate TP/SL based on live price
    fresh_price = None
    if symbol in CRYPTO_SYMBOLS:
        crypto_service = get_crypto_service()
        price_data = crypto_service.get_price(symbol)
        if price_data:
            fresh_price = price_data['price']
            signal['price'] = fresh_price
            signal['price_live'] = price_data.get('live', False)
        else:
            signal['price'] = signal.get('price', 0)
            signal['price_live'] = False
    elif symbol in PROXY_SYMBOLS:
        proxy_service = get_proxy_service()
        price_data = proxy_service.get_price(symbol)
        if price_data:
            fresh_price = price_data['price']
            signal['price'] = fresh_price
            signal['price_live'] = price_data.get('live', False)
        else:
            signal['price'] = signal.get('price', 0)
            signal['price_live'] = False
    else:
        signal['price'] = signal.get('price', 0)
        signal['price_live'] = False

    # Recalculate TP/SL with fresh price to ensure consistency
    if fresh_price and signal.get('atr') is not None and signal.get('direction') != 'neutral':
        tp, sl = calculate_tp_sl(
            fresh_price,
            signal['atr'],
            signal['direction'],
            signal.get('tp_multiplier', 3.0),
            signal.get('sl_multiplier', 1.5)
        )
        # Use more precision for low-priced assets
        decimal_places = 4 if fresh_price < 1.0 else 2
        signal['take_profit'] = round(tp, decimal_places) if tp else None
        signal['stop_loss'] = round(sl, decimal_places) if sl else None

    return signal


@router.get("/signals/history")
async def get_signal_history(
    symbol: str = Query(..., description="Trading symbol"),
    limit: int = Query(20, description="Number of signals to return")
) -> List[Dict]:
    """Get historical signals from database."""
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT symbol, timeframe, timestamp, direction, confidence,
                   features_json, created_at
            FROM signals
            WHERE symbol = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (symbol, limit)
        )

        rows = cursor.fetchall()

        signals = []
        for row in rows:
            signals.append({
                "symbol": row[0],
                "timeframe": row[1],
                "timestamp": row[2],
                "direction": row[3],
                "confidence": row[4],
                "features_json": row[5],
                "created_at": row[6],
            })

        return signals


@router.get("/db/info")
async def get_db_info() -> Dict:
    """Get database statistics (health check)."""
    db = get_database()
    info = db.db_info()

    return {
        "status": "healthy",
        "ohlcv_records": info["ohlcv"],
        "macro_events": info["macro_events"],
        "signals": info["signals"],
        "ohlcv_breakdown": info["ohlcv_breakdown"]
    }


@router.get("/symbols")
async def get_symbols() -> Dict:
    """Get list of all symbols with data in database."""
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT symbol, timeframe, COUNT(*) as candle_count
            FROM ohlcv
            GROUP BY symbol, timeframe
            ORDER BY symbol, timeframe
            """
        )

        rows = cursor.fetchall()

        symbols = {}
        for row in rows:
            symbol = row[0]
            if symbol not in symbols:
                symbols[symbol] = []

            symbols[symbol].append({
                "timeframe": row[1],
                "candle_count": row[2]
            })

        return {
            "symbols": symbols,
            "total_symbols": len(symbols)
        }


@router.get("/backtest/{symbol}/{timeframe}")
async def get_backtest_results(symbol: str, timeframe: str) -> Dict:
    """Get backtest equity curve and metrics for a symbol/timeframe."""
    from pathlib import Path
    import json

    storage_dir = Path(__file__).parent.parent / "storage" / "backtest"
    equity_file = storage_dir / f"{symbol}_{timeframe}_equity.json"
    trades_file = storage_dir / f"{symbol}_{timeframe}_trades.csv"

    if not equity_file.exists():
        return {
            "error": "no_data",
            "symbol": symbol,
            "timeframe": timeframe,
            "message": f"Run backtest first: python cli.py backtest --symbol {symbol} --timeframe {timeframe}"
        }

    try:
        with open(equity_file, 'r') as f:
            equity_data = json.load(f)

        trades_data = []
        if trades_file.exists():
            import pandas as pd
            trades_df = pd.read_csv(trades_file)
            trades_data = trades_df.to_dict('records')

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "equity_curve": equity_data,
            "trades": trades_data,
            "trade_count": len(trades_data)
        }
    except Exception as e:
        return {
            "error": "parse_error",
            "symbol": symbol,
            "timeframe": timeframe,
            "message": f"Error loading backtest data: {str(e)}"
        }


@router.post("/trades/close")
async def close_trade(trade: ClosedTrade) -> Dict:
    """Save a closed trade to the database."""
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_trades (
                symbol, direction, entry_price, exit_price, leverage,
                size_usdt, pnl, pnl_pct, opened_at, closed_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade.symbol,
                trade.direction,
                trade.entry_price,
                trade.exit_price,
                trade.leverage,
                trade.size_usdt,
                trade.pnl,
                trade.pnl_pct,
                trade.opened_at,
                trade.closed_at,
                trade.notes,
            )
        )

        return {
            "status": "success",
            "message": "Trade closed and saved",
            "trade_id": cursor.lastrowid
        }


@router.get("/trades/history")
async def get_trade_history() -> Dict:
    """Get all closed trades from database."""
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, symbol, direction, entry_price, exit_price, leverage,
                   size_usdt, pnl, pnl_pct, opened_at, closed_at, notes, created_at
            FROM user_trades
            ORDER BY closed_at DESC
            """
        )

        rows = cursor.fetchall()

        trades = []
        for row in rows:
            trades.append({
                "id": row[0],
                "symbol": row[1],
                "direction": row[2],
                "entry_price": row[3],
                "exit_price": row[4],
                "leverage": row[5],
                "size_usdt": row[6],
                "pnl": row[7],
                "pnl_pct": row[8],
                "opened_at": row[9],
                "closed_at": row[10],
                "notes": row[11],
                "created_at": row[12],
            })

        total_pnl = sum(t["pnl"] for t in trades)
        winning_trades = [t for t in trades if t["pnl"] > 0]
        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
        best_trade = max(trades, key=lambda t: t["pnl"]) if trades else None
        worst_trade = min(trades, key=lambda t: t["pnl"]) if trades else None

        return {
            "trades": trades,
            "summary": {
                "total_pnl": round(total_pnl, 2),
                "win_rate": round(win_rate, 2),
                "total_trades": len(trades),
                "best_trade": best_trade,
                "worst_trade": worst_trade,
            }
        }


@router.get("/positions/open")
async def get_open_positions() -> Dict:
    """Get open positions from Binance Futures with ML signal comparison."""
    from ..data.exchange_sync import fetch_open_positions, get_position_signal_comparison
    import yaml
    from pathlib import Path

    config_path = Path(__file__).parent.parent / "config.yaml"

    if not config_path.exists():
        return {
            "error": "config_not_found",
            "message": "config.yaml not found - exchange sync not configured"
        }

    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    exchange_config = config_data.get('exchange_sync', {})

    if not exchange_config.get('enabled'):
        return {
            "error": "exchange_sync_disabled",
            "message": "Exchange sync is disabled in config.yaml"
        }

    api_key = exchange_config.get('binance_api_key')
    api_secret = exchange_config.get('binance_api_secret')

    if not api_key or not api_secret:
        return {
            "error": "credentials_missing",
            "message": "Binance API credentials not configured"
        }

    positions = fetch_open_positions(api_key, api_secret)

    if not positions:
        return {
            "positions": [],
            "total_unrealized_pnl": 0,
            "count": 0
        }

    enriched = get_position_signal_comparison(positions)

    total_unrealized_pnl = sum(p['unrealized_pnl'] for p in enriched)

    return {
        "positions": enriched,
        "total_unrealized_pnl": round(total_unrealized_pnl, 2),
        "count": len(enriched)
    }


@router.get("/analytics/live-performance")
async def get_live_performance(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    days_back: Optional[int] = Query(None, description="Days to look back")
) -> Dict:
    """Get live trading performance metrics from synced Binance trades."""
    from analytics.live_metrics import compute_live_metrics, get_equity_curve

    metrics = compute_live_metrics(symbol=symbol, days_back=days_back)

    if metrics['status'] == 'success':
        equity_curve = get_equity_curve(symbol=symbol, days_back=days_back)
        metrics['equity_curve'] = equity_curve

    return metrics


@router.get("/analytics/regimes")
async def get_regime_performance(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    days_back: Optional[int] = Query(None, description="Days to look back")
) -> Dict:
    """Get performance metrics grouped by market regime."""
    from analytics.regime_performance import compute_regime_performance, get_regime_distribution

    metrics = compute_regime_performance(symbol=symbol, days_back=days_back)

    if metrics['status'] == 'success':
        distribution = get_regime_distribution(symbol=symbol, days_back=days_back)
        metrics['distribution'] = distribution

    return metrics


@router.get("/analytics/confidence")
async def get_confidence_performance(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    days_back: Optional[int] = Query(None, description="Days to look back")
) -> Dict:
    """Get performance metrics grouped by confidence buckets."""
    from analytics.confidence_report import compute_confidence_performance, analyze_confidence_correlation

    metrics = compute_confidence_performance(symbol=symbol, days_back=days_back)

    if metrics['status'] == 'success':
        correlation = analyze_confidence_correlation(symbol=symbol, days_back=days_back)
        metrics['correlation_analysis'] = correlation

    return metrics


@router.get("/analytics/trade-history")
async def get_enhanced_trade_history(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(100, description="Number of trades to return")
) -> Dict:
    """Get enhanced trade history with signal attribution."""
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
                uth.id,
                uth.symbol,
                uth.side,
                uth.price,
                uth.qty,
                uth.realized_pnl,
                uth.commission,
                uth.trade_time,
                uth.matched_signal_id,
                uth.market_regime,
                uth.confidence_at_entry,
                s.direction as signal_direction,
                s.tp_multiplier,
                s.sl_multiplier,
                s.labeling_method
            FROM user_trade_history uth
            LEFT JOIN signals s ON uth.matched_signal_id = s.id
            WHERE 1=1
        """
        params = []

        if symbol:
            query += " AND uth.symbol = ?"
            params.append(symbol)

        query += " ORDER BY uth.trade_time DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        trades = []
        for row in rows:
            trade = {
                "id": row[0],
                "symbol": row[1],
                "side": row[2],
                "price": row[3],
                "qty": row[4],
                "realized_pnl": row[5],
                "commission": row[6],
                "net_pnl": row[5] - row[6],
                "trade_time": row[7],
                "matched_signal_id": row[8],
                "market_regime": row[9],
                "confidence_at_entry": row[10],
                "signal_direction": row[11],
                "tp_multiplier": row[12],
                "sl_multiplier": row[13],
                "labeling_method": row[14],
            }
            trades.append(trade)

    return {
        "trades": trades,
        "count": len(trades),
        "timestamp": datetime.now().isoformat()
    }
