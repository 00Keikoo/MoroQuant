"""Tests for Research Governance Engine - Sprint 3.9D-3

Validates governance policy evaluation and registry proposal generation.
"""

import pytest
from ml_service.research.promotion.models import PromotionDecision, PromotionStatus
from ml_service.research.governance.models import GovernanceAction, RegistryProposal
from ml_service.research.governance.policy import GovernancePolicy
from ml_service.research.governance.governance import DefaultGovernanceEngine


class TestRegistryProposal:
    """Test RegistryProposal immutability and validation."""

    def test_registry_proposal_immutability(self):
        """Verify frozen dataclass prevents modification."""
        from ml_service.research.promotion_engine.models import PromotionScore, PromotionStatus

        score = PromotionScore(
            model_id="test_model_v1",
            validation_score=0.85,
            calibration_score=0.82,
            lifecycle_score=0.80,
            governance_score=0.83,
            total_score=0.825,
        )
        proposal = RegistryProposal(
            model_id="test_model_v1",
            symbol="TEST",
            asset_class="CRYPTO",
            current_state="VALIDATED",
            proposed_state="APPROVED_RESEARCH",
            status=PromotionStatus.APPROVED,
            score=score,
            reason_codes=("APPROVED",),
        )

        with pytest.raises(AttributeError):
            proposal.model_id = "modified"

        with pytest.raises(AttributeError):
            proposal.status = PromotionStatus.REJECTED

    def test_registry_proposal_validation_score_ranges(self):
        """Verify score validation."""
        from ml_service.research.promotion_engine.models import PromotionScore, PromotionStatus

        # Test invalid validation_score
        with pytest.raises(ValueError, match="validation_score must be between"):
            PromotionScore(
                model_id="test",
                validation_score=1.5,
                calibration_score=0.8,
                lifecycle_score=0.7,
                governance_score=0.8,
                total_score=0.95,
            )

        # Test invalid total_score mismatch
        with pytest.raises(ValueError, match="total_score.*does not match"):
            PromotionScore(
                model_id="test",
                validation_score=0.8,
                calibration_score=0.8,
                lifecycle_score=0.7,
                governance_score=0.8,
                total_score=0.99,  # Wrong total
            )

    def test_registry_proposal_deterministic_serialization(self):
        """Verify deterministic JSON serialization."""
        from ml_service.research.promotion_engine.models import PromotionScore, PromotionStatus

        score = PromotionScore(
            model_id="test_model",
            validation_score=0.75,
            calibration_score=0.70,
            lifecycle_score=0.72,
            governance_score=0.73,
            total_score=0.727,  # 0.75*0.3 + 0.70*0.2 + 0.72*0.3 + 0.73*0.2
        )
        proposal = RegistryProposal(
            model_id="test_model",
            symbol="TEST",
            asset_class="CRYPTO",
            current_state="VALIDATED",
            proposed_state="GOVERNANCE_READY",
            status=PromotionStatus.CANDIDATE,
            score=score,
            reason_codes=("REVIEW",),
        )

        json1 = proposal.to_json()
        json2 = proposal.to_json()

        assert json1 == json2
        # Verify keys are sorted
        assert '"asset_class"' in json1
        assert json1.index('"asset_class"') < json1.index('"model_id"')
        assert json1.index('"model_id"') < json1.index('"symbol"')


class TestGovernancePolicy:
    """Test GovernancePolicy validation."""

    def test_policy_score_validation(self):
        """Verify minimum_score range validation."""
        with pytest.raises(ValueError):
            GovernancePolicy(minimum_score=-0.1)

        with pytest.raises(ValueError):
            GovernancePolicy(minimum_score=1.1)

        policy = GovernancePolicy(minimum_score=0.75)
        assert policy.minimum_score == 0.75


