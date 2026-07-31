import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.models import ResearchSession, ResearchExperiment, DatasetSnapshot, FeatureSnapshot, ResearchRun
from ml_service.research.research_session import ResearchSessionManager
from ml_service.research.research_repository import ResearchRepository
from ml_service.research.research_service import ResearchService

from ml_service.research.dataset_snapshot import DatasetSnapshotManager
from ml_service.research.dataset_repository import DatasetRepository
from ml_service.research.dataset_service import DatasetService

from ml_service.research.feature_snapshot import FeatureSnapshotManager
from ml_service.research.feature_repository import FeatureRepository
from ml_service.research.feature_service import FeatureService

from ml_service.research.research_experiment import ResearchExperimentManager
from ml_service.research.experiment_repository import ExperimentRepository
from ml_service.research.experiment_service import ExperimentService

from ml_service.research.research_orchestrator import ResearchOrchestrator

@pytest.fixture
def orchestrator():
    # Instantiate repositories
    research_repo = ResearchRepository()
    dataset_repo = DatasetRepository()
    feature_repo = FeatureRepository()
    experiment_repo = ExperimentRepository()
    
    # Instantiate managers
    research_mgr = ResearchSessionManager()
    dataset_mgr = DatasetSnapshotManager()
    feature_mgr = FeatureSnapshotManager()
    experiment_mgr = ResearchExperimentManager()
    
    # Instantiate services
    research_svc = ResearchService(research_repo, research_mgr)
    dataset_svc = DatasetService(dataset_repo, dataset_mgr)
    feature_svc = FeatureService(feature_repo, feature_mgr)
    experiment_svc = ExperimentService(experiment_repo, experiment_mgr)
    
    # Instantiate orchestrator (Dependency Injection)
    return ResearchOrchestrator(
        research_service=research_svc,
        dataset_service=dataset_svc,
        feature_service=feature_svc,
        experiment_service=experiment_svc
    )

def test_complete_orchestration_workflow(orchestrator):
    session_config = {"session_id": "SESS_001", "symbol": "BTCUSDT"}
    snapshot_id = "snap_123"
    dataset_version_id = "DS_1.0.0"
    dataset_fingerprint = "a" * 64
    dataset_file_path = "/storage/datasets/DS_1.0.0.parquet"
    feature_dataset_id = "FDS_1.0.0"
    feature_fingerprint = "b" * 64
    feature_file_path = "/storage/features/FDS_1.0.0.parquet"
    experiment_id = "exp_1"
    hypothesis_config = {"lr": 0.05}
    runs = (ResearchRun(run_id="run_1", experiment_id=experiment_id, status="COMPLETED"),)
    best_run_id = "run_1"

    session = orchestrator.execute_workflow(
        session_config=session_config,
        snapshot_id=snapshot_id,
        dataset_version_id=dataset_version_id,
        dataset_fingerprint=dataset_fingerprint,
        dataset_file_path=dataset_file_path,
        feature_dataset_id=feature_dataset_id,
        feature_fingerprint=feature_fingerprint,
        feature_file_path=feature_file_path,
        experiment_id=experiment_id,
        hypothesis_config=hypothesis_config,
        runs=runs,
        best_run_id=best_run_id
    )

    # Assert session final status and fields
    assert session.session_id == "SESS_001"
    assert session.status == "COMPLETED"
    assert session.snapshot_id == "snap_123"
    assert session.best_run_id == "run_1"
    assert len(session.experiments) == 1
    
    # Assert underlying storage state
    assert orchestrator.research_service.has_session("SESS_001") is True
    assert orchestrator.dataset_service.has_snapshot(dataset_version_id) is True
    assert orchestrator.feature_service.has_snapshot(feature_dataset_id) is True
    assert orchestrator.experiment_service.has_experiment(experiment_id) is True

def test_fail_fast_error_propagation(orchestrator):
    # Invalid dataset snapshot details (e.g. invalid version format) should trigger fail-fast validation error
    session_config = {"session_id": "SESS_ERR", "symbol": "BTCUSDT"}
    
    with pytest.raises(ValueError):
        orchestrator.execute_workflow(
            session_config=session_config,
            snapshot_id="snap_123",
            dataset_version_id="INVALID_FORMAT",  # Should fail step 2
            dataset_fingerprint="a" * 64,
            dataset_file_path="/storage/datasets/DS_1.0.0.parquet",
            feature_dataset_id="FDS_1.0.0",
            feature_fingerprint="b" * 64,
            feature_file_path="/storage/features/FDS_1.0.0.parquet",
            experiment_id="exp_1",
            hypothesis_config={"lr": 0.05}
        )
    
    # Verify that the session stayed in CREATED state since it failed before starting (Step 5)
    assert orchestrator.research_service.has_session("SESS_ERR") is True
    assert orchestrator.research_service.get_session("SESS_ERR").status == "CREATED"

def test_fail_fast_in_running_state(orchestrator):
    # Test error inside the running phase (e.g. invalid completion of experiment)
    session_config = {"session_id": "SESS_FAIL", "symbol": "BTCUSDT"}
    
    # We pass runs that don't match the active experiment's status or fail completion
    # Actually, experiment completing can be failed by throwing a ValueError.
    # Let's mock experiment_service.complete_experiment to raise ValueError
    import unittest.mock as mock
    with mock.patch.object(orchestrator.experiment_service, 'complete_experiment', side_effect=ValueError("Simulation")):
        with pytest.raises(ValueError):
            orchestrator.execute_workflow(
                session_config=session_config,
                snapshot_id="snap_123",
                dataset_version_id="DS_1.0.0",
                dataset_fingerprint="a" * 64,
                dataset_file_path="/storage/datasets/DS_1.0.0.parquet",
                feature_dataset_id="FDS_1.0.0",
                feature_fingerprint="b" * 64,
                feature_file_path="/storage/features/FDS_1.0.0.parquet",
                experiment_id="exp_1",
                hypothesis_config={"lr": 0.05}
            )
            
    # Session must be transitioned to FAILED
    assert orchestrator.research_service.get_session("SESS_FAIL").status == "FAILED"

def test_immutable_preservation(orchestrator):
    session_config = {"session_id": "SESS_IMMUT", "symbol": "BTCUSDT"}
    session = orchestrator.research_service.create_session(config=session_config, session_id="SESS_IMMUT")
    
    with pytest.raises(FrozenInstanceError):
        session.status = "RUNNING"  # type: ignore
