#!/usr/bin/env python3
"""Validate TP/SL calculations for all trading pairs."""

import requests
import sys

SYMBOLS = ['BTCUSDT', 'BNBUSDT', 'SOLUSDT', 'ETHUSDT', 'HYPEUSDT',
           'ADAUSDT', 'XRPUSDT', 'LINKUSDT', 'LTCUSDT', 'ZECUSDT', 'SUIUSDT']

def validate_signal(symbol):
    """Validate TP/SL for a single symbol."""
    try:
        resp = requests.get(f"http://localhost:8000/api/signals?symbol={symbol}&timeframe=1h", timeout=30)
        signal = resp.json()

        direction = signal.get('direction')
        price = signal.get('price')
        tp = signal.get('take_profit')
        sl = signal.get('stop_loss')
        atr = signal.get('atr')

        # Neutral signals don't need TP/SL
        if direction == 'neutral':
            if tp is None and sl is None:
                return True, f"{symbol:10s} {direction.upper():8s}: No TP/SL (neutral) ✓"
            else:
                return False, f"{symbol:10s} {direction.upper():8s}: ERROR - Neutral should have no TP/SL"

        # Non-neutral signals must have TP/SL
        if tp is None or sl is None:
            return False, f"{symbol:10s} {direction.upper():8s}: ERROR - Missing TP/SL (ATR={atr})"

        # Validate directional logic
        if direction == 'short':
            if tp < price < sl:
                # Use appropriate formatting based on price magnitude
                fmt = '.4f' if price < 1.0 else '.2f'
                return True, f"{symbol:10s} {direction.upper():8s}: TP={tp:{fmt}} < Entry={price:{fmt}} < SL={sl:{fmt}} ✓"
            else:
                return False, f"{symbol:10s} {direction.upper():8s}: BROKEN - TP={tp} Entry={price} SL={sl}"

        elif direction == 'long':
            if sl < price < tp:
                fmt = '.4f' if price < 1.0 else '.2f'
                return True, f"{symbol:10s} {direction.upper():8s}: SL={sl:{fmt}} < Entry={price:{fmt}} < TP={tp:{fmt}} ✓"
            else:
                return False, f"{symbol:10s} {direction.upper():8s}: BROKEN - SL={sl} Entry={price} TP={tp}"

        return False, f"{symbol:10s}: Unknown direction '{direction}'"

    except Exception as e:
        return False, f"{symbol:10s}: ERROR - {e}"

if __name__ == "__main__":
    print("=" * 80)
    print("TP/SL Validation Test - All Trading Pairs")
    print("=" * 80)

    results = []
    for symbol in SYMBOLS:
        passed, message = validate_signal(symbol)
        results.append((symbol, passed))
        print(message)

    print("=" * 80)
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\nResults: {passed_count}/{total_count} pairs passed")

    if passed_count == total_count:
        print("✓ All validations passed!")
        sys.exit(0)
    else:
        failed = [sym for sym, p in results if not p]
        print(f"✗ Failed: {', '.join(failed)}")
        sys.exit(1)
