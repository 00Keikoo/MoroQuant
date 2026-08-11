"""Tests for Model Lifecycle Manager - Sprint 3.9D-7

Comprehensive test suite for deterministic lifecycle state management.
ADR-024 compliance validation: no database, no execution dependencies.
"""

import pytest
from datetime import datetime
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import LifecycleState, ModelLifecycleRecord
from ml_service.research.model_lifecycle.policy import LifecyclePolicy
from ml_service.research.model_lifecycle.lifecycle import LifecycleManager


@pytest.fixture
def crypto_model_discovered():
    """Fixture: discovered crypto model with no validation."""
    return ModelIdentity(
        artifact_path="/models/BTC_5m_lstm.keras",
        symbol="BTC",
        timeframe="5m",
        model_type="lstm",
        asset_class="crypto",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=False,
        calibration_available=False,
        sample_count=1000,
        lifecycle_status="DISCOVERED"
    )


@pytest.fixture
def crypto_model_validated():
    """Fixture: validated crypto model with validation but no calibration."""
    return ModelIdentity(
        artifact_path="/models/ETH_5m_lstm.keras",
        symbol="ETH",
        timeframe="5m",
        model_type="lstm",
        asset_class="crypto",
        feature_count=10,
        feature_fingerprint="def456",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=True,
        calibration_available=False,
        sample_count=1000,
        lifecycle_status="VALIDATED"
    )


@pytest.fixture
def crypto_model_governance_ready():
    """Fixture: governance-ready crypto model with validation and calibration."""
    return ModelIdentity(
        artifact_path="/models/SOL_5m_lstm.keras",
        symbol="SOL",
        timeframe="5m",
        model_type="lstm",
        asset_class="crypto",
        feature_count=10,
        feature_fingerprint="ghi789",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="GOVERNANCE_READY"
    )


@pytest.fixture
def proxy_model_governance_ready():
    """Fixture: governance-ready proxy model (blocked from production)."""
    return ModelIdentity(
        artifact_path="/models/SPY_5m_lstm.keras",
        symbol="SPY",
        timeframe="5m",
        model_type="lstm",
        asset_class="proxy",
        feature_count=10,
        feature_fingerprint="jkl012",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="GOVERNANCE_READY"
    )


class TestLifecycleState:
    """Tests for LifecycleState enum."""

    def test_all_states_defined(self):
        """All required states are defined."""
        expected_states = {
            "DISCOVERED",
            "VALIDATED",
            "GOVERNANCE_READY",
            "APPROVED",
            "PRODUCTION",
            "REJECTED"
        }
        actual_states = {state.value for state in LifecycleState}
        assert actual_states == expected_states


class TestModelLifecycleRecord:
    """Tests for ModelLifecycleRecord immutability and validation."""

    def test_immutable_record_creation(self):
        """Record is immutable frozen dataclass."""
        record = ModelLifecycleRecord(
            artifact_path="/models/test.keras",
            symbol="BTC",
            asset_class="crypto",
            current_state=LifecycleState.VALIDATED,
            previous_state=LifecycleState.DISCOVERED,
            reason="validation metrics available",
            timestamp="2024-01-01T00:00:00Z"
        )

        with pytest.raises(Exception):
            record.current_state = LifecycleState.APPROVED

    def test_record_validation_empty_artifact_path(self):
        """Record validates non-empty artifact_path."""
        with pytest.raises(ValueError, match="artifact_path cannot be empty"):
            ModelLifecycleRecord(
                artifact_path="",
                symbol="BTC",
                asset_class="crypto",
                current_state=LifecycleState.VALIDATED,
                previous_state=LifecycleState.DISCOVERED,
                reason="test",
                timestamp="2024-01-01T00:00:00Z"
            )

    def test_record_validation_empty_symbol(self):
        """Record validates non-empty symbol."""
        with pytest.raises(ValueError, match="symbol cannot be empty"):
            ModelLifecycleRecord(
                artifact_path="/models/test.keras",
                symbol="",
                asset_class="crypto",
                current_state=LifecycleState.VALIDATED,
                previous_state=LifecycleState.DISCOVERED,
                reason="test",
                timestamp="2024-01-01T00:00:00Z"
            )

    def test_record_validation_invalid_current_state(self):
        """Record validates current_state is LifecycleState."""
        with pytest.raises(TypeError, match="current_state must be LifecycleState"):
            ModelLifecycleRecord(
                artifact_path="/models/test.keras",
                symbol="BTC",
                asset_class="crypto",
                current_state="VALIDATED",
                previous_state=LifecycleState.DISCOVERED,
                reason="test",
                timestamp="2024-01-01T00:00:00Z"
            )


