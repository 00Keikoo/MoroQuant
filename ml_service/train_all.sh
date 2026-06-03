#!/bin/bash
# Train all models for crypto and proxy symbols

cd /home/zafka/trade-dashboard/ml_service

SYMBOLS=(
  "ETHUSDT"
  "BNBUSDT"
  "SOLUSDT"
  "ES_proxy"
  "NQ_proxy"
  "GC_proxy"
  "CL_proxy"
  "ZB_proxy"
  "BTCUSDT"
)

TIMEFRAMES=("1h" "4h")

for symbol in "${SYMBOLS[@]}"; do
  for timeframe in "${TIMEFRAMES[@]}"; do
    echo "=========================================="
    echo "Training $symbol $timeframe"
    echo "=========================================="
    venv/bin/python3 cli.py train --symbol "$symbol" --timeframe "$timeframe"
    echo ""
  done
done

echo "All training complete!"
