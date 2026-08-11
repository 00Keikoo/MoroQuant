"""Registry API Tests - Sprint 3.9D-12

Tests for registry governance API layer.
ADR-024 compliant: read-only, deterministic, no database access in research layer.
"""

import pytest
from unittest.mock import Mock

from ml_service.research.registry_api.service import RegistryAPIService
from ml_service.research.registry_api.schemas import (
    ModelListResponse,
    ModelDetailResponse,
    RegistrySummaryResponse,
    ProductionCandidatesResponse,
    ModelHistoryResponse,
)
from ml_service.research.registry_query.models import (
    RegistryQueryResult,
    ModelSummary,
    RegistrySummary,
)
from ml_service.research.registry_event_ledger.models import RegistryEventRecord


class TestRegistryAPIService:
    """Test RegistryAPIService business logic."""

    @pytest.fixture
    def mock_query_engine(self):
        """Mock RegistryQueryEngine."""
        return Mock()

    @pytest.fixture
    def service(self, mock_query_engine):
        """Create RegistryAPIService with mock engine."""
        return RegistryAPIService(mock_query_engine)

    def test_list_models_empty(self, service, mock_query_engine):
        """Test list_models with no models."""
        mock_query_engine.list_models.return_value = RegistryQueryResult(
            query_type="LIST_MODELS",
            result_count=0,
            results=(),
        )

        response = service.list_models()

        assert isinstance(response, ModelListResponse)
        assert response.query_type == "LIST_MODELS"
        assert response.result_count == 0
        assert response.models == ()

    def test_list_models_with_data(self, service, mock_query_engine):
        """Test list_models with multiple models."""
        mock_query_engine.list_models.return_value = RegistryQueryResult(
            query_type="LIST_MODELS",
            result_count=2,
            results=(
                ModelSummary(
                    model_id="models/BTCUSD_1h/test",
                    symbol="BTCUSD",
                    timeframe="1h",
                    asset_class="CRYPTO",
                    lifecycle_state="APPROVED",
                    latest_event_type="LIFECYCLE_TRANSITION",
                ),
                ModelSummary(
                    model_id="models/ETHUSD_4h/test",
                    symbol="ETHUSD",
                    timeframe="4h",
                    asset_class="CRYPTO",
                    lifecycle_state="PRODUCTION",
                    latest_event_type="PROMOTED_TO_PRODUCTION",
                ),
            ),
        )

        response = service.list_models()

        assert isinstance(response, ModelListResponse)
        assert response.result_count == 2
        assert len(response.models) == 2
        assert response.models[0].symbol == "BTCUSD"
        assert response.models[1].symbol == "ETHUSD"

    def test_get_model_by_id_found(self, service, mock_query_engine):
        """Test get_model_by_id when model exists."""
        mock_query_engine.list_models.return_value = RegistryQueryResult(
            query_type="LIST_MODELS",
            result_count=1,
            results=(
                ModelSummary(
                    model_id="models/BTCUSD_1h/test",
                    symbol="BTCUSD",
                    timeframe="1h",
                    asset_class="CRYPTO",
                    lifecycle_state="APPROVED",
                    latest_event_type="LIFECYCLE_TRANSITION",
                ),
            ),
        )

        response = service.get_model_by_id("models/BTCUSD_1h/test")

        assert isinstance(response, ModelDetailResponse)
        assert response.model_id == "models/BTCUSD_1h/test"
        assert response.symbol == "BTCUSD"
        assert response.lifecycle_state == "APPROVED"

    def test_get_model_by_id_not_found(self, service, mock_query_engine):
        """Test get_model_by_id when model does not exist."""
        mock_query_engine.list_models.return_value = RegistryQueryResult(
            query_type="LIST_MODELS",
            result_count=0,
            results=(),
        )

        response = service.get_model_by_id("models/NONEXISTENT/test")

        assert response is None

    def test_get_registry_summary(self, service, mock_query_engine):
        """Test get_registry_summary returns aggregated statistics."""
        mock_query_engine.get_registry_summary.return_value = RegistrySummary(
            total_models=10,
            by_asset_class={"CRYPTO": 8, "PROXY": 2},
            by_lifecycle_state={"PRODUCTION": 3, "APPROVED": 5, "DEVELOPMENT": 2},
            production_count=3,
            approved_count=5,
        )

        response = service.get_registry_summary()

        assert isinstance(response, RegistrySummaryResponse)
        assert response.total_models == 10
        assert response.by_asset_class["CRYPTO"] == 8
        assert response.production_count == 3
        assert response.approved_count == 5

    def test_get_production_candidates_empty(self, service, mock_query_engine):
        """Test get_production_candidates with no candidates."""
        mock_query_engine.get_production_candidates.return_value = RegistryQueryResult(
            query_type="PRODUCTION_CANDIDATES",
            result_count=0,
            results=(),
        )

        response = service.get_production_candidates()

        assert isinstance(response, ProductionCandidatesResponse)
        assert response.result_count == 0
        assert response.candidates == ()

    def test_get_production_candidates_with_data(self, service, mock_query_engine):
        """Test get_production_candidates with multiple candidates."""
        mock_query_engine.get_production_candidates.return_value = RegistryQueryResult(
            query_type="PRODUCTION_CANDIDATES",
            result_count=2,
            results=(
                ModelSummary(
                    model_id="models/BTCUSD_1h/test",
                    symbol="BTCUSD",
                    timeframe="1h",
                    asset_class="CRYPTO",
                    lifecycle_state="APPROVED",
                    latest_event_type="LIFECYCLE_TRANSITION",
                ),
                ModelSummary(
                    model_id="models/ETHUSD_4h/test",
                    symbol="ETHUSD",
                    timeframe="4h",
                    asset_class="CRYPTO",
                    lifecycle_state="APPROVED",
                    latest_event_type="LIFECYCLE_TRANSITION",
                ),
            ),
        )

        response = service.get_production_candidates()

        assert response.result_count == 2
        assert len(response.candidates) == 2
        assert all(c.lifecycle_state == "APPROVED" for c in response.candidates)

    def test_get_model_history_found(self, service, mock_query_engine):
        """Test get_model_history when model exists."""
        mock_query_engine.get_lifecycle_history.return_value = RegistryQueryResult(
            query_type="LIFECYCLE_HISTORY",
            result_count=2,
            results=(
                RegistryEventRecord(
                    event_id="evt_001",
                    model_id="models/BTCUSD_1h/test",
                    event_type="LIFECYCLE_TRANSITION",
                    created_at="2026-08-11T10:00:00Z",
                    payload_hash="abc123",
                ),
                RegistryEventRecord(
                    event_id="evt_002",
                    model_id="models/BTCUSD_1h/test",
                    event_type="PROMOTED_TO_PRODUCTION",
                    created_at="2026-08-11T11:00:00Z",
                    payload_hash="def456",
                ),
            ),
            metadata={"model_id": "models/BTCUSD_1h/test"},
        )

        response = service.get_model_history("models/BTCUSD_1h/test")

        assert isinstance(response, ModelHistoryResponse)
        assert response.result_count == 2
        assert len(response.history) == 2
        assert response.model_id == "models/BTCUSD_1h/test"
        assert response.history[0].event_type == "LIFECYCLE_TRANSITION"

    def test_get_model_history_not_found(self, service, mock_query_engine):
        """Test get_model_history when model does not exist."""
        mock_query_engine.get_lifecycle_history.return_value = RegistryQueryResult(
            query_type="LIFECYCLE_HISTORY",
            result_count=0,
            results=(),
            metadata={"model_id": "models/NONEXISTENT/test"},
        )

        response = service.get_model_history("models/NONEXISTENT/test")

        assert response is None


