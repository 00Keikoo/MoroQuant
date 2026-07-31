"""Unit tests for Promotion Manager."""

import pytest
from datetime import datetime
from ml_service.research.model_registry.model_types import (
    Model,
    ModelVersion,
    EvaluationResult,
    ModelLifecycleState,
    CompositeFingerprint
)
from ml_service.research.model_registry.service import ModelRegistryService
from ml_service.research.model_registry.registry_manager import RegistryManager
from ml_service.research.model_registry.promotion_manager import PromotionManager


@pytest.fixture
def registry_setup():
    """Setup orchestrator components."""
    service = ModelRegistryService()
    manager = RegistryManager(service)
    promo_manager = PromotionManager(service, manager)
    return service, manager, promo_manager


def test_promotion_manager_transitions_and_quality_gates(registry_setup):
    """Verify transitions and quality gate parameters validation."""
    service, manager, promo_manager = registry_setup
    now = datetime.now()

    # Create parent model
    m = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    service.register_model(m)

    fp = CompositeFingerprint(value="a" * 64)
    v = ModelVersion(
        model_version_id="BTCUSD_v1.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp,
        created_at=now
    )
    service.register_version(v)

    # 1. Transition DRAFT -> CANDIDATE
    promo_manager.promote_candidate("BTCUSD_v1.0.0", "promoter-1")
    assert service.get_version("BTCUSD_v1.0.0").lifecycle_state == ModelLifecycleState.CANDIDATE

    # 2. Quality gate validations checks (Failing check)
    bad_eval = EvaluationResult(
        model_version_id="BTCUSD_v1.0.0",
        sharpe_ratio=1.2,  # Too low (gate is 1.5)
        max_drawdown=-0.20,  # Too bad (gate is -0.15)
        ece=0.06,  # Too high (gate is 0.05)
        brier_score=0.25,  # Too high (gate is 0.22)
        win_rate=0.50,
        profit_factor=1.1,
        sortino_ratio=1.5,
        trade_count=80,  # Too low (gate is 100)
        is_approved=False
    )
    with pytest.raises(ValueError) as exc:
        promo_manager.validate_model("BTCUSD_v1.0.0", bad_eval, "reviewer-1")
    assert "Quality gate checks failed" in str(exc.value)

    # 3. Quality gate validations checks (Passing check)
    good_eval = EvaluationResult(
        model_version_id="BTCUSD_v1.0.0",
        sharpe_ratio=1.7,
        max_drawdown=-0.10,
        ece=0.03,
        brier_score=0.18,
        win_rate=0.58,
        profit_factor=1.6,
        sortino_ratio=2.2,
        trade_count=120,
        is_approved=False
    )
    approved_eval = promo_manager.validate_model("BTCUSD_v1.0.0", good_eval, "reviewer-1")
    assert approved_eval.is_approved
    assert service.get_version("BTCUSD_v1.0.0").lifecycle_state == ModelLifecycleState.VALIDATED


def test_promotion_manager_uniqueness_and_autodemote(registry_setup):
    """Verify that promoting a champion model auto-demotes the existing production model."""
    service, manager, promo_manager = registry_setup
    now = datetime.now()

    m = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    service.register_model(m)

    # Register two validated versions
    fp1 = CompositeFingerprint(value="a" * 64)
    v1 = ModelVersion(
        model_version_id="BTCUSD_v1.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.VALIDATED,
        composite_fingerprint=fp1,
        created_at=now
    )
    service.register_version(v1)

    fp2 = CompositeFingerprint(value="b" * 64)
    v2 = ModelVersion(
        model_version_id="BTCUSD_v2.0.0",
        model_id="BTCUSD",
        version="2.0.0",
        lifecycle_state=ModelLifecycleState.VALIDATED,
        composite_fingerprint=fp2,
        created_at=now
    )
    service.register_version(v2)

    # Set approved evaluation metrics scorecards for both versions
    eval_res = EvaluationResult(
        model_version_id="BTCUSD_v1.0.0",
        sharpe_ratio=1.6, max_drawdown=-0.12, ece=0.03, brier_score=0.18,
        win_rate=0.55, profit_factor=1.5, sortino_ratio=2.0, trade_count=110,
        is_approved=True, approved_by="user", approved_at=now
    )
    service.register_evaluation(eval_res)

    eval_res2 = EvaluationResult(
        model_version_id="BTCUSD_v2.0.0",
        sharpe_ratio=1.8, max_drawdown=-0.08, ece=0.02, brier_score=0.15,
        win_rate=0.59, profit_factor=1.7, sortino_ratio=2.4, trade_count=130,
        is_approved=True, approved_by="user", approved_at=now
    )
    service.register_evaluation(eval_res2)

    # Promote v1.0.0 to production
    promo_manager.promote_to_production("BTCUSD_v1.0.0", "promoter")
    assert manager.resolve_production_version("BTCUSD").model_version_id == "BTCUSD_v1.0.0"

    # Promote v2.0.0 to production (auto demotes v1.0.0)
    promo_manager.promote_to_production("BTCUSD_v2.0.0", "promoter")
    assert manager.resolve_production_version("BTCUSD").model_version_id == "BTCUSD_v2.0.0"
    assert service.get_version("BTCUSD_v1.0.0").lifecycle_state == ModelLifecycleState.ARCHIVED


def test_promotion_manager_rollback_and_reject(registry_setup):
    """Verify rollback features and rejects."""
    service, manager, promo_manager = registry_setup
    now = datetime.now()

    m = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    service.register_model(m)

    fp = CompositeFingerprint(value="a" * 64)
    v = ModelVersion(
        model_version_id="BTCUSD_v1.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.VALIDATED,
        composite_fingerprint=fp,
        created_at=now
    )
    service.register_version(v)

    eval_res = EvaluationResult(
        model_version_id="BTCUSD_v1.0.0",
        sharpe_ratio=1.6, max_drawdown=-0.12, ece=0.03, brier_score=0.18,
        win_rate=0.55, profit_factor=1.5, sortino_ratio=2.0, trade_count=110,
        is_approved=True, approved_by="user", approved_at=now
    )
    service.register_evaluation(eval_res)

    # Rollback version 1.0.0 to production (acts like promotion if not already in production)
    promo_manager.rollback("BTCUSD_v1.0.0", "operator")
    assert manager.resolve_production_version("BTCUSD").model_version_id == "BTCUSD_v1.0.0"

    # Rejection of a candidate
    v2 = ModelVersion(
        model_version_id="BTCUSD_v2.0.0",
        model_id="BTCUSD",
        version="2.0.0",
        lifecycle_state=ModelLifecycleState.CANDIDATE,
        composite_fingerprint=CompositeFingerprint(value="b" * 64),
        created_at=now
    )
    service.register_version(v2)
    promo_manager.reject("BTCUSD_v2.0.0", "reviewer-2")
    assert service.get_version("BTCUSD_v2.0.0").lifecycle_state == ModelLifecycleState.ARCHIVED
