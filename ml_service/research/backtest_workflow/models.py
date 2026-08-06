"""
Backtest Workflow Domain Models

Immutable domain objects following ADR-024.
All models use @dataclass(frozen=True) for immutability.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any


class BacktestStatus(Enum):
    """Backtest execution lifecycle states."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class BacktestConfig:
    """
    Immutable backtest configuration.

    Defines the inputs required to execute a backtest workflow.
    """
    backtest_id: str
    model_version_id: str
    dataset_snapshot_id: str
    execution_assumption: Dict[str, Any]
    created_at: datetime

    def validate(self) -> None:
        """Validate configuration constraints."""
        if not self.backtest_id:
            raise ValueError("backtest_id cannot be empty")
        if not self.model_version_id:
            raise ValueError("model_version_id cannot be empty")
        if not self.dataset_snapshot_id:
            raise ValueError("dataset_snapshot_id cannot be empty")


@dataclass(frozen=True)
class BacktestResult:
    """
    Immutable backtest execution result.

    Contains the complete outcome of a backtest workflow execution.
    """
    backtest_id: str
    experiment_id: str
    simulation_run_id: str
    performance_metrics: Dict[str, float]
    final_equity: float
    total_trades: int
    completed_at: datetime
    evaluation_score: Optional[float] = None

    def validate(self) -> None:
        """Validate result constraints."""
        if not self.backtest_id:
            raise ValueError("backtest_id cannot be empty")
        if not self.experiment_id:
            raise ValueError("experiment_id cannot be empty")
        if not self.simulation_run_id:
            raise ValueError("simulation_run_id cannot be empty")
        if self.total_trades < 0:
            raise ValueError("total_trades cannot be negative")


@dataclass(frozen=True)
class BacktestRun:
    """
    Immutable backtest execution state.

    Tracks the complete lifecycle of a backtest from configuration to result.
    State transitions create new instances - no mutation.
    """
    backtest_id: str
    config: BacktestConfig
    status: BacktestStatus
    result: Optional[BacktestResult]
    error_message: Optional[str]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def with_status(self, status: BacktestStatus, timestamp: Optional[datetime] = None) -> "BacktestRun":
        """
        Create new BacktestRun with updated status.

        Args:
            status: New status
            timestamp: Optional timestamp for status transition

        Returns:
            New BacktestRun instance
        """
        updates = {"status": status}

        if status == BacktestStatus.RUNNING and timestamp:
            updates["started_at"] = timestamp
        elif status in (BacktestStatus.COMPLETED, BacktestStatus.FAILED) and timestamp:
            updates["completed_at"] = timestamp

        return replace(self, **updates)

    def with_result(self, result: BacktestResult) -> "BacktestRun":
        """
        Create new BacktestRun with result.

        Args:
            result: Backtest result

        Returns:
            New BacktestRun instance with COMPLETED status
        """
        return replace(
            self,
            result=result,
            status=BacktestStatus.COMPLETED,
            completed_at=result.completed_at
        )

    def with_error(self, error_message: str, timestamp: Optional[datetime] = None) -> "BacktestRun":
        """
        Create new BacktestRun with error.

        Args:
            error_message: Error description
            timestamp: Optional error timestamp

        Returns:
            New BacktestRun instance with FAILED status
        """
        return replace(
            self,
            error_message=error_message,
            status=BacktestStatus.FAILED,
            completed_at=timestamp or datetime.utcnow()
        )

    def validate(self) -> None:
        """Validate run constraints."""
        if not self.backtest_id:
            raise ValueError("backtest_id cannot be empty")
        if self.config.backtest_id != self.backtest_id:
            raise ValueError("config.backtest_id must match backtest_id")
        if self.status == BacktestStatus.COMPLETED and not self.result:
            raise ValueError("COMPLETED status requires result")
        if self.status == BacktestStatus.FAILED and not self.error_message:
            raise ValueError("FAILED status requires error_message")