class TestLifecyclePolicy:
    """Tests for LifecyclePolicy transition rules."""

    def test_crypto_allowed_transitions(self):
        """Crypto models have full path to PRODUCTION."""
        assert LifecyclePolicy.is_transition_allowed(
            "crypto", LifecycleState.DISCOVERED, LifecycleState.VALIDATED
        )
        assert LifecyclePolicy.is_transition_allowed(
            "crypto", LifecycleState.VALIDATED, LifecycleState.GOVERNANCE_READY
        )
        assert LifecyclePolicy.is_transition_allowed(
            "crypto", LifecycleState.GOVERNANCE_READY, LifecycleState.APPROVED
        )
        assert LifecyclePolicy.is_transition_allowed(
            "crypto", LifecycleState.APPROVED, LifecycleState.PRODUCTION
        )

    def test_proxy_blocked_from_production(self):
        """Proxy models cannot reach APPROVED or PRODUCTION."""
        assert not LifecyclePolicy.is_transition_allowed(
            "proxy", LifecycleState.GOVERNANCE_READY, LifecycleState.APPROVED
        )
        assert not LifecyclePolicy.is_transition_allowed(
            "proxy", LifecycleState.APPROVED, LifecycleState.PRODUCTION
        )

    def test_invalid_transition_rejected(self):
        """Invalid transitions are rejected."""
        assert not LifecyclePolicy.is_transition_allowed(
            "crypto", LifecycleState.DISCOVERED, LifecycleState.PRODUCTION
        )
        assert not LifecyclePolicy.is_transition_allowed(
            "crypto", LifecycleState.DISCOVERED, LifecycleState.APPROVED
        )

    def test_validate_discovered_to_validated_requires_validation(self, crypto_model_discovered):
        """DISCOVERED -> VALIDATED requires validation_available=True."""
        is_valid, reason = LifecyclePolicy.validate_discovered_to_validated(crypto_model_discovered)
        assert not is_valid
        assert "validation metrics not available" in reason

    def test_validate_validated_to_governance_ready_requires_calibration(self, crypto_model_validated):
        """VALIDATED -> GOVERNANCE_READY requires calibration_available=True."""
        is_valid, reason = LifecyclePolicy.validate_validated_to_governance_ready(crypto_model_validated)
        assert not is_valid
        assert "calibration metrics not available" in reason

    def test_validate_approved_to_production_blocks_proxy(self, proxy_model_governance_ready):
        """Proxy models are blocked from PRODUCTION."""
        is_valid, reason = LifecyclePolicy.validate_approved_to_production(proxy_model_governance_ready)
        assert not is_valid
        assert "proxy assets blocked from production" in reason