class TestRegistryAPISchemas:
    """Test Pydantic schema validation and immutability."""

    def test_model_summary_response_immutable(self):
        """Test ModelSummaryResponse is immutable."""
        from ml_service.research.registry_api.schemas import ModelSummaryResponse

        response = ModelSummaryResponse(
            model_id="test",
            symbol="BTCUSD",
            timeframe="1h",
            asset_class="CRYPTO",
            lifecycle_state="APPROVED",
        )

        with pytest.raises(Exception):
            response.symbol = "ETHUSD"

    def test_model_list_response_immutable(self):
        """Test ModelListResponse is immutable."""
        from ml_service.research.registry_api.schemas import (
            ModelListResponse,
            ModelSummaryResponse,
        )

        response = ModelListResponse(
            query_type="LIST_MODELS",
            result_count=1,
            models=(
                ModelSummaryResponse(
                    model_id="test",
                    symbol="BTCUSD",
                    timeframe="1h",
                    asset_class="CRYPTO",
                    lifecycle_state="APPROVED",
                ),
            ),
        )

        with pytest.raises(Exception):
            response.result_count = 99

    def test_registry_summary_response_structure(self):
        """Test RegistrySummaryResponse has correct structure."""
        response = RegistrySummaryResponse(
            total_models=10,
            by_asset_class={"CRYPTO": 10},
            by_lifecycle_state={"PRODUCTION": 5, "APPROVED": 5},
            production_count=5,
            approved_count=5,
        )

        assert response.total_models == 10
        assert "CRYPTO" in response.by_asset_class
        assert response.production_count == 5


