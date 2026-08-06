"""
Backtest Workflow Integration Layer

Connects Model Registry → Experiment Engine → Simulation Runtime → Evaluation Engine
to produce complete backtest results following ADR-024 architectural rules.

Key principles:
- Immutable domain objects
- No database writes during simulation
- Deterministic replay
- Repository/Service separation
"""

from ml_service.research.backtest_workflow.models import (
    BacktestConfig,
    BacktestResult,
    BacktestRun,
    BacktestStatus,
)
from ml_service.research.backtest_workflow.orchestrator import (
    BacktestWorkflowOrchestrator,
    BacktestWorkflowOrchestratorFactory,
)
from ml_service.research.backtest_workflow.repository import BacktestWorkflowRepository
from ml_service.research.backtest_workflow.service import BacktestWorkflowService

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "BacktestRun",
    "BacktestStatus",
    "BacktestWorkflowOrchestrator",
    "BacktestWorkflowOrchestratorFactory",
    "BacktestWorkflowRepository",
    "BacktestWorkflowService",
]
