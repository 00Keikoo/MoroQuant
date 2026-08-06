"""
Backtest Workflow Repository

Persistence layer for completed backtest runs.
Following ADR-024: No database writes during simulation runtime.
Only persists completed BacktestRun after workflow finishes.
"""

import copy
from typing import Dict, List, Optional
from ml_service.research.backtest_workflow.models import BacktestRun


class BacktestWorkflowRepository:
    """
    Repository for persisting completed backtest runs.

    Rules:
    - Only saves completed BacktestRun aggregate
    - NO persistence during simulation runtime
    - In-memory storage following project pattern
    - Preserves complete config, status, result, timestamps
    """

    def __init__(self):
        self._runs: Dict[str, BacktestRun] = {}

    def save(self, run: BacktestRun) -> BacktestRun:
        """
        Persist completed backtest run.

        Args:
            run: Completed BacktestRun

        Returns:
            Saved BacktestRun

        Raises:
            ValueError: If run validation fails
            TypeError: If not a BacktestRun instance
        """
        if not isinstance(run, BacktestRun):
            raise TypeError("Expected a BacktestRun instance.")

        run.validate()
        self._runs[run.backtest_id] = copy.deepcopy(run)
        return run

    def get(self, backtest_id: str) -> Optional[BacktestRun]:
        """
        Retrieve backtest run by ID.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Complete BacktestRun if found, None otherwise
        """
        return self._runs.get(backtest_id)

    def exists(self, backtest_id: str) -> bool:
        """
        Check if backtest run exists.

        Args:
            backtest_id: Backtest identifier

        Returns:
            True if run exists
        """
        return backtest_id in self._runs

    def list(self) -> List[BacktestRun]:
        """
        List all backtest runs.

        Returns:
            List of all BacktestRuns sorted by backtest_id
        """
        return sorted(self._runs.values(), key=lambda r: r.backtest_id)

    def delete(self, backtest_id: str) -> None:
        """
        Delete backtest run.

        Args:
            backtest_id: Backtest identifier

        Raises:
            KeyError: If backtest_id not found
        """
        if backtest_id not in self._runs:
            raise KeyError(f"BacktestRun with ID '{backtest_id}' not found.")
        del self._runs[backtest_id]