class TestLifecycleManager:
    """Tests for LifecycleManager evaluation and transitions."""

    def test_evaluate_crypto_discovered(self, crypto_model_discovered):
        """Evaluate discovered crypto model stays DISCOVERED."""
        manager = LifecycleManager()
        record = manager.evaluate(crypto_model_discovered)

        assert record.current_state == LifecycleState.DISCOVERED
        assert record.symbol == "BTC"
        assert record.asset_class == "crypto"
        assert record.artifact_path == "/models/BTC_5m_lstm.keras"

    def test_evaluate_crypto_validated(self, crypto_model_validated):
        """Evaluate validated crypto model stays VALIDATED."""
        manager = LifecycleManager()
        record = manager.evaluate(crypto_model_validated)

        assert record.current_state == LifecycleState.VALIDATED
        assert record.symbol == "ETH"

    def test_evaluate_crypto_governance_ready(self, crypto_model_governance_ready):
        """Evaluate governance-ready crypto model stays GOVERNANCE_READY."""
        manager = LifecycleManager()
        record = manager.evaluate(crypto_model_governance_ready)

        assert record.current_state == LifecycleState.GOVERNANCE_READY
        assert record.symbol == "SOL"

    def test_valid_transition_discovered_to_validated(self):
        """Valid transition DISCOVERED -> VALIDATED with validation available."""
        manager = LifecycleManager()
        model = ModelIdentity(
            artifact_path="/models/BTC_5m_lstm.keras",
            symbol="BTC",
            timeframe="5m",
            model_type="lstm",
            asset_class="crypto",
            feature_count=10,
            feature_fingerprint="abc123",
            trained_at="2024-01-01T00:00:00Z",
            validation_available=True,
            calibration_available=False,
            sample_count=1000,
            lifecycle_status="DISCOVERED"
        )

        record = manager.transition(model, LifecycleState.VALIDATED)

        assert record.current_state == LifecycleState.VALIDATED
        assert record.previous_state == LifecycleState.DISCOVERED
        assert record.symbol == "BTC"

    def test_invalid_transition_discovered_to_validated_no_validation(self, crypto_model_discovered):
        """Invalid transition DISCOVERED -> VALIDATED without validation."""
        manager = LifecycleManager()

        with pytest.raises(ValueError, match="Invalid transition"):
            manager.transition(crypto_model_discovered, LifecycleState.VALIDATED)

    def test_valid_transition_validated_to_governance_ready(self):
        """Valid transition VALIDATED -> GOVERNANCE_READY with calibration available."""
        manager = LifecycleManager()
        model = ModelIdentity(
            artifact_path="/models/ETH_5m_lstm.keras",
            symbol="ETH",
            timeframe="5m",
            model_type="lstm",
            asset_class="crypto",
            feature_count=10,
            feature_fingerprint="def456",
            trained_at="2024-01-01T00:00:00Z",
            validation_available=True,
            calibration_available=True,
            sample_count=1000,
            lifecycle_status="VALIDATED"
        )

        record = manager.transition(model, LifecycleState.GOVERNANCE_READY)

        assert record.current_state == LifecycleState.GOVERNANCE_READY
        assert record.previous_state == LifecycleState.VALIDATED

    def test_invalid_transition_validated_to_governance_ready_no_calibration(self, crypto_model_validated):
        """Invalid transition VALIDATED -> GOVERNANCE_READY without calibration."""
        manager = LifecycleManager()

        with pytest.raises(ValueError, match="Invalid transition"):
            manager.transition(crypto_model_validated, LifecycleState.GOVERNANCE_READY)

    def test_crypto_full_production_path(self):
        """Crypto model can reach PRODUCTION through full path."""
        manager = LifecycleManager()
        model = ModelIdentity(
            artifact_path="/models/BTC_5m_lstm.keras",
            symbol="BTC",
            timeframe="5m",
            model_type="lstm",
            asset_class="crypto",
            feature_count=10,
            feature_fingerprint="abc123",
            trained_at="2024-01-01T00:00:00Z",
            validation_available=True,
            calibration_available=True,
            sample_count=1000,
            lifecycle_status="APPROVED"
        )

        record = manager.transition(model, LifecycleState.PRODUCTION)

        assert record.current_state == LifecycleState.PRODUCTION
        assert record.previous_state == LifecycleState.APPROVED

    def test_proxy_blocked_from_production(self, proxy_model_governance_ready):
        """Proxy model cannot transition to APPROVED."""
        manager = LifecycleManager()

        with pytest.raises(ValueError, match="Invalid transition"):
            manager.transition(proxy_model_governance_ready, LifecycleState.APPROVED)

    def test_immutable_record_output(self, crypto_model_discovered):
        """Manager returns immutable records."""
        manager = LifecycleManager()
        record = manager.evaluate(crypto_model_discovered)

        with pytest.raises(Exception):
            record.current_state = LifecycleState.VALIDATED

    def test_deterministic_output(self, crypto_model_discovered):
        """Manager produces deterministic output for same input."""
        manager = LifecycleManager()
        record1 = manager.evaluate(crypto_model_discovered)
        record2 = manager.evaluate(crypto_model_discovered)

        assert record1.current_state == record2.current_state
        assert record1.symbol == record2.symbol
        assert record1.asset_class == record2.asset_class
        assert record1.artifact_path == record2.artifact_path

    def test_timestamp_format(self, crypto_model_discovered):
        """Record timestamp is ISO format with Z suffix."""
        manager = LifecycleManager()
        record = manager.evaluate(crypto_model_discovered)

        assert record.timestamp.endswith("Z")
        datetime.fromisoformat(record.timestamp.replace("Z", "+00:00"))


