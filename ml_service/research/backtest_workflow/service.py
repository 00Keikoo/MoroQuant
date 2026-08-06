"""
Backtest Workflow Service

Business-level service for backtest workflow operations.
Validates BacktestConfig and manages workflow lifecycle.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from ml_service.research.backtest_workflow.models import (
    BacktestConfig,
    BacktestRun,
    BacktestStatus,
)
from ml_service.research.backtest_workflow.repository import BacktestWorkflowRepository


class BacktestWorkflowService:
    """
    Service layer for backtest workflow operations.

    Responsibilities:
    - Validate BacktestConfig
    - Create and initialize BacktestRun
    - Coordinate workflow lifecycle
    - Does NOT execute simulation (delegated to orchestrator)
    """

    def __init__(self, repository: Optional[BacktestWorkflowRepository] = None):
        self.repository = repository or BacktestWorkflowRepository()

    def create_backtest(
        self,
        model_version_id: str,
        dataset_snapshot_id: str,
        execution_assumption: dict,
        backtest_id: Optional[str] = None,
    ) -> BacktestRun:
        """
        Create and validate a new backtest configuration.

        Args:
            model_version_id: Model version to backtest
            dataset_snapshot_id: Dataset snapshot for backtest
            execution_assumption: Execution simulation parameters
            backtest_id: Optional backtest identifier

        Returns:
            BacktestRun in PENDING state

        Raises:
            ValueError: If configuration is invalid
        """
        if backtest_id is None:
            backtest_id = f"backtest-{uuid4().hex[:8]}"

        config = BacktestConfig(
            backtest_id=backtest_id,
            model_version_id=model_version_id,
            dataset_snapshot_id=dataset_snapshot_id,
            execution_assumption=execution_assumption,
            created_at=datetime.utcnow(),
        )

        config.validate()

        return BacktestRun(
            backtest_id=backtest_id,
            config=config,
            status=BacktestStatus.PENDING,
            result=None,
            error_message=None,
        )

    def start_backtest(self, run: BacktestRun) -> BacktestRun:
        """
        Transition backtest to RUNNING state.

        Args:
            run: BacktestRun in PENDING state

        Returns:
            Updated BacktestRun in RUNNING state

        Raises:
            ValueError: If not in PENDING state
        """
        if run.status != BacktestStatus.PENDING:
            raise ValueError(f"Cannot start backtest in {run.status.value} state")

        return run.with_status(BacktestStatus.RUNNING, datetime.utcnow())

    def complete_backtest(self, run: BacktestRun) -> None:
        """
        Persist completed backtest run.

        Args:
            run: BacktestRun in COMPLETED state with result

        Raises:
            ValueError: If not in COMPLETED state or missing result
        """
        if run.status != BacktestStatus.COMPLETED:
            raise ValueError(f"Cannot persist backtest in {run.status.value} state")

        if not run.result:
            raise ValueError("Cannot persist backtest without result")

        run.validate()
        self.repository.save(run)

    def get_result(self, backtest_id: str) -> Optional[BacktestRun]:
        """
        Retrieve completed backtest run.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Complete BacktestRun if found, None otherwise
        """
        return self.repository.get(backtest_id)

    def validate_config(self, config: BacktestConfig) -> None:
        """
        Validate backtest configuration.

        Args:
            config: BacktestConfig to validate

        Raises:
            ValueError: If configuration is invalid
        """
        config.validate()

        if not config.execution_assumption:
            raise ValueError("execution_assumption cannot be empty")
