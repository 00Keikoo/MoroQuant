import pytest
from dataclasses import FrozenInstanceError

from ml_service.research.models import (
    ResearchSession,
    ResearchExperiment,
    ResearchRun,
    DatasetSnapshot,
    FeatureSnapshot,
)
from ml_service.research.research_repository import ResearchRepository


def test_create_session():
    repo = ResearchRepository()
    session = ResearchSession(
        session_id="session_1",
        status="CREATED",
        config_snapshot=(("param1", "value1"),),
        created_at="2026-07-31T20:00:00Z",
    )
    
    saved = repo.create_session(session)
    assert saved == session
    
    retrieved = repo.get_session("session_1")
    assert retrieved == session
    assert retrieved is not session  # should be a deepcopy to ensure decoupling


def test_duplicate_rejection():
    repo = ResearchRepository()
    session1 = ResearchSession(
        session_id="session_1",
        status="CREATED",
        config_snapshot=(),
        created_at="2026-07-31T20:00:00Z",
    )
    repo.create_session(session1)
    
    session2 = ResearchSession(
        session_id="session_1",
        status="RUNNING",
        config_snapshot=(),
        created_at="2026-07-31T20:01:00Z",
    )
    with pytest.raises(ValueError):
        repo.create_session(session2)

    # Test duplicate experiment rejection
    experiment1 = ResearchExperiment(
        experiment_id="exp_1",
        session_id="session_1",
        status="INITIALIZED",
    )
    repo.save_experiment(experiment1)
    
    experiment2 = ResearchExperiment(
        experiment_id="exp_1",
        session_id="session_2",
        status="ACTIVE",
    )
    with pytest.raises(ValueError):
        repo.save_experiment(experiment2)

    # Test duplicate dataset snapshot rejection
    dataset1 = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/datasets/ds_1.0.0.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save_dataset_snapshot(dataset1)
    
    dataset2 = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="b" * 64,
        file_path="/storage/datasets/ds_1.0.0_alt.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    with pytest.raises(ValueError):
        repo.save_dataset_snapshot(dataset2)

    # Test duplicate feature snapshot rejection
    feature1 = FeatureSnapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="c" * 64,
        file_path="/storage/features/fds_1.0.0.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save_feature_snapshot(feature1)
    
    feature2 = FeatureSnapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="d" * 64,
        file_path="/storage/features/fds_1.0.0_alt.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    with pytest.raises(ValueError):
        repo.save_feature_snapshot(feature2)


def test_experiment_save_load():
    repo = ResearchRepository()
    run = ResearchRun(run_id="run_1", experiment_id="exp_1", status="COMPLETED")
    experiment = ResearchExperiment(
        experiment_id="exp_1",
        session_id="session_1",
        status="EVALUATED",
        hypothesis_config=(("param", 1),),
        runs=(run,),
        created_at="2026-07-31T20:00:00Z",
    )
    
    saved = repo.save_experiment(experiment)
    assert saved == experiment
    
    retrieved = repo.get_experiment("exp_1")
    assert retrieved == experiment
    assert retrieved.runs[0].run_id == "run_1"


def test_dataset_snapshot_save_load():
    repo = ResearchRepository()
    snapshot = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/datasets/ds1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    
    saved = repo.save_dataset_snapshot(snapshot)
    assert saved == snapshot
    
    retrieved = repo.get_dataset_snapshot("DS_1.0.0")
    assert retrieved == snapshot


def test_feature_snapshot_save_load():
    repo = ResearchRepository()
    snapshot = FeatureSnapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="b" * 64,
        file_path="/storage/features/feat1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    
    saved = repo.save_feature_snapshot(snapshot)
    assert saved == snapshot
    
    retrieved = repo.get_feature_snapshot("FDS_1.0.0")
    assert retrieved == snapshot


def test_deterministic_ordering():
    repo = ResearchRepository()
    
    # Save sessions out of order
    session_b = ResearchSession(session_id="session_B", status="CREATED")
    session_c = ResearchSession(session_id="session_C", status="CREATED")
    session_a = ResearchSession(session_id="session_A", status="CREATED")
    
    repo.create_session(session_b)
    repo.create_session(session_c)
    repo.create_session(session_a)
    
    sessions = repo.list_sessions()
    assert [s.session_id for s in sessions] == ["session_A", "session_B", "session_C"]
    
    # Save experiments for same session out of order
    exp_c = ResearchExperiment(experiment_id="exp_C", session_id="session_A", status="INITIALIZED")
    exp_a = ResearchExperiment(experiment_id="exp_A", session_id="session_A", status="INITIALIZED")
    exp_b = ResearchExperiment(experiment_id="exp_B", session_id="session_A", status="INITIALIZED")
    exp_other = ResearchExperiment(experiment_id="exp_D", session_id="session_B", status="INITIALIZED")
    
    repo.save_experiment(exp_c)
    repo.save_experiment(exp_a)
    repo.save_experiment(exp_b)
    repo.save_experiment(exp_other)
    
    experiments = repo.list_experiments("session_A")
    assert [e.experiment_id for e in experiments] == ["exp_A", "exp_B", "exp_C"]


def test_deletion():
    repo = ResearchRepository()
    session = ResearchSession(session_id="session_1", status="CREATED")
    repo.create_session(session)
    
    experiment = ResearchExperiment(experiment_id="exp_1", session_id="session_1", status="INITIALIZED")
    repo.save_experiment(experiment)
    
    # Verify they exist
    assert repo.get_session("session_1") == session
    assert repo.get_experiment("exp_1") == experiment
    
    # Delete them
    repo.delete_session("session_1")
    repo.delete_experiment("exp_1")
    
    # Verify they are gone
    with pytest.raises(KeyError):
        repo.get_session("session_1")
        
    with pytest.raises(KeyError):
        repo.get_experiment("exp_1")


def test_immutable_preservation():
    repo = ResearchRepository()
    session = ResearchSession(
        session_id="session_1",
        status="CREATED",
        config_snapshot=(("param1", "value1"),),
        created_at="2026-07-31T20:00:00Z",
    )
    repo.create_session(session)
    retrieved = repo.get_session("session_1")
    
    with pytest.raises(FrozenInstanceError):
        retrieved.status = "RUNNING"  # type: ignore


def test_invalid_lookup():
    repo = ResearchRepository()
    
    with pytest.raises(KeyError):
        repo.get_session("non_existent_session")
        
    with pytest.raises(KeyError):
        repo.get_experiment("non_existent_experiment")
        
    with pytest.raises(KeyError):
        repo.get_dataset_snapshot("non_existent_ds")
        
    with pytest.raises(KeyError):
        repo.get_feature_snapshot("non_existent_fds")

    with pytest.raises(KeyError):
        repo.delete_session("non_existent_session")

    with pytest.raises(KeyError):
        repo.delete_experiment("non_existent_experiment")
