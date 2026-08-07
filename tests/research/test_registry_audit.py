"""Tests for Model Registry Classification Audit - Sprint 3.9D-4

Validates the audit metrics, deterministic serialization, production candidates,
and compliance constraints.
"""

import pytest
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_registry_audit.models import AuditReport
from ml_service.research.model_registry_audit.audit import (
    DefaultRegistryClassificationAuditor,
    is_production_candidate,
)


def create_mock_identity(
    symbol: str = "BTCUSDT",
    asset_class: str = "crypto",
    validation_available: bool = True,
    calibration_available: bool = True,
    lifecycle_status: str = "GOVERNANCE_READY"
) -> ModelIdentity:
    """Helper to create a ModelIdentity for testing."""
    return ModelIdentity(
        artifact_path=f"path/to/{symbol}.pkl",
        symbol=symbol,
        timeframe="1h",
        model_type="xgboost",
        asset_class=asset_class,
        feature_count=10,
        feature_fingerprint="f" * 64,
        trained_at="20260621_071847",
        validation_available=validation_available,
        calibration_available=calibration_available,
        sample_count=1000,
        lifecycle_status=lifecycle_status
    )


class TestAuditReport:
    """Tests validation, immutability, and serialization of AuditReport."""

    def test_immutable_report(self):
        """Verify frozen dataclass prevents field mutations."""
        report = AuditReport(
            total_models=5,
            crypto_models=3,
            proxy_models=2,
            validated_models=4,
            calibrated_models=3,
            governance_ready_models=2,
            invalid_models=0
        )

        with pytest.raises(AttributeError):
            report.total_models = 10

        with pytest.raises(AttributeError):
            report.crypto_models = 4

    def test_value_validation(self):
        """Verify negative values or incorrect types raise exceptions."""
        with pytest.raises(ValueError, match="cannot be negative"):
            AuditReport(
                total_models=-1,
                crypto_models=0,
                proxy_models=0,
                validated_models=0,
                calibrated_models=0,
                governance_ready_models=0,
                invalid_models=0
            )

        with pytest.raises(TypeError, match="must be an integer"):
            AuditReport(
                total_models="five",  # type: ignore
                crypto_models=0,
                proxy_models=0,
                validated_models=0,
                calibrated_models=0,
                governance_ready_models=0,
                invalid_models=0
            )

    def test_deterministic_serialization(self):
        """Verify deterministic JSON serialization with sorted keys."""
        report = AuditReport(
            total_models=5,
            crypto_models=3,
            proxy_models=2,
            validated_models=4,
            calibrated_models=3,
            governance_ready_models=2,
            invalid_models=0
        )

        json_out1 = report.to_json()
        json_out2 = report.to_json()

        assert json_out1 == json_out2
        assert "classification_summary" in json_out1

        # Check alphabetical order of keys in dictionary serialization
        keys = list(report.to_dict().keys())
        # The keys of to_dict don't have to be sorted, but to_json must have sorted keys.
        # Let's ensure classification_summary tuples are sorted by key.
        summary_keys = [k for k, _ in report.classification_summary]
        assert summary_keys == sorted(summary_keys)


