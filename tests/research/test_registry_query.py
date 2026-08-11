"""Tests for Registry Query Engine - Sprint 3.9D-11

Verify read-only queries, deterministic ordering, and ADR-024 compliance.
"""

import pytest
import tempfile
from pathlib import Path

from ml_service.research.registry_query import (
    RegistryQueryResult,
    RegistryQueryEngine,
)
from ml_service.research.registry_query.models import ModelSummary, RegistrySummary
from ml_service.research.registry_snapshot import RegistrySnapshot
from ml_service.research.registry_event_ledger import RegistryEventLedger
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.promotion_workflow.models import PromotionEvent


def test_no_sqlite_imports():
    """Verify no SQLite imports in registry_query package."""
    import ml_service.research.registry_query.query as query_mod
    import ml_service.research.registry_query.models as models_mod
    import inspect

    for mod in [query_mod, models_mod]:
        source = inspect.getsource(mod)
        forbidden = ["import sqlite", "from sqlite", "sqlite3"]
        for term in forbidden:
            assert term not in source.lower(), f"Found forbidden SQLite import: {term}"


def test_no_execution_imports():
    """Verify no execution layer imports in registry_query package."""
    import ml_service.research.registry_query.query as query_mod
    import inspect

    source = inspect.getsource(query_mod)
    forbidden = ["PortfolioService", "ExecutionSimulator", "ml_service.execution"]
    for term in forbidden:
        assert term not in source, f"Found forbidden execution import: {term}"


def test_query_result_immutable():
    """Verify RegistryQueryResult is immutable."""
    result = RegistryQueryResult(
        query_type="TEST",
        result_count=2,
        results=(1, 2),
    )

    with pytest.raises(AttributeError):
        result.query_type = "MODIFIED"


def test_query_result_validation():
    """Verify RegistryQueryResult validates inputs."""
    with pytest.raises(ValueError, match="query_type cannot be empty"):
        RegistryQueryResult(
            query_type="",
            result_count=0,
            results=(),
        )

    with pytest.raises(ValueError, match="result_count .* does not match results length"):
        RegistryQueryResult(
            query_type="TEST",
            result_count=5,
            results=(1, 2),
        )


def create_test_snapshot():
    """Create test RegistrySnapshot with sample models."""
    models = [
        ModelIdentity(
            artifact_path="models/btc_1h.pkl",
            symbol="BTCUSD",
            timeframe="1h",
            model_type="lightgbm",
            asset_class="CRYPTO",
            feature_count=15,
            feature_fingerprint="abc123",
            trained_at="2026-08-07T10:00:00Z",
            validation_available=True,
            calibration_available=True,
            sample_count=10000,
            lifecycle_status="APPROVED",
        ),
        ModelIdentity(
            artifact_path="models/eth_4h.pkl",
            symbol="ETHUSD",
            timeframe="4h",
            model_type="lightgbm",
            asset_class="CRYPTO",
            feature_count=12,
            feature_fingerprint="def456",
            trained_at="2026-08-07T11:00:00Z",
            validation_available=True,
            calibration_available=True,
            sample_count=8000,
            lifecycle_status="VALIDATED",
        ),
        ModelIdentity(
            artifact_path="models/spy_1d.pkl",
            symbol="SPY",
            timeframe="1d",
            model_type="lightgbm",
            asset_class="PROXY",
            feature_count=10,
            feature_fingerprint="ghi789",
            trained_at="2026-08-07T12:00:00Z",
            validation_available=True,
            calibration_available=True,
            sample_count=5000,
            lifecycle_status="APPROVED",
        ),
        ModelIdentity(
            artifact_path="models/sol_1h.pkl",
            symbol="SOLUSD",
            timeframe="1h",
            model_type="lightgbm",
            asset_class="CRYPTO",
            feature_count=14,
            feature_fingerprint="jkl012",
            trained_at="2026-08-07T13:00:00Z",
            validation_available=False,
            calibration_available=True,
            sample_count=6000,
            lifecycle_status="DISCOVERED",
        ),
    ]

    return RegistrySnapshot(
        snapshot_id="test_snapshot",
        created_at="2026-08-07T14:00:00Z",
        total_models=len(models),
        models=tuple(models),
        summary={},
    )


def create_test_ledger(tmpdir):
    """Create test RegistryEventLedger with sample events."""
    ledger_path = Path(tmpdir) / "events.jsonl"
    ledger = RegistryEventLedger(str(ledger_path))

    event1 = PromotionEvent(
        event_id="e1",
        model_id="models/btc_1h.pkl",
        from_state="VALIDATED",
        to_state="APPROVED",
        decision="APPROVED",
        reason_codes=("CRYPTO_VALIDATED_TO_APPROVED",),
        created_at="2026-08-07T10:30:00Z",
    )

    event2 = PromotionEvent(
        event_id="e2",
        model_id="models/eth_4h.pkl",
        from_state="DISCOVERED",
        to_state="VALIDATED",
        decision="APPROVED",
        reason_codes=("VALIDATION_COMPLETE",),
        created_at="2026-08-07T11:30:00Z",
    )

    ledger.append(event1)
    ledger.append(event2)

    return ledger


