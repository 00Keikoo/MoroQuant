"""Registry Query Engine - Sprint 3.9D-11

Read-only query layer combining RegistrySnapshot and RegistryEventLedger.
ADR-024 compliant: research layer only, no database, immutable outputs.
"""

from typing import Optional
from collections import defaultdict

from ml_service.research.registry_query.models import (
    RegistryQueryResult,
    ModelSummary,
    RegistrySummary,
)
from ml_service.research.registry_snapshot.snapshot import RegistrySnapshot
from ml_service.research.registry_event_ledger.service import RegistryEventLedger


class RegistryQueryEngine:
    """Read-only query interface for model governance data.

    Combines RegistrySnapshot (current state) with RegistryEventLedger (history)
    to provide comprehensive query capabilities.
    """

    def __init__(self, snapshot: RegistrySnapshot, ledger: RegistryEventLedger):
        self.snapshot = snapshot
        self.ledger = ledger

    def list_models(self) -> RegistryQueryResult:
        """List all models in registry with current state.

        Returns:
            RegistryQueryResult with tuple of ModelSummary objects
        """
        models = []

        for identity in self.snapshot.models:
            latest_event = self.ledger.latest_event(identity.artifact_path)
            event_type = latest_event.event_type if latest_event else None

            summary = ModelSummary(
                model_id=identity.artifact_path,
                symbol=identity.symbol,
                timeframe=identity.timeframe,
                asset_class=identity.asset_class,
                lifecycle_state=identity.lifecycle_status,
                latest_event_type=event_type,
            )
            models.append(summary)

        models_sorted = sorted(models, key=lambda m: (m.symbol, m.timeframe))

        return RegistryQueryResult(
            query_type="LIST_MODELS",
            result_count=len(models_sorted),
            results=tuple(models_sorted),
        )

    def find_model(self, symbol: str, timeframe: str) -> Optional[ModelSummary]:
        """Find model by symbol and timeframe.

        Args:
            symbol: Model symbol (e.g., "BTCUSD")
            timeframe: Model timeframe (e.g., "1h")

        Returns:
            ModelSummary if found, None otherwise
        """
        for identity in self.snapshot.models:
            if identity.symbol == symbol and identity.timeframe == timeframe:
                latest_event = self.ledger.latest_event(identity.artifact_path)
                event_type = latest_event.event_type if latest_event else None

                return ModelSummary(
                    model_id=identity.artifact_path,
                    symbol=identity.symbol,
                    timeframe=identity.timeframe,
                    asset_class=identity.asset_class,
                    lifecycle_state=identity.lifecycle_status,
                    latest_event_type=event_type,
                )

        return None

    def get_lifecycle_history(self, model_id: str) -> RegistryQueryResult:
        """Get lifecycle transition history for model.

        Args:
            model_id: Model artifact identifier

        Returns:
            RegistryQueryResult with lifecycle records
        """
        history = self.ledger.get_model_history(model_id)

        return RegistryQueryResult(
            query_type="LIFECYCLE_HISTORY",
            result_count=len(history),
            results=tuple(history),
            metadata={"model_id": model_id},
        )

    def get_promotion_history(self, model_id: str) -> RegistryQueryResult:
        """Get promotion event history for model.

        Args:
            model_id: Model artifact identifier

        Returns:
            RegistryQueryResult with promotion events
        """
        history = self.ledger.get_model_history(model_id)

        return RegistryQueryResult(
            query_type="PROMOTION_HISTORY",
            result_count=len(history),
            results=tuple(history),
            metadata={"model_id": model_id},
        )

    def get_production_candidates(self) -> RegistryQueryResult:
        """Get models ready for production promotion.

        Criteria:
        - Lifecycle state = APPROVED
        - Validation available
        - Calibration available
        - Asset class = CRYPTO (proxy models excluded)

        Returns:
            RegistryQueryResult with candidate models
        """
        candidates = []

        for identity in self.snapshot.models:
            if (
                identity.lifecycle_status == "APPROVED"
                and identity.validation_available
                and identity.calibration_available
                and identity.asset_class == "CRYPTO"
            ):
                latest_event = self.ledger.latest_event(identity.artifact_path)
                event_type = latest_event.event_type if latest_event else None

                summary = ModelSummary(
                    model_id=identity.artifact_path,
                    symbol=identity.symbol,
                    timeframe=identity.timeframe,
                    asset_class=identity.asset_class,
                    lifecycle_state=identity.lifecycle_status,
                    latest_event_type=event_type,
                )
                candidates.append(summary)

        candidates_sorted = sorted(candidates, key=lambda m: (m.symbol, m.timeframe))

        return RegistryQueryResult(
            query_type="PRODUCTION_CANDIDATES",
            result_count=len(candidates_sorted),
            results=tuple(candidates_sorted),
        )

    def get_registry_summary(self) -> RegistrySummary:
        """Get summary statistics for entire registry.

        Returns:
            RegistrySummary with aggregated statistics
        """
        by_asset_class = defaultdict(int)
        by_lifecycle_state = defaultdict(int)
        production_count = 0
        approved_count = 0

        for identity in self.snapshot.models:
            by_asset_class[identity.asset_class] += 1
            by_lifecycle_state[identity.lifecycle_status] += 1

            if identity.lifecycle_status == "PRODUCTION":
                production_count += 1
            elif identity.lifecycle_status == "APPROVED":
                approved_count += 1

        return RegistrySummary(
            total_models=len(self.snapshot.models),
            by_asset_class=dict(by_asset_class),
            by_lifecycle_state=dict(by_lifecycle_state),
            production_count=production_count,
            approved_count=approved_count,
        )
