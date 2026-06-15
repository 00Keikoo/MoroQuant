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
    timeframe: str = Query(..., description="Timeframe (e.g., 1h)")
) -> Dict:
    """Generate fresh trading signal for a symbol/timeframe."""
    signal = generate_signal(symbol=symbol, timeframe=timeframe)

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

    config_path = Path(__file__).parent.parent.parent / "config.yaml"

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
