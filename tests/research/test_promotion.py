"""Tests for Research Promotion Engine - Sprint 3.9D-2

Validates pure functional promotion decision system.
"""

import pytest
from ml_service.research.promotion.models import PromotionStatus, PromotionDecision
from ml_service.research.promotion.rules import PromotionCriteria, evaluate_promotion_rules
from ml_service.research.promotion.promotion import DefaultPromotionEngine
from ml_service.research.benchmark.models import BenchmarkResult


class TestPromotionDecisionImmutability:
    """Test that PromotionDecision is truly immutable."""

    def test_promotion_decision_immutability(self):
        """Verify frozen dataclass prevents mutation."""
        decision = PromotionDecision(
            model_id="test_model",
            decision=PromotionStatus.PROMOTE,
            reason="Test reason",
            candidate_score=0.75,
            current_score=0.65,
            score_delta=0.10,
            metrics=(("win_rate", 0.60), ("max_drawdown", 0.15))
        )

        with pytest.raises(AttributeError):
            decision.model_id = "new_id"

        with pytest.raises(AttributeError):
            decision.decision = PromotionStatus.REJECT

        with pytest.raises(AttributeError):
            decision.candidate_score = 0.80

    def test_promotion_decision_validation(self):
        """Verify score range validation."""
        with pytest.raises(ValueError, match="candidate_score must be in"):
            PromotionDecision(
                model_id="test_model",
                decision=PromotionStatus.PROMOTE,
                reason="Test",
                candidate_score=1.5,
                current_score=0.5,
                score_delta=1.0
            )

        with pytest.raises(ValueError, match="current_score must be in"):
            PromotionDecision(
                model_id="test_model",
                decision=PromotionStatus.PROMOTE,
                reason="Test",
                candidate_score=0.5,
                current_score=-1.5,
                score_delta=2.0
            )

        with pytest.raises(ValueError, match="model_id cannot be empty"):
            PromotionDecision(
                model_id="",
                decision=PromotionStatus.PROMOTE,
                reason="Test",
                candidate_score=0.5,
                current_score=0.4,
                score_delta=0.1
            )