class TestRegistryAPIRouter:
    """Test FastAPI router integration."""

    @pytest.fixture
    def mock_service(self):
        """Mock RegistryAPIService."""
        return Mock(spec=RegistryAPIService)

    def test_list_models_endpoint(self, mock_service):
        """Test GET /registry/models endpoint."""
        from ml_service.research.registry_api.router import list_models

        mock_service.list_models.return_value = ModelListResponse(
            query_type="LIST_MODELS",
            result_count=0,
            models=(),
        )

        import asyncio
        response = asyncio.run(list_models(service=mock_service))

        assert isinstance(response, ModelListResponse)
        mock_service.list_models.assert_called_once()

    def test_get_model_detail_endpoint_not_found(self, mock_service):
        """Test GET /registry/models/{artifact_id} endpoint when not found."""
        from ml_service.research.registry_api.router import get_model_detail
        from fastapi import HTTPException

        mock_service.get_model_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            asyncio.run(get_model_detail("nonexistent", service=mock_service))

        assert exc_info.value.status_code == 404

    def test_get_registry_summary_endpoint(self, mock_service):
        """Test GET /registry/summary endpoint."""
        from ml_service.research.registry_api.router import get_registry_summary

        mock_service.get_registry_summary.return_value = RegistrySummaryResponse(
            total_models=5,
            by_asset_class={"CRYPTO": 5},
            by_lifecycle_state={"PRODUCTION": 5},
            production_count=5,
            approved_count=0,
        )

        import asyncio
        response = asyncio.run(get_registry_summary(service=mock_service))

        assert isinstance(response, RegistrySummaryResponse)
        assert response.total_models == 5

    def test_get_model_history_endpoint_not_found(self, mock_service):
        """Test GET /registry/history/{artifact_id} endpoint when not found."""
        from ml_service.research.registry_api.router import get_model_history
        from fastapi import HTTPException

        mock_service.get_model_history.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            asyncio.run(get_model_history("nonexistent", service=mock_service))

        assert exc_info.value.status_code == 404


class TestRegistryAPIDeterminism:
    """Test deterministic behavior of API responses."""

    def test_model_list_ordering(self):
        """Test that model list maintains deterministic ordering."""
        from ml_service.research.registry_api.schemas import (
            ModelListResponse,
            ModelSummaryResponse,
        )

        models = (
            ModelSummaryResponse(
                model_id="m1",
                symbol="BTCUSD",
                timeframe="1h",
                asset_class="CRYPTO",
                lifecycle_state="APPROVED",
            ),
            ModelSummaryResponse(
                model_id="m2",
                symbol="BTCUSD",
                timeframe="4h",
                asset_class="CRYPTO",
                lifecycle_state="APPROVED",
            ),
        )

        response1 = ModelListResponse(
            query_type="LIST_MODELS",
            result_count=2,
            models=models,
        )

        response2 = ModelListResponse(
            query_type="LIST_MODELS",
            result_count=2,
            models=models,
        )

        assert response1.models == response2.models

    def test_response_immutability_prevents_mutation(self):
        """Test that frozen schemas prevent accidental mutation."""
        from ml_service.research.registry_api.schemas import ModelSummaryResponse

        model = ModelSummaryResponse(
            model_id="test",
            symbol="BTCUSD",
            timeframe="1h",
            asset_class="CRYPTO",
            lifecycle_state="APPROVED",
        )

        with pytest.raises(Exception):
            model.lifecycle_state = "PRODUCTION"


class TestRegistryAPIRegistration:
    """Test that registry API router is registered in the FastAPI app."""

    def test_routes_registered(self):
        """Verify all expected registry routes are registered in the main FastAPI application."""
        from ml_service.api.main import app

        # Extract all registered route paths
        route_paths = {route.path for route in app.routes}

        expected_paths = {
            "/api/v1/registry/models",
            "/api/v1/registry/models/{artifact_id:path}",
            "/api/v1/registry/summary",
            "/api/v1/registry/production-candidates",
            "/api/v1/registry/history/{artifact_id:path}",
        }

        for path in expected_paths:
            assert path in route_paths, f"Path {path} not registered in FastAPI app"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

