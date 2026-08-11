"""Registry Query Models - Sprint 3.9D-11

Immutable query result models for registry queries.
ADR-024 compliant: research layer only, no database, no execution dependencies.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RegistryQueryResult:
    """Immutable query result container.

    Generic container for query results with metadata.
    """
    query_type: str
    result_count: int
    results: tuple
    metadata: Optional[dict] = None

    def __post_init__(self):
        if not self.query_type:
            raise ValueError("query_type cannot be empty")
        if not isinstance(self.results, tuple):
            raise TypeError(f"results must be tuple, got {type(self.results)}")
        if self.result_count < 0:
            raise ValueError(f"result_count must be non-negative, got {self.result_count}")
        if len(self.results) != self.result_count:
            raise ValueError(
                f"result_count {self.result_count} does not match results length {len(self.results)}"
            )


@dataclass(frozen=True)
class ModelSummary:
    """Lightweight model summary for list queries."""
    model_id: str
    symbol: str
    timeframe: str
    asset_class: str
    lifecycle_state: str
    latest_event_type: Optional[str] = None


@dataclass(frozen=True)
class RegistrySummary:
    """Summary statistics for entire registry."""
    total_models: int
    by_asset_class: dict
    by_lifecycle_state: dict
    production_count: int
    approved_count: int
