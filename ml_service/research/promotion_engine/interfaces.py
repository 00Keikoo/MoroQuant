"""Promotion Engine Interfaces - Sprint 3.9D-8

Protocol definitions for promotion decision components.
ADR-024 compliant: research layer only, no database dependencies.
"""

from typing import Protocol
from ml_service.research.promotion_engine.models import PromotionScore, RegistryProposal
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import ModelLifecycleRecord


class IPromotionScorer(Protocol):
    """Protocol for calculating promotion scores."""

    def calculate_score(
        self,
        model_identity: ModelIdentity,
        lifecycle_record: ModelLifecycleRecord,
        audit_report: dict,
    ) -> PromotionScore:
        """Calculate weighted promotion score from inputs."""
        ...


class IPromotionPolicy(Protocol):
    """Protocol for applying promotion rules."""

    def evaluate(
        self,
        model_identity: ModelIdentity,
        lifecycle_record: ModelLifecycleRecord,
        score: PromotionScore,
    ) -> tuple[str, str, tuple[str, ...]]:
        """Evaluate promotion eligibility.

        Returns:
            (proposed_state, status, reason_codes)
        """
        ...


class IPromotionEngine(Protocol):
    """Protocol for the promotion decision engine."""

    def evaluate(
        self,
        model_identity: ModelIdentity,
        lifecycle_record: ModelLifecycleRecord,
        audit_report: dict,
    ) -> RegistryProposal:
        """Evaluate model candidate and produce promotion proposal."""
        ...