class TestADR024Compliance:
    """Tests for ADR-024 compliance: no database, no execution dependencies."""

    def test_no_database_imports(self):
        """Module does not import database libraries."""
        import ml_service.research.model_lifecycle.models as models_module
        import ml_service.research.model_lifecycle.policy as policy_module
        import ml_service.research.model_lifecycle.lifecycle as lifecycle_module

        forbidden_imports = ["sqlalchemy", "psycopg2", "sqlite3", "pymongo"]

        for module in [models_module, policy_module, lifecycle_module]:
            module_vars = dir(module)
            for forbidden in forbidden_imports:
                assert forbidden not in module_vars, f"Found forbidden import: {forbidden}"

    def test_no_execution_imports(self):
        """Module does not import execution system components."""
        import ml_service.research.model_lifecycle.lifecycle as lifecycle_module

        module_source = lifecycle_module.__file__
        with open(module_source, 'r') as f:
            content = f.read()

        forbidden_patterns = [
            "PortfolioService",
            "ExecutionSimulator",
            "from ml_service.execution",
            "from ml_service.portfolio"
        ]

        for pattern in forbidden_patterns:
            assert pattern not in content, f"Found forbidden pattern: {pattern}"

    def test_stateless_manager(self):
        """LifecycleManager is stateless between calls."""
        manager = LifecycleManager()
        model1 = ModelIdentity(
            artifact_path="/models/BTC_5m_lstm.keras",
            symbol="BTC",
            timeframe="5m",
            model_type="lstm",
            asset_class="crypto",
            feature_count=10,
            feature_fingerprint="abc123",
            trained_at="2024-01-01T00:00:00Z",
            validation_available=False,
            calibration_available=False,
            sample_count=1000,
            lifecycle_status="DISCOVERED"
        )
        model2 = ModelIdentity(
            artifact_path="/models/ETH_5m_lstm.keras",
            symbol="ETH",
            timeframe="5m",
            model_type="lstm",
            asset_class="crypto",
            feature_count=10,
            feature_fingerprint="def456",
            trained_at="2024-01-01T00:00:00Z",
            validation_available=True,
            calibration_available=False,
            sample_count=1000,
            lifecycle_status="VALIDATED"
        )

        record1 = manager.evaluate(model1)
        record2 = manager.evaluate(model2)

        assert record1.symbol == "BTC"
        assert record2.symbol == "ETH"
        assert record1.current_state == LifecycleState.DISCOVERED
        assert record2.current_state == LifecycleState.VALIDATED
