"""Registry API Schemas - Sprint 3.9D-12

Immutable Pydantic schemas for API responses.
ADR-024 compliant: read-only, deterministic.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ModelSummaryResponse(BaseModel):
    """Model summary for list queries."""
    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model artifact identifier")
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Model timeframe")
    asset_class: str = Field(..., description="Asset class (CRYPTO, PROXY)")
    lifecycle_state: str = Field(..., description="Current lifecycle state")
    latest_event_type: Optional[str] = Field(None, description="Most recent event type")


class ModelListResponse(BaseModel):
    """Response for GET /registry/models."""
    model_config = ConfigDict(frozen=True)

    query_type: str = Field(..., description="Query type identifier")
    result_count: int = Field(..., description="Number of results")
    models: tuple[ModelSummaryResponse, ...] = Field(..., description="Model summaries")


class ModelDetailResponse(BaseModel):
    """Response for GET /registry/models/{artifact_id}."""
    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model artifact identifier")
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Model timeframe")
    asset_class: str = Field(..., description="Asset class")
    lifecycle_state: str = Field(..., description="Current lifecycle state")
    latest_event_type: Optional[str] = Field(None, description="Most recent event type")


class RegistrySummaryResponse(BaseModel):
    """Response for GET /registry/summary."""
    model_config = ConfigDict(frozen=True)

    total_models: int = Field(..., description="Total model count")
    by_asset_class: dict[str, int] = Field(..., description="Count by asset class")
    by_lifecycle_state: dict[str, int] = Field(..., description="Count by lifecycle state")
    production_count: int = Field(..., description="Models in PRODUCTION")
    approved_count: int = Field(..., description="Models in APPROVED")


class ProductionCandidatesResponse(BaseModel):
    """Response for GET /registry/production-candidates."""
    model_config = ConfigDict(frozen=True)

    query_type: str = Field(..., description="Query type identifier")
    result_count: int = Field(..., description="Number of candidates")
    candidates: tuple[ModelSummaryResponse, ...] = Field(..., description="Candidate models")


class HistoryRecordResponse(BaseModel):
    """Single history record."""
    model_config = ConfigDict(frozen=True)

    artifact_path: str = Field(..., description="Model artifact identifier")
    event_type: str = Field(..., description="Event type")
    from_state: Optional[str] = Field(None, description="Previous state")
    to_state: Optional[str] = Field(None, description="New state")
    timestamp: str = Field(..., description="Event timestamp")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class ModelHistoryResponse(BaseModel):
    """Response for GET /registry/history/{artifact_id}."""
    model_config = ConfigDict(frozen=True)

    query_type: str = Field(..., description="Query type identifier")
    result_count: int = Field(..., description="Number of history records")
    model_id: str = Field(..., description="Model artifact identifier")
    history: tuple[HistoryRecordResponse, ...] = Field(..., description="History records")