class TestPromotionDecisions:
    """Test promotion decision logic."""

    def test_promote_candidate(self):
        """Candidate significantly better than current should PROMOTE."""
        candidate_report = BenchmarkResult(
            benchmark_id="bench_001",
            compared_experiments=("candidate_model",),
            ranking=("candidate_model",),
            winner="candidate_model",
            scores=(("candidate_model", 0.75),),
            metrics=(("win_rate", 0.60), ("max_drawdown", 0.15))
        )

        current_report = BenchmarkResult(
            benchmark_id="bench_002",
            compared_experiments=("current_model",),
            ranking=("current_model",),
            winner="current_model",
            scores=(("current_model", 0.65),),
            metrics=(("win_rate", 0.55), ("max_drawdown", 0.18))
        )

        engine = DefaultPromotionEngine()
        decision = engine.evaluate(candidate_report, current_report)

        assert decision.decision == PromotionStatus.PROMOTE
        assert decision.model_id == "candidate_model"
        assert decision.candidate_score == 0.75
        assert decision.current_score == 0.65
        assert decision.score_delta == pytest.approx(0.10)
        assert "meets all promotion criteria" in decision.reason

    def test_reject_candidate(self):
        """Candidate worse than current should REJECT."""
        candidate_report = BenchmarkResult(
            benchmark_id="bench_003",
            compared_experiments=("candidate_model",),
            ranking=("candidate_model",),
            winner="candidate_model",
            scores=(("candidate_model", 0.55),),
            metrics=(("win_rate", 0.50), ("max_drawdown", 0.20))
        )

        current_report = BenchmarkResult(
            benchmark_id="bench_004",
            compared_experiments=("current_model",),
            ranking=("current_model",),
            winner="current_model",
            scores=(("current_model", 0.70),),
            metrics=(("win_rate", 0.58), ("max_drawdown", 0.15))
        )

        engine = DefaultPromotionEngine()
        decision = engine.evaluate(candidate_report, current_report)

        assert decision.decision == PromotionStatus.REJECT
        assert "lower than current score" in decision.reason

    def test_hold_candidate_insufficient_delta(self):
        """Candidate improvement below threshold should HOLD."""
        candidate_report = BenchmarkResult(
            benchmark_id="bench_005",
            compared_experiments=("candidate_model",),
            ranking=("candidate_model",),
            winner="candidate_model",
            scores=(("candidate_model", 0.67),),
            metrics=(("win_rate", 0.58), ("max_drawdown", 0.16))
        )

        current_report = BenchmarkResult(
            benchmark_id="bench_006",
            compared_experiments=("current_model",),
            ranking=("current_model",),
            winner="current_model",
            scores=(("current_model", 0.65),),
            metrics=(("win_rate", 0.57), ("max_drawdown", 0.17))
        )

        engine = DefaultPromotionEngine(criteria=PromotionCriteria(minimum_score_delta=0.05))
        decision = engine.evaluate(candidate_report, current_report)

        assert decision.decision == PromotionStatus.HOLD
        assert "below minimum threshold" in decision.reason

    def test_hold_candidate_low_win_rate(self):
        """Candidate with low win rate should HOLD."""
        candidate_report = BenchmarkResult(
            benchmark_id="bench_007",
            compared_experiments=("candidate_model",),
            ranking=("candidate_model",),
            winner="candidate_model",
            scores=(("candidate_model", 0.75),),
            metrics=(("win_rate", 0.50), ("max_drawdown", 0.15))
        )

        current_report = BenchmarkResult(
            benchmark_id="bench_008",
            compared_experiments=("current_model",),
            ranking=("current_model",),
            winner="current_model",
            scores=(("current_model", 0.65),),
            metrics=(("win_rate", 0.58), ("max_drawdown", 0.16))
        )

        engine = DefaultPromotionEngine()
        decision = engine.evaluate(candidate_report, current_report)

        assert decision.decision == PromotionStatus.HOLD
        assert "Win rate" in decision.reason

    def test_hold_candidate_high_drawdown(self):
        """Candidate with high drawdown should HOLD."""
        candidate_report = BenchmarkResult(
            benchmark_id="bench_009",
            compared_experiments=("candidate_model",),
            ranking=("candidate_model",),
            winner="candidate_model",
            scores=(("candidate_model", 0.75),),
            metrics=(("win_rate", 0.60), ("max_drawdown", 0.25))
        )

        current_report = BenchmarkResult(
            benchmark_id="bench_010",
            compared_experiments=("current_model",),
            ranking=("current_model",),
            winner="current_model",
            scores=(("current_model", 0.65),),
            metrics=(("win_rate", 0.58), ("max_drawdown", 0.15))
        )

        engine = DefaultPromotionEngine()
        decision = engine.evaluate(candidate_report, current_report)

        assert decision.decision == PromotionStatus.HOLD
        assert "Max drawdown" in decision.reason


class TestDeterministicDecision:
    """Test determinism of promotion decisions."""

    def test_deterministic_decision(self):
        """Same input produces identical output."""
        candidate_report = BenchmarkResult(
            benchmark_id="bench_011",
            compared_experiments=("candidate_model",),
            ranking=("candidate_model",),
            winner="candidate_model",
            scores=(("candidate_model", 0.75),),
            metrics=(("win_rate", 0.60), ("max_drawdown", 0.15))
        )

        current_report = BenchmarkResult(
            benchmark_id="bench_012",
            compared_experiments=("current_model",),
            ranking=("current_model",),
            winner="current_model",
            scores=(("current_model", 0.65),),
            metrics=(("win_rate", 0.55), ("max_drawdown", 0.18))
        )

        engine = DefaultPromotionEngine()

        decision1 = engine.evaluate(candidate_report, current_report)
        decision2 = engine.evaluate(candidate_report, current_report)

        assert decision1.model_id == decision2.model_id
        assert decision1.decision == decision2.decision
        assert decision1.reason == decision2.reason
        assert decision1.candidate_score == decision2.candidate_score
        assert decision1.current_score == decision2.current_score
        assert decision1.score_delta == decision2.score_delta
        assert decision1.metrics == decision2.metrics

        assert decision1.to_json() == decision2.to_json()


