"""Registry API Service - Sprint 3.9D-12

Business logic layer for registry API.
ADR-024 compliant: delegates to registry_query, no database access.
"""

from typing import Optional

from ml_service.research.registry_api.schemas import (
    ModelSummaryResponse,
    ModelListResponse,
    ModelDetailResponse,
    RegistrySummaryResponse,
    ProductionCandidatesResponse,
    HistoryRecordResponse,
    ModelHistoryResponse,
)
from ml_service.research.registry_query import RegistryQueryEngine
from ml_service.research.registry_query.models import ModelSummary


class RegistryAPIService:
    """Service layer for registry governance API.

    Converts registry_query results to API response schemas.
    """

    def __init__(self, query_engine: RegistryQueryEngine):
        self.query_engine = query_engine

    def list_models(self) -> ModelListResponse:
        """Get all models in registry.

        Returns:
            ModelListResponse with all models
        """
        result = self.query_engine.list_models()

        models = tuple(
            ModelSummaryResponse(
                model_id=m.model_id,
                symbol=m.symbol,
                timeframe=m.timeframe,
                asset_class=m.asset_class,
                lifecycle_state=m.lifecycle_state,
                latest_event_type=m.latest_event_type,
            )
            for m in result.results
        )

        return ModelListResponse(
            query_type=result.query_type,
            result_count=result.result_count,
            models=models,
        )

    def get_model_by_id(self, artifact_id: str) -> Optional[ModelDetailResponse]:
        """Get model detail by artifact ID.

        Args:
            artifact_id: Model artifact path

        Returns:
            ModelDetailResponse if found, None otherwise
        """
        result = self.query_engine.list_models()

        for m in result.results:
            model_summary: ModelSummary = m
            if model_summary.model_id == artifact_id:
                return ModelDetailResponse(
                    model_id=model_summary.model_id,
                    symbol=model_summary.symbol,
                    timeframe=model_summary.timeframe,
                    asset_class=model_summary.asset_class,
                    lifecycle_state=model_summary.lifecycle_state,
                    latest_event_type=model_summary.latest_event_type,
                )

        return None

    def get_registry_summary(self) -> RegistrySummaryResponse:
        """Get registry summary statistics.

        Returns:
            RegistrySummaryResponse with aggregated statistics
        """
        summary = self.query_engine.get_registry_summary()

        return RegistrySummaryResponse(
            total_models=summary.total_models,
            by_asset_class=summary.by_asset_class,
            by_lifecycle_state=summary.by_lifecycle_state,
            production_count=summary.production_count,
            approved_count=summary.approved_count,
        )

    def get_production_candidates(self) -> ProductionCandidatesResponse:
        """Get models ready for production promotion.

        Returns:
            ProductionCandidatesResponse with candidate models
        """
        result = self.query_engine.get_production_candidates()

        candidates = tuple(
            ModelSummaryResponse(
                model_id=m.model_id,
                symbol=m.symbol,
                timeframe=m.timeframe,
                asset_class=m.asset_class,
                lifecycle_state=m.lifecycle_state,
                latest_event_type=m.latest_event_type,
            )
            for m in result.results
        )

        return ProductionCandidatesResponse(
            query_type=result.query_type,
            result_count=result.result_count,
            candidates=candidates,
        )

    def get_model_history(self, artifact_id: str) -> Optional[ModelHistoryResponse]:
        """Get lifecycle history for model.

        Args:
            artifact_id: Model artifact path

        Returns:
            ModelHistoryResponse if model exists, None otherwise
        """
        result = self.query_engine.get_lifecycle_history(artifact_id)

        if result.result_count == 0:
            return None

        history = tuple(
            HistoryRecordResponse(
                artifact_path=record.model_id,
                event_type=record.event_type,
                from_state=None,
                to_state=None,
                timestamp=record.created_at,
                metadata=None,
            )
            for record in result.results
        )

        return ModelHistoryResponse(
            query_type=result.query_type,
            result_count=result.result_count,
            model_id=artifact_id,
            history=history,
        )
