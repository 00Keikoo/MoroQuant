"""Tests for Promotion Workflow - Sprint 3.9D-9

Verify deterministic promotion workflow, immutable events, and ADR-024 compliance.
"""

import pytest
import json
from datetime import datetime
from ml_service.research.promotion_workflow import (
    PromotionEvent,
    PromotionWorkflow,
    WorkflowPolicy,
)
from ml_service.research.promotion_engine import (
    PromotionStatus,
    PromotionScore,
    RegistryProposal,
)


def test_no_database_imports():
    """Verify no database imports in promotion_workflow package."""
    import ml_service.research.promotion_workflow.workflow as workflow_mod
    import ml_service.research.promotion_workflow.policy as policy_mod
    import ml_service.research.promotion_workflow.models as models_mod
    import inspect

    for mod in [workflow_mod, policy_mod, models_mod]:
        source = inspect.getsource(mod)
        forbidden_imports = ["from sqlalchemy", "import sqlalchemy", "from database", "import database"]
        for term in forbidden_imports:
            assert term not in source.lower(), f"Found forbidden database import: {term}"


def test_no_execution_imports():
    """Verify no execution layer imports in promotion_workflow package."""
    import ml_service.research.promotion_workflow.workflow as workflow_mod
    import ml_service.research.promotion_workflow.policy as policy_mod
    import inspect

    for mod in [workflow_mod, policy_mod]:
        source = inspect.getsource(mod)
        forbidden = ["PortfolioService", "ExecutionSimulator", "ml_service.execution"]
        for term in forbidden:
            assert term not in source, f"Found forbidden execution import: {term}"


def test_promotion_event_immutable():
    """Verify PromotionEvent is immutable."""
    event = PromotionEvent(
        event_id="abc123",
        model_id="models/test_model.pkl",
        from_state="VALIDATED",
        to_state="APPROVED",
        decision="APPROVED",
        reason_codes=("TEST_REASON",),
        created_at="2026-08-07T12:00:00Z",
    )

    with pytest.raises(AttributeError):
        event.decision = "REJECTED"


def test_promotion_event_validation():
    """Verify PromotionEvent validates inputs."""
    with pytest.raises(ValueError, match="event_id cannot be empty"):
        PromotionEvent(
            event_id="",
            model_id="test",
            from_state="A",
            to_state="B",
            decision="APPROVED",
            reason_codes=(),
            created_at="2026-08-07T12:00:00Z",
        )


def test_deterministic_event_ids():
    """Verify event IDs are deterministic from content."""
    event_id_1 = PromotionEvent.generate_event_id(
        model_id="models/test.pkl",
        from_state="VALIDATED",
        to_state="APPROVED",
        created_at="2026-08-07T12:00:00Z",
    )

    event_id_2 = PromotionEvent.generate_event_id(
        model_id="models/test.pkl",
        from_state="VALIDATED",
        to_state="APPROVED",
        created_at="2026-08-07T12:00:00Z",
    )

    assert event_id_1 == event_id_2
    assert len(event_id_1) == 16


def test_event_json_serialization():
    """Verify PromotionEvent supports deterministic JSON serialization."""
    event = PromotionEvent(
        event_id="abc123",
        model_id="models/test_model.pkl",
        from_state="VALIDATED",
        to_state="APPROVED",
        decision="APPROVED",
        reason_codes=("CRYPTO_VALIDATED_TO_APPROVED", "WORKFLOW_APPROVED"),
        created_at="2026-08-07T12:00:00Z",
    )

    json_str = event.to_json()
    data = json.loads(json_str)

    assert data["event_id"] == "abc123"
    assert data["decision"] == "APPROVED"
    assert "WORKFLOW_APPROVED" in data["reason_codes"]

    reconstructed = PromotionEvent.from_dict(data)
    assert reconstructed == event


def create_approved_crypto_proposal() -> RegistryProposal:
    """Helper to create an APPROVED crypto proposal."""
    score = PromotionScore(
        model_id="models/btc_model.pkl",
        validation_score=1.0,
        calibration_score=1.0,
        lifecycle_score=1.0,
        governance_score=1.0,
        total_score=1.0,
    )

    return RegistryProposal(
        model_id="models/btc_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state="VALIDATED",
        proposed_state="APPROVED",
        status=PromotionStatus.APPROVED,
        score=score,
        reason_codes=("CRYPTO_VALIDATED_TO_APPROVED",),
    )


def create_rejected_proposal() -> RegistryProposal:
    """Helper to create a REJECTED proposal."""
    score = PromotionScore(
        model_id="models/incomplete_model.pkl",
        validation_score=0.0,
        calibration_score=0.0,
        lifecycle_score=0.0,
        governance_score=0.0,
        total_score=0.0,
    )

    return RegistryProposal(
        model_id="models/incomplete_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state="DISCOVERED",
        proposed_state="DISCOVERED",
        status=PromotionStatus.REJECTED,
        score=score,
        reason_codes=("MISSING_VALIDATION", "MISSING_CALIBRATION"),
    )


def create_proxy_production_proposal() -> RegistryProposal:
    """Helper to create a proxy proposal attempting PRODUCTION."""
    score = PromotionScore(
        model_id="models/proxy_model.pkl",
        validation_score=1.0,
        calibration_score=1.0,
        lifecycle_score=1.0,
        governance_score=1.0,
        total_score=1.0,
    )

    return RegistryProposal(
        model_id="models/proxy_model.pkl",
        symbol="SPY",
        asset_class="PROXY",
        current_state="APPROVED",
        proposed_state="PRODUCTION",
        status=PromotionStatus.APPROVED,
        score=score,
        reason_codes=("PROXY_TO_APPROVED",),
    )


