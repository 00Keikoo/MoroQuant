#!/usr/bin/env python3
"""Generate signals and verify persistence."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from models.predictor import generate_signal
from data.database import get_database

def main():
    pairs = [
        ('BTCUSDT', '1h'),
        ('BTCUSDT', '4h'),
        ('ETHUSDT', '1h'),
        ('ETHUSDT', '4h'),
        ('SOLUSDT', '1h'),
        ('SOLUSDT', '4h'),
        ('HYPEUSDT', '1h'),
        ('HYPEUSDT', '4h'),
    ]

    print("="*60)
    print("GENERATING FRESH SIGNALS")
    print("="*60)

    for symbol, timeframe in pairs:
        print(f"\nGenerating {symbol} {timeframe}...")
        signal = generate_signal(symbol, timeframe, n_candles=300, persist=True)

        if signal:
            print(f"  ✓ {signal['direction']} (confidence: {signal['confidence']}%)")
            print(f"    Entry: {signal.get('price')}")
            print(f"    TP: {signal.get('take_profit')}")
            print(f"    SL: {signal.get('stop_loss')}")
        else:
            print(f"  ✗ Failed")

    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)

    db = get_database()

    # Get recent signals (last 15 minutes)
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Overall counts
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(entry_price) as with_entry,
                COUNT(take_profit) as with_tp,
                COUNT(stop_loss) as with_sl
            FROM signals
            WHERE datetime(created_at) > datetime('now', '-15 minutes')
        """)
        row = cursor.fetchone()
        print(f"\nNew signals (last 15 min):")
        print(f"  Total signals: {row[0]}")
        print(f"  With entry_price: {row[1]}")
        print(f"  With take_profit: {row[2]}")
        print(f"  With stop_loss: {row[3]}")

        # Directional signals
        cursor.execute("""
            SELECT symbol, timeframe, direction, entry_price, take_profit, stop_loss
            FROM signals
            WHERE datetime(created_at) > datetime('now', '-15 minutes')
            AND direction != 'neutral'
            ORDER BY created_at DESC
        """)
        directional = cursor.fetchall()

        print(f"\nDirectional signals (non-neutral): {len(directional)}")
        for row in directional:
            symbol, tf, direction, entry, tp, sl = row
            status = "✓" if (entry and tp and sl) else "✗"
            print(f"  {status} {symbol} {tf} {direction}: entry={entry}, tp={tp}, sl={sl}")

        # NULL audit
        cursor.execute("""
            SELECT symbol, timeframe, direction, entry_price, take_profit, stop_loss
            FROM signals
            WHERE datetime(created_at) > datetime('now', '-15 minutes')
            AND direction != 'neutral'
            AND (entry_price IS NULL OR take_profit IS NULL OR stop_loss IS NULL)
        """)
        null_signals = cursor.fetchall()

        print(f"\n" + "="*60)
        if null_signals:
            print("❌ NULL VALUES FOUND IN DIRECTIONAL SIGNALS")
            print("="*60)
            for row in null_signals:
                symbol, tf, direction, entry, tp, sl = row
                print(f"  {symbol} {tf} {direction}")
                print(f"    entry_price: {entry}")
                print(f"    take_profit: {tp}")
                print(f"    stop_loss: {sl}")
            return 1
        else:
            print("✅ ALL DIRECTIONAL SIGNALS HAVE COMPLETE PRICE DATA")
            print("="*60)
            return 0

if __name__ == "__main__":
    sys.exit(main())
