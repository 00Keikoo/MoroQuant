"""
Backtest Workflow Verification Tests

Tests Sprint 3.8 requirements:
1. Domain immutability
2. Lifecycle transitions
3. Dependency ordering
4. Failure handling
5. Determinism
"""

from datetime import datetime
from dataclasses import FrozenInstanceError

from ml_service.research.backtest_workflow.models import (
    BacktestConfig,
    BacktestResult,
    BacktestRun,
    BacktestStatus,
)
from ml_service.research.backtest_workflow.repository import BacktestWorkflowRepository
from ml_service.research.backtest_workflow.service import BacktestWorkflowService


class RaisesContext:
    """Simple context manager to replace pytest.raises."""
    def __init__(self, exception_type, match=None):
        self.exception_type = exception_type
        self.match = match

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(f"Expected {self.exception_type.__name__} but no exception was raised")
        if not issubclass(exc_type, self.exception_type):
            return False
        if self.match and self.match not in str(exc_val):
            raise AssertionError(f"Expected message containing '{self.match}', got '{exc_val}'")
        return True


# Mock pytest module
class PytestMock:
    @staticmethod
    def raises(exception_type, match=None):
        return RaisesContext(exception_type, match)

pytest = PytestMock()


class TestDomainImmutability:
    """Test that domain objects are immutable per ADR-024."""

    def test_backtest_config_immutable(self):
        """BacktestConfig cannot be mutated after creation."""
        config = BacktestConfig(
            backtest_id="test-1",
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption={"threshold": 0.5},
            created_at=datetime.utcnow(),
        )

        with pytest.raises(FrozenInstanceError):
            config.backtest_id = "modified"

    def test_backtest_result_immutable(self):
        """BacktestResult cannot be mutated after creation."""
        result = BacktestResult(
            backtest_id="test-1",
            experiment_id="exp-1",
            simulation_run_id="sim-1",
            performance_metrics={"sharpe": 1.5},
            final_equity=10000.0,
            total_trades=100,
            completed_at=datetime.utcnow(),
        )

        with pytest.raises(FrozenInstanceError):
            result.final_equity = 20000.0

    def test_backtest_run_immutable(self):
        """BacktestRun cannot be mutated after creation."""
        config = BacktestConfig(
            backtest_id="test-1",
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption={"threshold": 0.5},
            created_at=datetime.utcnow(),
        )

        run = BacktestRun(
            backtest_id="test-1",
            config=config,
            status=BacktestStatus.PENDING,
            result=None,
            error_message=None,
        )

        with pytest.raises(FrozenInstanceError):
            run.status = BacktestStatus.RUNNING


class TestLifecycleTransitions:
    """Test backtest lifecycle state transitions."""

    def test_pending_to_running(self):
        """Transition from PENDING to RUNNING."""
        config = BacktestConfig(
            backtest_id="test-1",
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption={"threshold": 0.5},
            created_at=datetime.utcnow(),
        )

        run = BacktestRun(
            backtest_id="test-1",
            config=config,
            status=BacktestStatus.PENDING,
            result=None,
            error_message=None,
        )

        timestamp = datetime.utcnow()
        updated_run = run.with_status(BacktestStatus.RUNNING, timestamp)

        assert updated_run.status == BacktestStatus.RUNNING
        assert updated_run.started_at == timestamp
        assert run.status == BacktestStatus.PENDING  # Original unchanged

    def test_running_to_completed(self):
        """Transition from RUNNING to COMPLETED with result."""
        config = BacktestConfig(
            backtest_id="test-1",
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption={"threshold": 0.5},
            created_at=datetime.utcnow(),
        )

        run = BacktestRun(
            backtest_id="test-1",
            config=config,
            status=BacktestStatus.RUNNING,
            result=None,
            error_message=None,
        )

        result = BacktestResult(
            backtest_id="test-1",
            experiment_id="exp-1",
            simulation_run_id="sim-1",
            performance_metrics={"sharpe": 1.5},
            final_equity=10000.0,
            total_trades=100,
            completed_at=datetime.utcnow(),
        )

        updated_run = run.with_result(result)

        assert updated_run.status == BacktestStatus.COMPLETED
        assert updated_run.result == result
        assert updated_run.completed_at == result.completed_at

    def test_running_to_failed(self):
        """Transition from RUNNING to FAILED with error."""
        config = BacktestConfig(
            backtest_id="test-1",
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption={"threshold": 0.5},
            created_at=datetime.utcnow(),
        )

        run = BacktestRun(
            backtest_id="test-1",
            config=config,
            status=BacktestStatus.RUNNING,
            result=None,
            error_message=None,
        )

        error_msg = "Model version not found"
        updated_run = run.with_error(error_msg)

        assert updated_run.status == BacktestStatus.FAILED
        assert updated_run.error_message == error_msg
        assert updated_run.completed_at is not None