def test_approved_proposal_workflow():
    """Verify approved proposal creates promotion event."""
    proposal = create_approved_crypto_proposal()
    workflow = PromotionWorkflow()

    event = workflow.evaluate(proposal)

    assert event is not None
    assert event.model_id == "models/btc_model.pkl"
    assert event.from_state == "VALIDATED"
    assert event.to_state == "APPROVED"
    assert event.decision == "APPROVED"
    assert "CRYPTO_VALIDATED_TO_APPROVED" in event.reason_codes
    assert "WORKFLOW_APPROVED" in event.reason_codes


def test_rejected_proposal_blocked():
    """Verify rejected proposal does not create promotion event."""
    proposal = create_rejected_proposal()
    workflow = PromotionWorkflow()

    event = workflow.evaluate(proposal)

    assert event is None


def test_proxy_production_blocked():
    """Verify proxy models cannot reach PRODUCTION via workflow."""
    proposal = create_proxy_production_proposal()
    workflow = PromotionWorkflow()

    event = workflow.evaluate(proposal)

    assert event is None


def test_policy_can_promote_approved():
    """Verify policy allows approved proposals."""
    proposal = create_approved_crypto_proposal()
    policy = WorkflowPolicy()

    can_promote, reason_codes = policy.can_promote(proposal)

    assert can_promote is True
    assert "PROMOTION_APPROVED" in reason_codes


def test_policy_blocks_rejected():
    """Verify policy blocks rejected proposals."""
    proposal = create_rejected_proposal()
    policy = WorkflowPolicy()

    can_promote, reason_codes = policy.can_promote(proposal)

    assert can_promote is False
    assert "PROPOSAL_REJECTED" in reason_codes


def test_policy_blocks_proxy_production():
    """Verify policy blocks proxy models from PRODUCTION."""
    proposal = create_proxy_production_proposal()
    policy = WorkflowPolicy()

    can_promote, reason_codes = policy.can_promote(proposal)

    assert can_promote is False
    assert "PROXY_CANNOT_BE_PRODUCTION" in reason_codes


def test_approve_creates_event():
    """Verify approve() creates promotion event."""
    proposal = create_approved_crypto_proposal()
    workflow = PromotionWorkflow()

    event = workflow.approve(proposal)

    assert event is not None
    assert event.decision == "APPROVED"
    assert event.from_state == "VALIDATED"
    assert event.to_state == "APPROVED"
    assert "WORKFLOW_APPROVED" in event.reason_codes


def test_reject_creates_event():
    """Verify reject() creates rejection event."""
    proposal = create_rejected_proposal()
    workflow = PromotionWorkflow()

    event = workflow.reject(proposal)

    assert event is not None
    assert event.decision == "REJECTED"
    assert event.from_state == "DISCOVERED"
    assert event.to_state == "DISCOVERED"
    assert "WORKFLOW_REJECTED" in event.reason_codes


def test_workflow_never_mutates_proposal():
    """Verify workflow never mutates input proposal."""
    proposal = create_approved_crypto_proposal()

    proposal_before = (
        proposal.model_id,
        proposal.status,
        proposal.current_state,
        proposal.proposed_state,
    )

    workflow = PromotionWorkflow()
    workflow.evaluate(proposal)

    proposal_after = (
        proposal.model_id,
        proposal.status,
        proposal.current_state,
        proposal.proposed_state,
    )

    assert proposal_before == proposal_after


def test_event_ids_unique_per_transition():
    """Verify event IDs differ for different transitions."""
    proposal = create_approved_crypto_proposal()
    workflow = PromotionWorkflow()

    event1 = workflow.approve(proposal)

    score2 = PromotionScore(
        model_id="models/btc_model.pkl",
        validation_score=1.0,
        calibration_score=1.0,
        lifecycle_score=1.0,
        governance_score=1.0,
        total_score=1.0,
    )

    proposal2 = RegistryProposal(
        model_id="models/btc_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state="APPROVED",
        proposed_state="PRODUCTION",
        status=PromotionStatus.APPROVED,
        score=score2,
        reason_codes=("CRYPTO_APPROVED_TO_PRODUCTION",),
    )

    event2 = workflow.approve(proposal2)

    assert event1.event_id != event2.event_id


def test_blocked_proposal_workflow():
    """Verify BLOCKED proposals cannot create events."""
    score = PromotionScore(
        model_id="models/blocked.pkl",
        validation_score=1.0,
        calibration_score=1.0,
        lifecycle_score=1.0,
        governance_score=1.0,
        total_score=1.0,
    )

    proposal = RegistryProposal(
        model_id="models/blocked.pkl",
        symbol="SPY",
        asset_class="PROXY",
        current_state="APPROVED",
        proposed_state="APPROVED",
        status=PromotionStatus.BLOCKED,
        score=score,
        reason_codes=("PROXY_BLOCKED_FROM_PRODUCTION",),
    )

    workflow = PromotionWorkflow()
    event = workflow.evaluate(proposal)

    assert event is None


def test_reason_codes_accumulate():
    """Verify workflow appends reason codes to proposal codes."""
    proposal = create_approved_crypto_proposal()
    workflow = PromotionWorkflow()

    event = workflow.approve(proposal)

    assert "CRYPTO_VALIDATED_TO_APPROVED" in event.reason_codes
    assert "WORKFLOW_APPROVED" in event.reason_codes
    assert len(event.reason_codes) >= 2
