import sys
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

def test_legacy_orchestrator_not_imported_by_main():
    """Verify that importing ml_service.api.main does not load the legacy orchestrator api."""
    # Clear main and legacy orchestrator modules from cache if present
    for mod in list(sys.modules.keys()):
        if mod.startswith("ml_service.api.main") or mod.startswith("ml_service.research.research_orchestrator"):
            sys.modules.pop(mod, None)

    # Import main
    from ml_service.api.main import app

    # Assert that the legacy orchestrator API module was NOT loaded during import
    assert "ml_service.research.research_orchestrator.api" not in sys.modules
    assert "ml_service.research.research_orchestrator.service" not in sys.modules


def test_canonical_orchestrator_endpoint():
    """Verify that /api/research/orchestrator/run is available and invokes the canonical orchestrator."""
    from ml_service.api.main import app
    client = TestClient(app)

    # Mock execute_session on the canonical ResearchSessionOrchestrator
    with patch("ml_service.research.orchestrator_api.ResearchSessionOrchestrator.execute_session") as mock_execute:
        from ml_service.research.models import ResearchSession
        from ml_service.research.orchestrator import ResearchSessionStatus

        mock_session = ResearchSession(
            session_id="test-api-session",
            status=ResearchSessionStatus.COMPLETED,
            dataset_version_id="v1",
            config_snapshot=(("model_version_id", "m1"),),
            model_fingerprint="fingerprint-api-test",
            completed_at="2026-08-20T00:00:00Z"
        )
        mock_execute.return_value = mock_session

        payload = {
            "session_id": "test-api-session",
            "dataset_version_id": "v1",
            "model_version_id": "m1"
        }
        response = client.post("/api/research/orchestrator/run", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-api-session"
        assert data["status"] == "COMPLETED"
        assert data["model_fingerprint"] == "fingerprint-api-test"

        # Verify the canonical orchestrator execute_session method was called
        mock_execute.assert_called_once()