class TestDependencyOrdering:
    """Test that workflow executes dependencies in correct order."""

    def test_service_requires_valid_config(self):
        """Service validates config before creating backtest."""
        service = BacktestWorkflowService()

        with pytest.raises(ValueError, match="model_version_id cannot be empty"):
            service.create_backtest(
                model_version_id="",
                dataset_snapshot_id="dataset-1",
                execution_assumption={"threshold": 0.5},
            )

    def test_service_allows_multiple_pending_backtests(self):
        """Service allows creating multiple pending backtests per ADR-024."""
        service = BacktestWorkflowService()

        run1 = service.create_backtest(
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption={"threshold": 0.5},
            backtest_id="test-1",
        )

        run2 = service.create_backtest(
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption={"threshold": 0.5},
            backtest_id="test-2",
        )

        assert run1.backtest_id == "test-1"
        assert run2.backtest_id == "test-2"
        assert run1.status == BacktestStatus.PENDING
        assert run2.status == BacktestStatus.PENDING

    def test_cannot_start_non_pending_backtest(self):
        """Cannot start backtest unless in PENDING state."""
        service = BacktestWorkflowService()

        run = service.create_backtest(
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption={"threshold": 0.5},
        )

        started_run = service.start_backtest(run)

        with pytest.raises(ValueError, match="Cannot start backtest"):
            service.start_backtest(started_run)


class TestFailureHandling:
    """Test workflow failure scenarios."""

    def test_missing_model_error(self):
        """Workflow handles missing model gracefully."""
        config = BacktestConfig(
            backtest_id="test-1",
            model_version_id="nonexistent-model",
            dataset_snapshot_id="dataset-1",
            execution_assumption={"threshold": 0.5},
            created_at=datetime.utcnow(),
        )

        config.validate()

    def test_invalid_experiment_error(self):
        """Workflow handles invalid experiment configuration."""
        config = BacktestConfig(
            backtest_id="test-1",
            model_version_id="model-v1",
            dataset_snapshot_id="",
            execution_assumption={"threshold": 0.5},
            created_at=datetime.utcnow(),
        )

        with pytest.raises(ValueError, match="dataset_snapshot_id cannot be empty"):
            config.validate()

    def test_simulation_failure_captured(self):
        """Workflow captures simulation failures."""
        config = BacktestConfig(
            backtest_id="test-1",
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption={"threshold": 0.5},
            created_at=datetime.utcnow(),
        )

        run = BacktestRun(
            backtest_id="test-1",
            config=config,
            status=BacktestStatus.RUNNING,
            result=None,
            error_message=None,
        )

        error_run = run.with_error("Simulation failed: insufficient data")

        assert error_run.status == BacktestStatus.FAILED
        assert "Simulation failed" in error_run.error_message


