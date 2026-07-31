import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.models import ResearchRun
from ml_service.research.research_run_repository import ResearchRunRepository

def test_save():
    repo = ResearchRunRepository()
    run = ResearchRun(
        run_id="run_1",
        experiment_id="exp_1",
        status="CREATED",
        session_id="session_1",
        hyperparameters=(("lr", 0.01),)
    )
    
    saved = repo.save(run)
    assert saved == run
    
    retrieved = repo.get("run_1")
    assert retrieved == run
    assert retrieved is not run  # should be deep copied

def test_get():
    repo = ResearchRunRepository()
    run = ResearchRun(run_id="run_1", experiment_id="exp_1", status="CREATED")
    repo.save(run)
    
    retrieved = repo.get("run_1")
    assert retrieved.run_id == "run_1"

def test_duplicate_rejection():
    repo = ResearchRunRepository()
    run1 = ResearchRun(run_id="run_1", experiment_id="exp_1", status="CREATED")
    repo.save(run1)
    
    run2 = ResearchRun(run_id="run_1", experiment_id="exp_2", status="RUNNING")
    with pytest.raises(ValueError):
        repo.save(run2)

def test_exists():
    repo = ResearchRunRepository()
    assert repo.exists("run_1") is False
    
    run = ResearchRun(run_id="run_1", experiment_id="exp_1", status="CREATED")
    repo.save(run)
    assert repo.exists("run_1") is True

def test_delete():
    repo = ResearchRunRepository()
    run = ResearchRun(run_id="run_1", experiment_id="exp_1", status="CREATED")
    repo.save(run)
    
    assert repo.exists("run_1") is True
    repo.delete("run_1")
    assert repo.exists("run_1") is False
    
    with pytest.raises(KeyError):
        repo.get("run_1")

def test_deterministic_ordering():
    repo = ResearchRunRepository()
    run_b = ResearchRun(run_id="run_B", experiment_id="exp_1", status="CREATED")
    run_c = ResearchRun(run_id="run_C", experiment_id="exp_1", status="CREATED")
    run_a = ResearchRun(run_id="run_A", experiment_id="exp_1", status="CREATED")
    
    repo.save(run_b)
    repo.save(run_c)
    repo.save(run_a)
    
    runs = repo.list()
    assert [r.run_id for r in runs] == ["run_A", "run_B", "run_C"]

def test_filter_by_experiment():
    repo = ResearchRunRepository()
    run_a = ResearchRun(run_id="run_A", experiment_id="exp_1", status="CREATED")
    run_b = ResearchRun(run_id="run_B", experiment_id="exp_2", status="CREATED")
    run_c = ResearchRun(run_id="run_C", experiment_id="exp_1", status="CREATED")
    
    repo.save(run_a)
    repo.save(run_b)
    repo.save(run_c)
    
    exp1_runs = repo.list_by_experiment("exp_1")
    assert [r.run_id for r in exp1_runs] == ["run_A", "run_C"]
    
    exp2_runs = repo.list_by_experiment("exp_2")
    assert [r.run_id for r in exp2_runs] == ["run_B"]

def test_filter_by_session():
    repo = ResearchRunRepository()
    run_a = ResearchRun(run_id="run_A", experiment_id="exp_1", session_id="session_1", status="CREATED")
    run_b = ResearchRun(run_id="run_B", experiment_id="exp_2", session_id="session_2", status="CREATED")
    run_c = ResearchRun(run_id="run_C", experiment_id="exp_3", session_id="session_1", status="CREATED")
    
    repo.save(run_a)
    repo.save(run_b)
    repo.save(run_c)
    
    sess1_runs = repo.list_by_session("session_1")
    assert [r.run_id for r in sess1_runs] == ["run_A", "run_C"]
    
    sess2_runs = repo.list_by_session("session_2")
    assert [r.run_id for r in sess2_runs] == ["run_B"]

def test_immutable_preservation():
    repo = ResearchRunRepository()
    run = ResearchRun(run_id="run_1", experiment_id="exp_1", status="CREATED")
    repo.save(run)
    
    retrieved = repo.get("run_1")
    with pytest.raises(FrozenInstanceError):
        retrieved.status = "RUNNING"  # type: ignore

def test_invalid_lookup():
    repo = ResearchRunRepository()
    
    with pytest.raises(KeyError):
        repo.get("non_existent_run")
        
    with pytest.raises(KeyError):
        repo.delete("non_existent_run")

def test_save_type_error():
    repo = ResearchRunRepository()
    with pytest.raises(TypeError):
        repo.save("not_a_run_object")  # type: ignore
