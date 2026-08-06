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
        proposal = RegistryProposal(
            model_id="test_model_v1",
            action=GovernanceAction.APPROVE,
            reason="Test approval",
            promotion_score=0.85,
            benchmark_score=0.82,
            metadata=(("key1", "value1"), ("key2", 42))
        )

        with pytest.raises(AttributeError):
            proposal.model_id = "modified"

        with pytest.raises(AttributeError):
            proposal.action = GovernanceAction.REJECT

    def test_registry_proposal_validation_score_ranges(self):
        """Verify score validation."""
        with pytest.raises(ValueError, match="promotion_score must be in"):
            RegistryProposal(
                model_id="test",
                action=GovernanceAction.APPROVE,
                reason="test",
                promotion_score=1.5,
                benchmark_score=0.8
            )

        with pytest.raises(ValueError, match="benchmark_score must be in"):
            RegistryProposal(
                model_id="test",
                action=GovernanceAction.APPROVE,
                reason="test",
                promotion_score=0.8,
                benchmark_score=2.0
            )

    def test_registry_proposal_deterministic_serialization(self):
        """Verify deterministic JSON serialization."""
        proposal = RegistryProposal(
            model_id="test_model",
            action=GovernanceAction.REVIEW,
            reason="Manual review",
            promotion_score=0.75,
            benchmark_score=0.70,
            metadata=(("z_key", "last"), ("a_key", "first"), ("m_key", "middle"))
        )

        json1 = proposal.to_json()
        json2 = proposal.to_json()

        assert json1 == json2
        assert '"a_key"' in json1
        assert json1.index('"a_key"') < json1.index('"m_key"')
        assert json1.index('"m_key"') < json1.index('"z_key"')


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
        """PROMOTE with manual review required should produce REVIEW action."""
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

        assert proposal.action == GovernanceAction.REVIEW
        assert proposal.model_id == "candidate_model_v2"
        assert "Manual review required" in proposal.reason
        assert proposal.benchmark_score == 0.85

    def test_promoted_model_auto_approve(self):
        """PROMOTE without manual review and satisfying score should produce APPROVE."""
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

        assert proposal.action == GovernanceAction.APPROVE
        assert proposal.model_id == "candidate_model_v3"
        assert "approved" in proposal.reason.lower()
        assert proposal.benchmark_score == 0.88

    def test_promoted_model_below_threshold_rejected(self):
        """PROMOTE with score below minimum should produce REJECT."""
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

        assert proposal.action == GovernanceAction.REJECT
        assert "below minimum" in proposal.reason.lower()
        assert proposal.benchmark_score == 0.72

    def test_rejected_model(self):
        """REJECT decision should produce REJECT action."""
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

        assert proposal.action == GovernanceAction.REJECT
        assert proposal.model_id == "failed_model_v1"
        assert "rejected" in proposal.reason.lower()
        assert proposal.benchmark_score == 0.65

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
        assert proposal1.action == proposal2.action
        assert proposal1.promotion_score == proposal2.promotion_score

    def test_metadata_preservation(self):
        """Verify decision metrics are preserved in proposal metadata."""
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

        metadata_dict = dict(proposal.metadata)
        assert metadata_dict["candidate_score"] == 0.85
        assert metadata_dict["current_score"] == 0.80
        assert metadata_dict["score_delta"] == 0.05


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
