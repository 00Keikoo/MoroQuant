"""
Backtest execution infrastructure.

Owns execution-coupled backtest orchestration that research consumes via outcomes.
"""

from ml_service.simulation.backtest.runner import BacktestRunner

__all__ = ["BacktestRunner"]
