"""Canonical Research Orchestrator API Router.

Thin adapter around the canonical ResearchSessionOrchestrator.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ml_service.research.orchestrator import ResearchSessionOrchestrator, ResearchSessionStatus
from ml_service.research.models import ResearchSession

router = APIRouter(prefix="/api/research/orchestrator", tags=["research_orchestrator"])

class RunSessionRequest(BaseModel):
    session_id: str
    dataset_version_id: str
    model_version_id: str
    config_snapshot: Optional[Dict[str, Any]] = None

class SessionResponse(BaseModel):
    session_id: str
    status: str
    dataset_version_id: str
    model_fingerprint: Optional[str] = None
    completed_at: Optional[str] = None

class MockEngine:
    def create_snapshot(self, dataset_version_id):
        class Snap:
            snapshot_id = "snap-api"
            dataset_version_id = dataset_version_id
            file_hash = "hash-api"
        return Snap()

    def replay(self, snapshot_id):
        class Rep:
            replay_id = "replay-api"
            dataset_fingerprint = "fp-api"
            execution_config = {}
            random_seed = 42
        return Rep()

    def run_experiment(self, session):
        class Exp:
            experiment_id = "exp-api"
            replay_fingerprint = "fp-api"
            strategy_config = {}
            model_config = {}
            random_seed = 42
        return Exp()

    def evaluate(self, session):
        class Eval:
            evaluation_id = "eval-api"
            experiment_fingerprint = "fp-api"
            metrics_config = {}
        return Eval()

    def generate_report(self, evaluation_result):
        return "report-api"

    def benchmark(self, report):
        return "bench-api"

    def evaluate_promotion(self, benchmark_result):
        return "proposal-api"

class MockRegistry:
    def __init__(self):
        self.last_proposal = None

    def get_version(self, model_version_id):
        class ModelVersion:
            composite_fingerprint = "fingerprint-api"
        return ModelVersion()

class MockRepository:
    def __init__(self):
        self.sessions = {}

    def save_session(self, session):
        self.sessions[session.session_id] = session

@router.post("/run", response_model=SessionResponse)
def run_session(request: RunSessionRequest):
    """Run a research session using the canonical ResearchSessionOrchestrator."""
    engine = MockEngine()
    registry = MockRegistry()
    repository = MockRepository()

    orchestrator = ResearchSessionOrchestrator(
        snapshot_engine=engine,
        replay_engine=engine,
        experiment_engine=engine,
        evaluation_engine=engine,
        reporting_engine=engine,
        benchmark_engine=engine,
        promotion_engine=engine,
        registry_service=registry,
        repository=repository,
    )

    config_tuple = (("model_version_id", request.model_version_id),)
    if request.config_snapshot:
        config_tuple = tuple((k, v) for k, v in request.config_snapshot.items())

    session = ResearchSession(
        session_id=request.session_id,
        status=ResearchSessionStatus.PENDING,
        dataset_version_id=request.dataset_version_id,
        config_snapshot=config_tuple,
    )

    try:
        final_session = orchestrator.execute_session(session)
        return SessionResponse(
            session_id=final_session.session_id,
            status=final_session.status,
            dataset_version_id=final_session.dataset_version_id,
            model_fingerprint=final_session.model_fingerprint,
            completed_at=final_session.completed_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
