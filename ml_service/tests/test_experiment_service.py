import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.models import ResearchExperiment, ResearchRun
from ml_service.research.research_experiment import ResearchExperimentManager
from ml_service.research.experiment_repository import ExperimentRepository
from ml_service.research.experiment_service import ExperimentService

@pytest.fixture
def service():
    repository = ExperimentRepository()
    manager = ResearchExperimentManager()
    return ExperimentService(repository, manager)

def test_experiment_creation(service):
    session_id = "sess_123"
    config = {"lr": 0.01, "batch_size": 32}
    exp = service.create_experiment(session_id=session_id, hypothesis_config=config, experiment_id="exp_1")
    
    assert exp.experiment_id == "exp_1"
    assert exp.session_id == session_id
    assert exp.status == "INITIALIZED"
    assert exp.runs == ()
    assert exp.created_at != ""
    
    # Retrieve and verify
    retrieved = service.get_experiment("exp_1")
    assert retrieved == exp
    assert service.has_experiment("exp_1") is True

def test_duplicate_rejection(service):
    session_id = "sess_123"
    config = {"lr": 0.01}
    service.create_experiment(session_id=session_id, hypothesis_config=config, experiment_id="exp_1")
    
    with pytest.raises(ValueError):
        service.create_experiment(session_id=session_id, hypothesis_config=config, experiment_id="exp_1")

def test_retrieval_and_invalid_lookup(service):
    with pytest.raises(KeyError):
        service.get_experiment("exp_nonexistent")
        
    assert service.has_experiment("exp_nonexistent") is False

def test_deletion(service):
    exp = service.create_experiment("sess_123", {"lr": 0.01}, "exp_1")
    service.delete_experiment("exp_1")
    
    assert service.has_experiment("exp_1") is False
    with pytest.raises(KeyError):
        service.get_experiment("exp_1")

def test_deterministic_ordering(service):
    service.create_experiment("sess_1", {"lr": 0.01}, "exp_a")
    service.create_experiment("sess_1", {"lr": 0.01}, "exp_c")
    service.create_experiment("sess_1", {"lr": 0.01}, "exp_b")
    
    exps = service.list_experiments()
    assert len(exps) == 3
    assert [e.experiment_id for e in exps] == ["exp_a", "exp_b", "exp_c"]

def test_filtering_by_session_id(service):
    service.create_experiment("sess_1", {"lr": 0.01}, "exp_a")
    service.create_experiment("sess_2", {"lr": 0.01}, "exp_b")
    service.create_experiment("sess_1", {"lr": 0.01}, "exp_c")
    
    exps_sess_1 = service.list_experiments_by_session("sess_1")
    assert len(exps_sess_1) == 2
    assert [e.experiment_id for e in exps_sess_1] == ["exp_a", "exp_c"]
    
    exps_sess_2 = service.list_experiments_by_session("sess_2")
    assert len(exps_sess_2) == 1
    assert exps_sess_2[0].experiment_id == "exp_b"

def test_immutability_preservation(service):
    exp = service.create_experiment("sess_123", {"lr": 0.01}, "exp_1")
    with pytest.raises(FrozenInstanceError):
        exp.status = "ACTIVE"  # type: ignore

def test_lifecycle_transitions(service):
    exp = service.create_experiment("sess_123", {"lr": 0.01}, "exp_1")
    
    # Transition to ACTIVE
    exp = service.start_experiment("exp_1")
    assert exp.status == "ACTIVE"
    assert service.get_experiment("exp_1").status == "ACTIVE"
    
    # Transition to EVALUATED (completed)
    run = ResearchRun(run_id="run_1", experiment_id="exp_1", status="COMPLETED")
    exp = service.complete_experiment("exp_1", runs=(run,))
    assert exp.status == "EVALUATED"
    assert len(exp.runs) == 1
    assert service.get_experiment("exp_1").status == "EVALUATED"
    
    # Invalid transition check
    with pytest.raises(ValueError):
        service.start_experiment("exp_1")