def test_list_models():
    """Verify list_models returns all models with deterministic ordering."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        result = engine.list_models()

        assert result.query_type == "LIST_MODELS"
        assert result.result_count == 4
        assert len(result.results) == 4

        assert result.results[0].symbol == "BTCUSD"
        assert result.results[1].symbol == "ETHUSD"
        assert result.results[2].symbol == "SOLUSD"
        assert result.results[3].symbol == "SPY"


def test_find_model_exists():
    """Verify find_model returns model when found."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        model = engine.find_model("BTCUSD", "1h")

        assert model is not None
        assert model.symbol == "BTCUSD"
        assert model.timeframe == "1h"
        assert model.asset_class == "CRYPTO"
        assert model.lifecycle_state == "APPROVED"
        assert model.latest_event_type == "APPROVED"


def test_find_model_not_exists():
    """Verify find_model returns None when not found."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        model = engine.find_model("NONEXISTENT", "1h")

        assert model is None


def test_get_lifecycle_history():
    """Verify get_lifecycle_history returns event history."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        result = engine.get_lifecycle_history("models/btc_1h.pkl")

        assert result.query_type == "LIFECYCLE_HISTORY"
        assert result.result_count == 1
        assert result.metadata["model_id"] == "models/btc_1h.pkl"
        assert result.results[0].event_id == "e1"


def test_get_promotion_history():
    """Verify get_promotion_history returns event history."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        result = engine.get_promotion_history("models/eth_4h.pkl")

        assert result.query_type == "PROMOTION_HISTORY"
        assert result.result_count == 1
        assert result.metadata["model_id"] == "models/eth_4h.pkl"
        assert result.results[0].event_id == "e2"


def test_get_production_candidates():
    """Verify get_production_candidates filters correctly."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        result = engine.get_production_candidates()

        assert result.query_type == "PRODUCTION_CANDIDATES"
        assert result.result_count == 1
        assert result.results[0].symbol == "BTCUSD"
        assert result.results[0].lifecycle_state == "APPROVED"
        assert result.results[0].asset_class == "CRYPTO"


def test_production_candidates_exclude_proxy():
    """Verify production candidates exclude proxy models."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        result = engine.get_production_candidates()

        for model in result.results:
            assert model.asset_class != "PROXY"


def test_production_candidates_require_validation():
    """Verify production candidates require validation."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        result = engine.get_production_candidates()

        for model in result.results:
            identity = next(m for m in snapshot.models if m.artifact_path == model.model_id)
            assert identity.validation_available is True


def test_get_registry_summary():
    """Verify get_registry_summary aggregates statistics."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        summary = engine.get_registry_summary()

        assert summary.total_models == 4
        assert summary.by_asset_class["CRYPTO"] == 3
        assert summary.by_asset_class["PROXY"] == 1
        assert summary.by_lifecycle_state["APPROVED"] == 2
        assert summary.by_lifecycle_state["VALIDATED"] == 1
        assert summary.by_lifecycle_state["DISCOVERED"] == 1
        assert summary.approved_count == 2
        assert summary.production_count == 0


def test_deterministic_ordering():
    """Verify queries return deterministic ordering."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        result1 = engine.list_models()
        result2 = engine.list_models()

        assert result1.results == result2.results


def test_immutable_outputs():
    """Verify query engine never mutates inputs."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)

        snapshot_models_before = snapshot.models
        ledger_path_before = ledger.storage.storage_path

        engine = RegistryQueryEngine(snapshot, ledger)
        engine.list_models()
        engine.get_registry_summary()

        assert snapshot.models is snapshot_models_before
        assert ledger.storage.storage_path == ledger_path_before


def test_model_summary_immutable():
    """Verify ModelSummary is immutable."""
    summary = ModelSummary(
        model_id="test",
        symbol="BTCUSD",
        timeframe="1h",
        asset_class="CRYPTO",
        lifecycle_state="APPROVED",
    )

    with pytest.raises(AttributeError):
        summary.symbol = "ETHUSD"


def test_registry_summary_immutable():
    """Verify RegistrySummary is immutable."""
    summary = RegistrySummary(
        total_models=10,
        by_asset_class={},
        by_lifecycle_state={},
        production_count=5,
        approved_count=3,
    )

    with pytest.raises(AttributeError):
        summary.total_models = 20


def test_empty_ledger_integration():
    """Verify query engine handles empty ledger gracefully."""
    snapshot = create_test_snapshot()

    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "empty.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))
        engine = RegistryQueryEngine(snapshot, ledger)

        result = engine.list_models()

        assert result.result_count == 4
        for model in result.results:
            assert model.latest_event_type is None


def test_empty_snapshot_integration():
    """Verify query engine handles empty snapshot gracefully."""
    empty_snapshot = RegistrySnapshot(
        snapshot_id="empty",
        created_at="2026-08-07T14:00:00Z",
        total_models=0,
        models=(),
        summary={},
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))
        engine = RegistryQueryEngine(empty_snapshot, ledger)

        result = engine.list_models()
        summary = engine.get_registry_summary()

        assert result.result_count == 0
        assert summary.total_models == 0


def test_query_result_with_metadata():
    """Verify query results can include metadata."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        result = engine.get_lifecycle_history("models/btc_1h.pkl")

        assert result.metadata is not None
        assert result.metadata["model_id"] == "models/btc_1h.pkl"


def test_production_candidates_sorted():
    """Verify production candidates are sorted deterministically."""
    snapshot = create_test_snapshot()
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = create_test_ledger(tmpdir)
        engine = RegistryQueryEngine(snapshot, ledger)

        result1 = engine.get_production_candidates()
        result2 = engine.get_production_candidates()

        assert result1.results == result2.results