class TestDefaultGovernanceEngine:
    """Test DefaultGovernanceEngine policy evaluation."""

    def test_promoted_model_requires_review(self):
        """PROMOTE with manual review required should produce CANDIDATE status."""
        from ml_service.research.promotion_engine.models import PromotionStatus as CanonicalStatus

        engine = DefaultGovernanceEngine(
            GovernancePolicy(
                minimum_score=0.75,
                require_manual_review=True
            )
        )

        decision = PromotionDecision(
            model_id="candidate_model_v2",
            decision=PromotionStatus.PROMOTE,
            reason="Score improvement detected",
            candidate_score=0.85,
            current_score=0.80,
            score_delta=0.05
        )

        proposal = engine.evaluate(decision)

        assert proposal.status == CanonicalStatus.CANDIDATE
        assert proposal.model_id == "candidate_model_v2"
        assert proposal.proposed_state == "GOVERNANCE_READY"
        assert proposal.score.total_score == 0.85

    def test_promoted_model_auto_approve(self):
        """PROMOTE without manual review and satisfying score should produce APPROVED."""
        from ml_service.research.promotion_engine.models import PromotionStatus as CanonicalStatus

        engine = DefaultGovernanceEngine(
            GovernancePolicy(
                minimum_score=0.75,
                require_manual_review=False
            )
        )

        decision = PromotionDecision(
            model_id="candidate_model_v3",
            decision=PromotionStatus.PROMOTE,
            reason="Strong performance improvement",
            candidate_score=0.88,
            current_score=0.75,
            score_delta=0.13
        )

        proposal = engine.evaluate(decision)

        assert proposal.status == CanonicalStatus.APPROVED
        assert proposal.model_id == "candidate_model_v3"
        assert proposal.proposed_state == "APPROVED_RESEARCH"
        assert proposal.score.total_score == 0.88

    def test_promoted_model_below_threshold_rejected(self):
        """PROMOTE with score below minimum should produce REJECTED."""
        from ml_service.research.promotion_engine.models import PromotionStatus as CanonicalStatus

        engine = DefaultGovernanceEngine(
            GovernancePolicy(
                minimum_score=0.80,
                require_manual_review=False
            )
        )

        decision = PromotionDecision(
            model_id="weak_model_v1",
            decision=PromotionStatus.PROMOTE,
            reason="Marginal improvement",
            candidate_score=0.72,
            current_score=0.70,
            score_delta=0.02
        )

        proposal = engine.evaluate(decision)

        assert proposal.status == CanonicalStatus.REJECTED
        assert proposal.proposed_state == "REJECTED"
        assert proposal.score.total_score == 0.72

    def test_rejected_model(self):
        """REJECT decision should produce REJECTED status."""
        from ml_service.research.promotion_engine.models import PromotionStatus as CanonicalStatus

        engine = DefaultGovernanceEngine(
            GovernancePolicy(
                minimum_score=0.75,
                require_manual_review=True
            )
        )

        decision = PromotionDecision(
            model_id="failed_model_v1",
            decision=PromotionStatus.REJECT,
            reason="Performance degradation",
            candidate_score=0.65,
            current_score=0.80,
            score_delta=-0.15
        )

        proposal = engine.evaluate(decision)

        assert proposal.status == CanonicalStatus.REJECTED
        assert proposal.model_id == "failed_model_v1"
        assert proposal.proposed_state == "REJECTED"
        assert proposal.score.total_score == 0.65

    def test_deterministic_governance_output(self):
        """Same input should produce identical proposal."""
        engine = DefaultGovernanceEngine(
            GovernancePolicy(
                minimum_score=0.75,
                require_manual_review=True
            )
        )

        decision = PromotionDecision(
            model_id="test_model",
            decision=PromotionStatus.PROMOTE,
            reason="Test",
            candidate_score=0.80,
            current_score=0.75,
            score_delta=0.05,
            metrics=(("sharpe", 1.5), ("returns", 0.12))
        )

        proposal1 = engine.evaluate(decision)
        proposal2 = engine.evaluate(decision)

        assert proposal1.to_json() == proposal2.to_json()
        assert proposal1.model_id == proposal2.model_id
        assert proposal1.status == proposal2.status
        assert proposal1.score.total_score == proposal2.score.total_score

    def test_metadata_preservation(self):
        """Verify decision score is preserved in proposal."""
        from ml_service.research.promotion_engine.models import PromotionStatus as CanonicalStatus

        engine = DefaultGovernanceEngine(
            GovernancePolicy(require_manual_review=False)
        )

        decision = PromotionDecision(
            model_id="test",
            decision=PromotionStatus.PROMOTE,
            reason="test",
            candidate_score=0.85,
            current_score=0.80,
            score_delta=0.05
        )

        proposal = engine.evaluate(decision)

        assert proposal.status == CanonicalStatus.APPROVED
        assert proposal.score.total_score == 0.85
        assert proposal.score.model_id == "test"


class TestForbiddenDependencies:
    """Verify ADR-024 compliance - no forbidden dependencies."""

    def test_no_forbidden_dependencies(self):
        """Verify governance module has no database or service dependencies."""
        import ml_service.research.governance.governance as gov_module
        import ml_service.research.governance.models as models_module
        import ml_service.research.governance.policy as policy_module

        forbidden_imports = [
            'sqlite',
            'sqlalchemy',
            'PortfolioService',
            'ExecutionSimulator',
            'ModelRegistryService'
        ]

        for module in [gov_module, models_module, policy_module]:
            module_globals = dir(module)
            for forbidden in forbidden_imports:
                assert forbidden not in module_globals, \
                    f"Found forbidden dependency {forbidden} in {module.__name__}"

    def test_governance_is_pure_functional(self):
        """Verify governance engine is stateless and deterministic."""
        from ml_service.research.promotion_engine.models import PromotionStatus as CanonicalStatus

        policy = GovernancePolicy(minimum_score=0.75, require_manual_review=False)
        engine = DefaultGovernanceEngine(policy)

        decision = PromotionDecision(
            model_id="test",
            decision=PromotionStatus.PROMOTE,
            reason="test",
            candidate_score=0.85,
            current_score=0.80,
            score_delta=0.05
        )

        results = [engine.evaluate(decision) for _ in range(10)]

        first_json = results[0].to_json()
        assert all(r.to_json() == first_json for r in results)
        assert all(r.status == CanonicalStatus.APPROVED for r in results)
