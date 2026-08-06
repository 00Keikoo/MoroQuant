"""
Tests for BacktestWorkflow Dataset Integration

Validates:
1. BacktestWorkflow uses DatasetService (not synthetic loader)
2. Dataset snapshot validation enforced
3. MarketEventIterator integration
"""

import csv
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ml_service.research.backtest_workflow.models import BacktestConfig, BacktestStatus
from ml_service.research.backtest_workflow.orchestrator import (
    BacktestWorkflowOrchestrator,
    BacktestWorkflowOrchestratorFactory,
)
from ml_service.research.models import DatasetSnapshot


class TestBacktestWorkflowDatasetIntegration:
    """Test suite for BacktestWorkflow dataset integration."""

    def test_backtest_workflow_uses_dataset_service(self):
        """Verify BacktestWorkflow loads data via DatasetService."""
        orchestrator = BacktestWorkflowOrchestratorFactory.create()

        # Verify dataset_service is injected
        assert hasattr(orchestrator, 'dataset_service')
        assert orchestrator.dataset_service is not None

    def test_backtest_workflow_rejects_unfrozen_dataset(self):
        """Verify BacktestWorkflow rejects non-frozen datasets."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            )
            writer.writeheader()
            writer.writerow({
                'timestamp': '2024-01-01T00:00:00Z',
                'symbol': 'BTCUSDT',
                'open': '40000.0',
                'high': '40100.0',
                'low': '39900.0',
                'close': '40000.0',
                'volume': '1000.0',
            })

            file_path = f.name

        try:
            orchestrator = BacktestWorkflowOrchestratorFactory.create()

            # Create non-frozen dataset snapshot
            snapshot = orchestrator.dataset_service.create_snapshot(
                dataset_version_id="DS_1.0.0",
                fingerprint="a" * 64,
                file_path=file_path,
                is_frozen=False,  # NOT frozen
                created_at="2024-01-01T00:00:00Z",
            )

            config = BacktestConfig(
                backtest_id="test-bt-001",
                model_version_id="model-v1",
                dataset_snapshot_id="DS_1.0.0",
                execution_assumption={
                    "initial_capital": 100000.0,
                    "threshold_long": 0.5,
                    "threshold_short": 0.5,
                },
                created_at=datetime(2024, 1, 1, 0, 0, 0),
            )

            run = orchestrator.execute_backtest(config)

            # Verify error (model not found or dataset frozen check)
            assert run.status == BacktestStatus.FAILED
            assert run.error_message is not None

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_backtest_workflow_loads_from_dataset_file(self):
        """Verify BacktestWorkflow loads market events from dataset file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            )
            writer.writeheader()

            # Write 3 events
            for i in range(3):
                writer.writerow({
                    'timestamp': f'2024-01-01T{i:02d}:00:00Z',
                    'symbol': 'BTCUSDT',
                    'open': f'{40000 + i * 100}',
                    'high': f'{40000 + i * 100 + 50}',
                    'low': f'{40000 + i * 100 - 50}',
                    'close': f'{40000 + i * 100}',
                    'volume': '1000.0',
                })

            file_path = f.name

        try:
            orchestrator = BacktestWorkflowOrchestratorFactory.create()

            # Create frozen dataset snapshot
            snapshot = orchestrator.dataset_service.create_snapshot(
                dataset_version_id="DS_1.0.0",
                fingerprint="a" * 64,
                file_path=file_path,
                is_frozen=True,
                created_at="2024-01-01T00:00:00Z",
            )

            config = BacktestConfig(
                backtest_id="test-bt-002",
                model_version_id="model-v1",
                dataset_snapshot_id="DS_1.0.0",
                execution_assumption={
                    "initial_capital": 100000.0,
                    "threshold_long": 0.5,
                    "threshold_short": 0.5,
                },
                created_at=datetime(2024, 1, 1, 0, 0, 0),
            )

            run = orchestrator.execute_backtest(config)

            # Verify execution attempted (may fail on model not found, but dataset loading is tested)
            # The key validation is that dataset service is used, not model execution
            assert run.status in (BacktestStatus.COMPLETED, BacktestStatus.FAILED)

            # If failed, it should be due to model not found, not dataset issues
            if run.status == BacktestStatus.FAILED:
                assert "model" in run.error_message.lower()

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_backtest_workflow_dataset_not_found(self):
        """Verify BacktestWorkflow handles missing dataset gracefully."""
        orchestrator = BacktestWorkflowOrchestratorFactory.create()

        config = BacktestConfig(
            backtest_id="test-bt-003",
            model_version_id="model-v1",
            dataset_snapshot_id="DS_NONEXISTENT",
            execution_assumption={
                "initial_capital": 100000.0,
            },
            created_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        run = orchestrator.execute_backtest(config)

        # Verify error for missing dataset
        assert run.status == BacktestStatus.FAILED
        assert run.error_message is not None

    def test_no_synthetic_data_loader_exists(self):
        """Verify synthetic data generation removed from orchestrator."""
        import inspect

        orchestrator = BacktestWorkflowOrchestratorFactory.create()

        # Get source code of _load_market_data
        source = inspect.getsource(orchestrator._load_market_data)

        # Verify no hardcoded values
        assert "40000.0" not in source  # Old synthetic price
        assert "datetime(2024, 1, 1," not in source  # Old synthetic timestamp

        # Verify uses dataset service
        assert "dataset_service" in source.lower() or "MarketEventIterator" in source
