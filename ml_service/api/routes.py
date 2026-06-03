"""API routes for ML trading system."""

from fastapi import APIRouter, Query
from typing import List, Dict, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml_service.models.predictor import generate_signal
from ml_service.data.database import get_database
from ml_service.services.crypto_price_service import get_crypto_service
from ml_service.services.proxy_price_service import get_proxy_service

router = APIRouter()

CRYPTO_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
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

    if symbol in CRYPTO_SYMBOLS:
        crypto_service = get_crypto_service()
        price_data = crypto_service.get_price(symbol)
        if price_data and price_data.get('live'):
            signal['price'] = price_data['price']
            signal['price_live'] = True
        else:
            signal['price_live'] = False
    elif symbol in PROXY_SYMBOLS:
        proxy_service = get_proxy_service()
        price_data = proxy_service.get_price(symbol)
        if price_data and price_data.get('live'):
            signal['price'] = price_data['price']
            signal['price_live'] = True
        else:
            signal['price_live'] = False
    else:
        signal['price_live'] = False

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