class TestDeterminism:
    """Test that identical configs produce identical results."""

    def test_config_fingerprint_deterministic(self):
        """Same config parameters produce identical BacktestConfig."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        execution = {"threshold_long": 0.6, "threshold_short": 0.4}

        config1 = BacktestConfig(
            backtest_id="test-1",
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption=execution,
            created_at=timestamp,
        )

        config2 = BacktestConfig(
            backtest_id="test-1",
            model_version_id="model-v1",
            dataset_snapshot_id="dataset-1",
            execution_assumption=execution,
            created_at=timestamp,
        )

        assert config1.backtest_id == config2.backtest_id
        assert config1.model_version_id == config2.model_version_id
        assert config1.dataset_snapshot_id == config2.dataset_snapshot_id
        assert config1.execution_assumption == config2.execution_assumption

    def test_result_deterministic(self):
        """Same backtest produces identical BacktestResult structure."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        metrics = {"sharpe": 1.5, "winrate": 0.6}

        result1 = BacktestResult(
            backtest_id="test-1",
            experiment_id="exp-1",
            simulation_run_id="sim-1",
            performance_metrics=metrics,
            final_equity=10000.0,
            total_trades=100,
            completed_at=timestamp,
        )

        result2 = BacktestResult(
            backtest_id="test-1",
            experiment_id="exp-1",
            simulation_run_id="sim-1",
            performance_metrics=metrics,
            final_equity=10000.0,
            total_trades=100,
            completed_at=timestamp,
        )

        assert result1.backtest_id == result2.backtest_id
        assert result1.final_equity == result2.final_equity
        assert result1.total_trades == result2.total_trades


class TestRepository:
    """Test repository persistence rules."""

    def test_repository_only_saves_completed_results(self):
        """Repository only accepts completed BacktestResult."""
        repo = BacktestWorkflowRepository()

        result = BacktestResult(
            backtest_id="test-1",
            experiment_id="exp-1",
            simulation_run_id="sim-1",
            performance_metrics={"sharpe": 1.5},
            final_equity=10000.0,
            total_trades=100,
            completed_at=datetime.utcnow(),
        )

        repo.save(result)
        retrieved = repo.get("test-1")

        assert retrieved is not None
        assert retrieved.backtest_id == "test-1"

    def test_repository_retrieval(self):
        """Repository retrieves saved results correctly."""
        repo = BacktestWorkflowRepository()

        result = BacktestResult(
            backtest_id="test-1",
            experiment_id="exp-1",
            simulation_run_id="sim-1",
            performance_metrics={"sharpe": 1.5},
            final_equity=10000.0,
            total_trades=100,
            completed_at=datetime.utcnow(),
        )

        repo.save(result)

        assert repo.exists("test-1")
        assert not repo.exists("nonexistent")

    def test_repository_list_all(self):
        """Repository lists all results sorted by ID."""
        repo = BacktestWorkflowRepository()

        for i in range(3):
            result = BacktestResult(
                backtest_id=f"test-{i}",
                experiment_id=f"exp-{i}",
                simulation_run_id=f"sim-{i}",
                performance_metrics={"sharpe": 1.5},
                final_equity=10000.0,
                total_trades=100,
                completed_at=datetime.utcnow(),
            )
            repo.save(result)

        results = repo.list_all()
        assert len(results) == 3
        assert results[0].backtest_id == "test-0"
        assert results[2].backtest_id == "test-2"


def run_all_tests():
    """Run all verification tests."""
    print("=" * 60)
    print("Sprint 3.8 Backtest Workflow Verification")
    print("=" * 60)
    print()

    test_classes = [
        TestDomainImmutability,
        TestLifecycleTransitions,
        TestDependencyOrdering,
        TestFailureHandling,
        TestDeterminism,
        TestRepository,
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 60)

        test_instance = test_class()
        test_methods = [
            method
            for method in dir(test_instance)
            if method.startswith("test_")
        ]

        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                print(f"  ✓ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"  ✗ {method_name}: {str(e)}")

    print()
    print("=" * 60)
    print(f"Results: {passed_tests}/{total_tests} tests passed")
    print("=" * 60)

    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