class TestNoDatabaseOrExecutionDependency:
    """Test that promotion engine has no forbidden dependencies."""

    def test_no_database_or_execution_dependency(self):
        """Verify no imports of sqlite, sqlalchemy, PortfolioService, or ExecutionSimulator."""
        import ml_service.research.promotion.models as models_module
        import ml_service.research.promotion.rules as rules_module
        import ml_service.research.promotion.promotion as promotion_module
        import ml_service.research.promotion.interfaces as interfaces_module

        modules = [models_module, rules_module, promotion_module, interfaces_module]

        forbidden_imports = [
            'sqlite3',
            'sqlalchemy',
            'PortfolioService',
            'ExecutionSimulator',
            'portfolio_service',
            'execution_simulator'
        ]

        for module in modules:
            module_dict = dir(module)
            for forbidden in forbidden_imports:
                assert forbidden not in module_dict, f"Found forbidden import {forbidden} in {module.__name__}"

        import sys
        loaded_modules = sys.modules.keys()

        for module_name in loaded_modules:
            if 'promotion' in module_name:
                for forbidden in ['sqlite', 'sqlalchemy', 'portfolio_service', 'execution_simulator']:
                    assert forbidden not in module_name.lower(), f"Promotion module loaded forbidden dependency: {module_name}"


class TestPromotionCriteria:
    """Test promotion criteria validation."""

    def test_criteria_validation(self):
        """Verify criteria parameter validation."""
        with pytest.raises(ValueError, match="minimum_score_delta must be non-negative"):
            PromotionCriteria(minimum_score_delta=-0.1)

        with pytest.raises(ValueError, match="minimum_win_rate must be in"):
            PromotionCriteria(minimum_win_rate=1.5)

        with pytest.raises(ValueError, match="maximum_drawdown must be in"):
            PromotionCriteria(maximum_drawdown=-0.1)

    def test_custom_criteria(self):
        """Test engine with custom criteria."""
        custom_criteria = PromotionCriteria(
            minimum_score_delta=0.05,
            minimum_win_rate=0.60,
            maximum_drawdown=0.15
        )

        candidate_report = BenchmarkResult(
            benchmark_id="bench_013",
            compared_experiments=("candidate_model",),
            ranking=("candidate_model",),
            winner="candidate_model",
            scores=(("candidate_model", 0.75),),
            metrics=(("win_rate", 0.58), ("max_drawdown", 0.14))
        )

        current_report = BenchmarkResult(
            benchmark_id="bench_014",
            compared_experiments=("current_model",),
            ranking=("current_model",),
            winner="current_model",
            scores=(("current_model", 0.65),),
            metrics=(("win_rate", 0.55), ("max_drawdown", 0.16))
        )

        engine = DefaultPromotionEngine(criteria=custom_criteria)
        decision = engine.evaluate(candidate_report, current_report)

        assert decision.decision == PromotionStatus.HOLD
        assert "Win rate" in decision.reason


class TestPromotionSerialization:
    """Test deterministic serialization."""

    def test_decision_serialization(self):
        """Verify deterministic JSON serialization."""
        decision = PromotionDecision(
            model_id="test_model",
            decision=PromotionStatus.PROMOTE,
            reason="Excellent performance",
            candidate_score=0.75,
            current_score=0.65,
            score_delta=0.10,
            metrics=(("win_rate", 0.60), ("max_drawdown", 0.15), ("sharpe", 2.1))
        )

        json1 = decision.to_json()
        json2 = decision.to_json()

        assert json1 == json2

        decision_dict = decision.to_dict()
        assert decision_dict["model_id"] == "test_model"
        assert decision_dict["decision"] == "PROMOTE"
        assert decision_dict["candidate_score"] == 0.75
        assert decision_dict["metrics"] == [["max_drawdown", 0.15], ["sharpe", 2.1], ["win_rate", 0.60]]
