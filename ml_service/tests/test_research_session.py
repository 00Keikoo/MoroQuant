import pytest
from dataclasses import FrozenInstanceError
import json
from ml_service.research.models import ResearchSession, ResearchExperiment, ResearchRun
from ml_service.research.research_session import ResearchSessionManager, make_immutable

def test_session_creation():
    manager = ResearchSessionManager()
    config = {
        "symbol": "BTCUSDT",
        "time_bounds": ["2026-07-01T00:00:00Z", "2026-07-31T00:00:00Z"],
        "parameters": {
            "learning_rate": 0.001,
            "epochs": 10
        }
    }
    
    session = manager.create_session(config=config, snapshot_id="snap_123")
    
    assert session.session_id is not None
    assert session.status == "CREATED"
    assert session.snapshot_id == "snap_123"
    assert session.dataset_version_id is None
    assert session.feature_dataset_id is None
    assert session.best_run_id is None
    assert session.experiments == ()
    assert session.created_at != ""
    assert session.completed_at is None
    
    # Retrieve and verify
    retrieved = manager.get_session(session.session_id)
    assert retrieved == session

def test_valid_lifecycle_transitions():
    manager = ResearchSessionManager()
    session = manager.create_session(config={"symbol": "BTCUSDT"})
    session_id = session.session_id
    
    # CREATED -> RUNNING
    session = manager.start_session(session_id)
    assert session.status == "RUNNING"
    
    # RUNNING -> COMPLETED
    run = ResearchRun(run_id="run_1", experiment_id="exp_1", status="COMPLETED")
    exp = ResearchExperiment(experiment_id="exp_1", session_id=session_id, status="EVALUATED", runs=(run,))
    
    session = manager.complete_session(
        session_id,
        best_run_id="run_1",
        experiments=(exp,),
        completed_at="2026-07-31T14:00:00Z"
    )
    assert session.status == "COMPLETED"
    assert session.best_run_id == "run_1"
    assert len(session.experiments) == 1
    assert session.experiments[0].experiment_id == "exp_1"
    assert session.completed_at == "2026-07-31T14:00:00Z"

def test_invalid_lifecycle_transitions():
    manager = ResearchSessionManager()
    session = manager.create_session(config={"symbol": "BTCUSDT"})
    session_id = session.session_id
    
    # Cannot complete before starting
    with pytest.raises(ValueError):
        manager.complete_session(session_id)
        
    # Cannot fail before starting
    with pytest.raises(ValueError):
        manager.fail_session(session_id)
        
    # CREATED -> RUNNING
    manager.start_session(session_id)
    
    # Cannot start again
    with pytest.raises(ValueError):
        manager.start_session(session_id)
        
    # Cancel the session (RUNNING -> CANCELLED)
    manager.cancel_session(session_id)
    
    # Cannot start or complete a CANCELLED session
    with pytest.raises(ValueError):
        manager.start_session(session_id)
    with pytest.raises(ValueError):
        manager.complete_session(session_id)

def test_session_cancellation_pre_run():
    manager = ResearchSessionManager()
    session = manager.create_session(config={"symbol": "BTCUSDT"})
    session_id = session.session_id
    
    # CREATED -> CANCELLED
    session = manager.cancel_session(session_id)
    assert session.status == "CANCELLED"
    assert session.completed_at is not None

def test_deterministic_behavior():
    manager = ResearchSessionManager()
    config1 = {
        "symbol": "BTCUSDT",
        "epochs": 100,
        "learning_rate": 0.05
    }
    config2 = {
        "learning_rate": 0.05,
        "symbol": "BTCUSDT",
        "epochs": 100
    }
    
    session1 = manager.create_session(config=config1)
    session2 = manager.create_session(config=config2)
    
    # Config snapshot should be sorted alphabetically by key and be identical
    assert session1.config_snapshot == session2.config_snapshot
    assert session1.serialize() != session2.serialize()  # distinct session_ids and created_ats
    
    # With same fields, serialization must be deterministic
    session3 = ResearchSession(
        session_id="SESS_SAME",
        status="CREATED",
        config_snapshot=session1.config_snapshot,
        created_at="2026-07-31T00:00:00Z"
    )
    session4 = ResearchSession(
        session_id="SESS_SAME",
        status="CREATED",
        config_snapshot=session2.config_snapshot,
        created_at="2026-07-31T00:00:00Z"
    )
    assert session3.serialize() == session4.serialize()

def test_immutability_preservation():
    manager = ResearchSessionManager()
    session = manager.create_session(config={"symbol": "BTCUSDT"})
    
    with pytest.raises(FrozenInstanceError):
        session.status = "RUNNING"  # type: ignore

def test_metadata_propagation():
    manager = ResearchSessionManager()
    session = manager.create_session(config={"symbol": "BTCUSDT"}, snapshot_id="snapshot_abc")
    assert session.snapshot_id == "snapshot_abc"
    
    session = manager.start_session(session.session_id)
    assert session.snapshot_id == "snapshot_abc"  # persists through transition
    
    session = manager.complete_session(
        session.session_id,
        best_run_id="best_1",
        experiments=(),
        completed_at="2026-07-31T15:00:00Z"
    )
    assert session.snapshot_id == "snapshot_abc"
    assert session.best_run_id == "best_1"

def test_empty_default_values():
    manager = ResearchSessionManager()
    session = manager.create_session(config={})
    assert session.config_snapshot == ()
    assert session.snapshot_id is None
    assert session.experiments == ()
