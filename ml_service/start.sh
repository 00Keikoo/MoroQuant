#!/bin/bash
cd ~/app/ml-project/ml-trading-dashboard/ml_service
exec venv/bin/uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --limit-concurrency 20 \
  --timeout-keep-alive 5
