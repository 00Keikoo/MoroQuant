#!/bin/bash

PYTHON=./venv/bin/python

pairs=("BTCUSDT" "ETHUSDT" "BNBUSDT" "SOLUSDT" "HYPEUSDT" "LINKUSDT" "SUIUSDT" "XRPUSDT" "ZECUSDT" "LTCUSDT" "ADAUSDT")
timeframes=("1h" "4h")

for symbol in "${pairs[@]}"
do
  for tf in "${timeframes[@]}"
  do
    echo "================================================="
    echo "TUNING $symbol $tf"
    echo "================================================="

    $PYTHON -m cli.commands tune \
      --symbol $symbol \
      --timeframe $tf \
      --trials 100

    echo "Finished $symbol $tf"
    echo ""
  done
done