class TestDefaultRegistryClassificationAuditor:
    """Tests auditing classification metrics and logic."""

    def test_crypto_proxy_counting(self):
        """Verify proper classification counts of crypto, proxy, and invalid models."""
        models = (
            create_mock_identity(symbol="BTCUSDT", asset_class="crypto"),
            create_mock_identity(symbol="ETHUSDT", asset_class="crypto"),
            create_mock_identity(symbol="ES", asset_class="proxy"),
            create_mock_identity(symbol="GC", asset_class="proxy"),
            create_mock_identity(symbol="UNKNOWN", asset_class="equities"),
        )

        auditor = DefaultRegistryClassificationAuditor()
        report = auditor.audit(models)

        assert report.total_models == 5
        assert report.crypto_models == 2
        assert report.proxy_models == 2
        assert report.invalid_models == 1

    def test_validation_counting(self):
        """Verify correct counting of validated models."""
        models = (
            create_mock_identity(symbol="BTC", validation_available=True),
            create_mock_identity(symbol="ETH", validation_available=False),
            create_mock_identity(symbol="SOL", validation_available=True),
        )

        auditor = DefaultRegistryClassificationAuditor()
        report = auditor.audit(models)

        assert report.validated_models == 2

    def test_calibration_counting(self):
        """Verify correct counting of calibrated models."""
        models = (
            create_mock_identity(symbol="BTC", calibration_available=True),
            create_mock_identity(symbol="ETH", calibration_available=False),
            create_mock_identity(symbol="SOL", calibration_available=False),
        )

        auditor = DefaultRegistryClassificationAuditor()
        report = auditor.audit(models)

        assert report.calibrated_models == 1

    def test_governance_ready_counting(self):
        """Verify correct counting of GOVERNANCE_READY models."""
        models = (
            create_mock_identity(symbol="BTC", lifecycle_status="GOVERNANCE_READY"),
            create_mock_identity(symbol="ETH", lifecycle_status="DRAFT"),
            create_mock_identity(symbol="SOL", lifecycle_status="GOVERNANCE_READY"),
        )

        auditor = DefaultRegistryClassificationAuditor()
        report = auditor.audit(models)

        assert report.governance_ready_models == 2

    def test_deterministic_output(self):
        """Verify statelessness and deterministic output."""
        models = (
            create_mock_identity(symbol="BTCUSDT", asset_class="crypto"),
            create_mock_identity(symbol="ES", asset_class="proxy"),
        )

        auditor = DefaultRegistryClassificationAuditor()
        report1 = auditor.audit(models)
        report2 = auditor.audit(models)

        assert report1.to_json() == report2.to_json()


class TestProductionSafetyGuard:
    """Tests production safety guard policies."""

    def test_crypto_production_candidate(self):
        """Crypto models are candidates only if validation is available."""
        # Crypto + Validated = True
        crypto_valid = create_mock_identity(asset_class="crypto", validation_available=True)
        assert is_production_candidate(crypto_valid) is True

        # Crypto + Not Validated = False
        crypto_not_valid = create_mock_identity(asset_class="crypto", validation_available=False)
        assert is_production_candidate(crypto_not_valid) is False

    def test_proxy_cannot_become_production_candidate(self):
        """Proxy models must ALWAYS return False, regardless of validation/calibration."""
        proxy_valid = create_mock_identity(asset_class="proxy", validation_available=True)
        assert is_production_candidate(proxy_valid) is False

        proxy_not_valid = create_mock_identity(asset_class="proxy", validation_available=False)
        assert is_production_candidate(proxy_not_valid) is False

    def test_invalid_asset_class_cannot_become_production_candidate(self):
        """Unknown or invalid asset class models cannot be production candidates."""
        other_model = create_mock_identity(asset_class="equities", validation_available=True)
        assert is_production_candidate(other_model) is False


class TestForbiddenDependencies:
    """Verifies ADR-024 compliance by checking for forbidden dependencies."""

    def test_no_database_dependency(self):
        """Verify the registry audit module has no database dependencies."""
        import ml_service.research.model_registry_audit.audit as audit_module
        import ml_service.research.model_registry_audit.models as models_module
        import ml_service.research.model_registry_audit.interfaces as interfaces_module

        forbidden_imports = [
            'sqlite',
            'sqlalchemy',
            'database',
            'db',
            'session',
            'connection'
        ]

        for module in [audit_module, models_module, interfaces_module]:
            module_source = import_module_source(module)
            for forbidden in forbidden_imports:
                # Ensure they aren't imported or used in source code
                assert f"import {forbidden}" not in module_source, \
                    f"Forbidden import '{forbidden}' found in {module.__name__}"
                assert f"from {forbidden}" not in module_source, \
                    f"Forbidden import '{forbidden}' found in {module.__name__}"


def import_module_source(module) -> str:
    """Helper to retrieve module source code."""
    import inspect
    return inspect.getsource(module)
