import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.models import ResearchRun
from ml_service.research.research_run import ResearchRunManager
from ml_service.research.research_run_repository import ResearchRunRepository
from ml_service.research.research_run_service import ResearchRunService

@pytest.fixture
def run_service():
    repo = ResearchRunRepository()
    manager = ResearchRunManager()
    return ResearchRunService(repo, manager)

def test_create_run(run_service):
    run = run_service.create_run(
        experiment_id="exp_1",
        hyperparameters={"lr": 0.01},
        run_id="run_1",
        session_id="session_1"
    )
    assert run.run_id == "run_1"
    assert run.experiment_id == "exp_1"
    assert run.session_id == "session_1"
    assert run.status == "CREATED"
    assert run_service.exists("run_1") is True

def test_duplicate_rejection(run_service):
    run_service.create_run(experiment_id="exp_1", run_id="run_1")
    with pytest.raises(ValueError):
        run_service.create_run(experiment_id="exp_2", run_id="run_1")

def test_retrieved_run(run_service):
    run_service.create_run(experiment_id="exp_1", run_id="run_1")
    retrieved = run_service.get_run("run_1")
    assert retrieved.run_id == "run_1"

def test_deletion(run_service):
    run_service.create_run(experiment_id="exp_1", run_id="run_1")
    assert run_service.exists("run_1") is True
    run_service.delete_run("run_1")
    assert run_service.exists("run_1") is False

def test_exists(run_service):
    assert run_service.exists("run_1") is False
    run_service.create_run(experiment_id="exp_1", run_id="run_1")
    assert run_service.exists("run_1") is True

def test_list_ordering(run_service):
    run_service.create_run(experiment_id="exp_1", run_id="run_B")
    run_service.create_run(experiment_id="exp_1", run_id="run_A")
    
    runs = run_service.list_runs()
    assert [r.run_id for r in runs] == ["run_A", "run_B"]

def test_filter_by_experiment(run_service):
    run_service.create_run(experiment_id="exp_1", run_id="run_A")
    run_service.create_run(experiment_id="exp_2", run_id="run_B")
    run_service.create_run(experiment_id="exp_1", run_id="run_C")
    
    exp1_runs = run_service.list_by_experiment("exp_1")
    assert [r.run_id for r in exp1_runs] == ["run_A", "run_C"]

def test_filter_by_session(run_service):
    run_service.create_run(experiment_id="exp_1", session_id="sess_1", run_id="run_A")
    run_service.create_run(experiment_id="exp_2", session_id="sess_2", run_id="run_B")
    run_service.create_run(experiment_id="exp_3", session_id="sess_1", run_id="run_C")
    
    sess1_runs = run_service.list_by_session("sess_1")
    assert [r.run_id for r in sess1_runs] == ["run_A", "run_C"]

def test_lifecycle_transitions(run_service):
    run_service.create_run(experiment_id="exp_1", run_id="run_1")
    
    # CREATED -> RUNNING
    run = run_service.start_run("run_1")
    assert run.status == "RUNNING"
    
    # RUNNING -> COMPLETED
    run = run_service.complete_run("run_1", metrics={"sharpe": 2.1}, model_binary_path="/model.bin")
    assert run.status == "COMPLETED"
    assert dict(run.metrics) == {"sharpe": 2.1}
    assert run.model_binary_path == "/model.bin"

def test_lifecycle_rejections(run_service):
    run_service.create_run(experiment_id="exp_1", run_id="run_1")
    
    # Cannot complete before starting
    with pytest.raises(ValueError):
        run_service.complete_run("run_1")
        
    run_service.start_run("run_1")
    run_service.fail_run("run_1")
    
    # Cannot start or complete a failed run
    with pytest.raises(ValueError):
        run_service.start_run("run_1")
    with pytest.raises(ValueError):
        run_service.complete_run("run_1")

def test_immutability(run_service):
    run = run_service.create_run(experiment_id="exp_1", run_id="run_1")
    with pytest.raises(FrozenInstanceError):
        run.status = "RUNNING"  # type: ignore

def test_invalid_lookup(run_service):
    with pytest.raises(KeyError):
        run_service.get_run("non_existent")
        
    with pytest.raises(KeyError):
        run_service.delete_run("non_existent")
