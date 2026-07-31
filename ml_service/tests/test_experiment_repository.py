import pytest
from dataclasses import FrozenInstanceError

from ml_service.research.models import ResearchExperiment, ResearchRun
from ml_service.research.experiment_repository import ExperimentRepository


def test_save_and_get():
    repo = ExperimentRepository()
    experiment = ResearchExperiment(
        experiment_id="EXP_1.0.0",
        session_id="SESS_1.0.0",
        status="RUNNING",
        hypothesis_config=(("learning_rate", 0.01),),
        runs=(),
        created_at="2026-07-31T20:00:00Z",
    )
    
    saved = repo.save(experiment)
    assert saved == experiment
    
    retrieved = repo.get("EXP_1.0.0")
    assert retrieved == experiment
    assert retrieved is not experiment  # deepcopy preservation


def test_duplicate_rejection():
    repo = ExperimentRepository()
    experiment1 = ResearchExperiment(
        experiment_id="EXP_1.0.0",
        session_id="SESS_1.0.0",
        status="RUNNING",
        hypothesis_config=(("learning_rate", 0.01),),
        runs=(),
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save(experiment1)
    
    experiment2 = ResearchExperiment(
        experiment_id="EXP_1.0.0",
        session_id="SESS_1.0.0",
        status="COMPLETED",
        hypothesis_config=(("learning_rate", 0.02),),
        runs=(),
        created_at="2026-07-31T20:01:00Z",
    )
    
    with pytest.raises(ValueError):
        repo.save(experiment2)


def test_exists():
    repo = ExperimentRepository()
    experiment = ResearchExperiment(
        experiment_id="EXP_1.0.0",
        session_id="SESS_1.0.0",
        status="RUNNING",
        hypothesis_config=(),
        runs=(),
        created_at="2026-07-31T20:00:00Z",
    )
    
    assert not repo.exists("EXP_1.0.0")
    repo.save(experiment)
    assert repo.exists("EXP_1.0.0")


def test_delete():
    repo = ExperimentRepository()
    experiment = ResearchExperiment(
        experiment_id="EXP_1.0.0",
        session_id="SESS_1.0.0",
        status="RUNNING",
        hypothesis_config=(),
        runs=(),
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save(experiment)
    assert repo.exists("EXP_1.0.0")
    
    repo.delete("EXP_1.0.0")
    assert not repo.exists("EXP_1.0.0")
    
    with pytest.raises(KeyError):
        repo.get("EXP_1.0.0")


def test_list_ordering():
    repo = ExperimentRepository()
    
    exp_b = ResearchExperiment(
        experiment_id="EXP_2.0.0",
        session_id="SESS_1.0.0",
        status="RUNNING",
        hypothesis_config=(),
        runs=(),
        created_at="2026-07-31T20:01:00Z",
    )
    exp_c = ResearchExperiment(
        experiment_id="EXP_3.0.0",
        session_id="SESS_1.0.0",
        status="RUNNING",
        hypothesis_config=(),
        runs=(),
        created_at="2026-07-31T20:02:00Z",
    )
    exp_a = ResearchExperiment(
        experiment_id="EXP_1.0.0",
        session_id="SESS_1.0.0",
        status="RUNNING",
        hypothesis_config=(),
        runs=(),
        created_at="2026-07-31T20:00:00Z",
    )
    
    repo.save(exp_b)
    repo.save(exp_c)
    repo.save(exp_a)
    
    experiments = repo.list()
    assert [e.experiment_id for e in experiments] == ["EXP_1.0.0", "EXP_2.0.0", "EXP_3.0.0"]


def test_list_by_session():
    repo = ExperimentRepository()
    
    exp_1 = ResearchExperiment(
        experiment_id="EXP_1.0.0",
        session_id="SESS_A",
        status="RUNNING",
        hypothesis_config=(),
        runs=(),
        created_at="2026-07-31T20:00:00Z",
    )
    exp_2 = ResearchExperiment(
        experiment_id="EXP_2.0.0",
        session_id="SESS_B",
        status="RUNNING",
        hypothesis_config=(),
        runs=(),
        created_at="2026-07-31T20:01:00Z",
    )
    exp_3 = ResearchExperiment(
        experiment_id="EXP_3.0.0",
        session_id="SESS_A",
        status="RUNNING",
        hypothesis_config=(),
        runs=(),
        created_at="2026-07-31T20:02:00Z",
    )
    
    repo.save(exp_1)
    repo.save(exp_2)
    repo.save(exp_3)
    
    sess_a_exps = repo.list_by_session("SESS_A")
    assert [e.experiment_id for e in sess_a_exps] == ["EXP_1.0.0", "EXP_3.0.0"]
    
    sess_b_exps = repo.list_by_session("SESS_B")
    assert [e.experiment_id for e in sess_b_exps] == ["EXP_2.0.0"]


def test_immutable_preservation():
    repo = ExperimentRepository()
    experiment = ResearchExperiment(
        experiment_id="EXP_1.0.0",
        session_id="SESS_1.0.0",
        status="RUNNING",
        hypothesis_config=(),
        runs=(),
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save(experiment)
    retrieved = repo.get("EXP_1.0.0")
    
    with pytest.raises(FrozenInstanceError):
        retrieved.status = "COMPLETED"  # type: ignore


def test_invalid_lookup():
    repo = ExperimentRepository()
    
    with pytest.raises(KeyError):
        repo.get("non_existent_exp")
        
    with pytest.raises(KeyError):
        repo.delete("non_existent_exp")
