#!/bin/bash

PYTHON=./venv/bin/python

pairs=("BTCUSDT" "ETHUSDT" "BNBUSDT" "SOLUSDT" "HYPEUSDT" "ADAUSDT" "LINKUSDT" "LTCUSDT" "ZECUSDT" "SUIUSDT" "XRPUSDT")
timeframes=("1h" "4h")

for symbol in "${pairs[@]}"
do
  for tf in "${timeframes[@]}"
  do
    echo "================================================="
    echo "TRAINING $symbol $tf"
    echo "================================================="

    $PYTHON -m cli.commands train \
      --symbol $symbol \
      --timeframe $tf \
      --retrain

    echo "Finished $symbol $tf"
    echo ""
  done
done
