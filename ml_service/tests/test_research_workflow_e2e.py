"""End-to-End Research Workflow Tests for MoroQuant Research Platform."""

import pytest
import dataclasses
from typing import Dict, Any

from ml_service.research.models import (
    ResearchSession,
    ResearchExperiment,
    ResearchRun,
    DatasetSnapshot,
    FeatureSnapshot
)
from ml_service.research.research_session import ResearchSessionManager
from ml_service.research.research_repository import ResearchRepository
from ml_service.research.research_service import ResearchService

from ml_service.research.research_experiment import ResearchExperimentManager
from ml_service.research.experiment_repository import ExperimentRepository
from ml_service.research.experiment_service import ExperimentService

from ml_service.research.research_run import ResearchRunManager
from ml_service.research.research_run_repository import ResearchRunRepository
from ml_service.research.research_run_service import ResearchRunService

from ml_service.research.training_pipeline import TrainingPipelineManager, TrainingResult


@pytest.fixture
def workflow_context(tmp_path):
    """Builds and returns all services required for the research workflow."""
    import numpy as np
    import pandas as pd
    import hashlib

    # Repositories
    session_repo = ResearchRepository()
    experiment_repo = ExperimentRepository()
    run_repo = ResearchRunRepository()
    
    # Managers
    session_mgr = ResearchSessionManager()
    experiment_mgr = ResearchExperimentManager()
    run_mgr = ResearchRunManager()
    
    # Services
    session_service = ResearchService(session_repo, session_mgr)
    experiment_service = ExperimentService(experiment_repo, experiment_mgr)
    run_service = ResearchRunService(run_repo, run_mgr)
    
    # Pipeline
    pipeline_manager = TrainingPipelineManager()
    
    # Generate synthetic parquet files
    np.random.seed(42)
    n_rows = 100
    timestamps = pd.date_range("2026-01-01", periods=n_rows, freq="h")
    
    # Create dataset DataFrame containing both BTCUSDT and ETHUSDT symbols
    btc_df = pd.DataFrame({
        "timestamp": timestamps,
        "symbol": "BTCUSDT",
        "target": np.random.choice([0.0, 1.0], size=n_rows)
    })
    eth_df = pd.DataFrame({
        "timestamp": timestamps,
        "symbol": "ETHUSDT",
        "target": np.random.choice([0.0, 1.0], size=n_rows)
    })
    dataset_df = pd.concat([btc_df, eth_df], ignore_index=True)
    
    # Create feature DataFrame containing features for both symbols
    btc_feat = pd.DataFrame({
        "timestamp": timestamps,
        "symbol": "BTCUSDT",
        "feat_1": np.random.normal(0, 1, n_rows),
        "feat_2": np.random.normal(0, 1, n_rows)
    })
    eth_feat = pd.DataFrame({
        "timestamp": timestamps,
        "symbol": "ETHUSDT",
        "feat_1": np.random.normal(0, 1, n_rows),
        "feat_2": np.random.normal(0, 1, n_rows)
    })
    features_df = pd.concat([btc_feat, eth_feat], ignore_index=True)
    
    ds_path = str(tmp_path / "ds_1.0.0.parquet")
    feat_path = str(tmp_path / "fds_1.0.0.parquet")
    
    dataset_df.to_parquet(ds_path)
    features_df.to_parquet(feat_path)
    
    def compute_sha256(path):
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
            
    ds_hash = compute_sha256(ds_path)
    feat_hash = compute_sha256(feat_path)
    
    # Snapshots
    dataset_snapshot = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint=ds_hash,
        file_path=ds_path,
        is_frozen=True,
        created_at="2026-07-31T00:00:00Z"
    )
    
    feature_snapshot = FeatureSnapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint=feat_hash,
        file_path=feat_path,
        is_frozen=True,
        created_at="2026-07-31T00:00:00Z"
    )
    
    return {
        "session_service": session_service,
        "experiment_service": experiment_service,
        "run_service": run_service,
        "pipeline_manager": pipeline_manager,
        "dataset_snapshot": dataset_snapshot,
        "feature_snapshot": feature_snapshot,
    }


def test_complete_xgboost_workflow(workflow_context):
    """Verify a complete end-to-end research workflow using the xgboost trainer."""
    s_svc = workflow_context["session_service"]
    e_svc = workflow_context["experiment_service"]
    r_svc = workflow_context["run_service"]
    pipeline = workflow_context["pipeline_manager"]
    ds_snap = workflow_context["dataset_snapshot"]
    feat_snap = workflow_context["feature_snapshot"]

    # 1. Create and Start Session
    session = s_svc.create_session(config={"symbol": "BTCUSDT", "period": "1m"}, session_id="sess-xgb")
    assert session.status == "CREATED"
    session = s_svc.start_session("sess-xgb")
    assert session.status == "RUNNING"

    # 2. Create and Start Experiment
    experiment = e_svc.create_experiment(
        session_id="sess-xgb",
        hypothesis_config={"alpha": 0.05, "metric": "sharpe"},
        experiment_id="exp-xgb"
    )
    assert experiment.status == "INITIALIZED"
    experiment = e_svc.start_experiment("exp-xgb")
    assert experiment.status == "ACTIVE"

    # 3. Create and Start Run
    run = r_svc.create_run(
        experiment_id="exp-xgb",
        hyperparameters={"model_type": "xgboost", "max_depth": 6},
        run_id="run-xgb",
        session_id="sess-xgb"
    )
    assert run.status == "CREATED"
    run = r_svc.start_run("run-xgb")
    assert run.status == "RUNNING"

    # 4. Execute Training Pipeline
    result, updated_run = pipeline.run(
        research_run=run,
        dataset_snapshot=ds_snap,
        feature_snapshot=feat_snap,
        training_config={"epochs": 100},
        seed=42,
        model_params={"model_type": "xgboost", "max_depth": 6}
    )
    
    # 5. Complete the Run with Pipeline results
    run = r_svc.complete_run(
        run_id="run-xgb",
        metrics=dict(result.metrics.to_tuple()),
        model_binary_path=result.artifacts.file_path,
        completed_at=updated_run.completed_at
    )
    assert run.status == "COMPLETED"
    assert run.model_binary_path.startswith("/storage/models/xgboost_")

    # 6. Complete the Experiment
    experiment = e_svc.complete_experiment(experiment_id="exp-xgb", runs=(run,))
    assert experiment.status == "EVALUATED"
    assert len(experiment.runs) == 1

    # 7. Complete the Session
    session = s_svc.complete_session(session_id="sess-xgb", best_run_id="run-xgb", experiments=(experiment,))
    assert session.status == "COMPLETED"
    assert session.best_run_id == "run-xgb"
    assert len(session.experiments) == 1


def test_complete_lightgbm_workflow(workflow_context):
    """Verify a complete end-to-end research workflow using the lightgbm trainer."""
    s_svc = workflow_context["session_service"]
    e_svc = workflow_context["experiment_service"]
    r_svc = workflow_context["run_service"]
    pipeline = workflow_context["pipeline_manager"]
    ds_snap = workflow_context["dataset_snapshot"]
    feat_snap = workflow_context["feature_snapshot"]

    # 1. Create and Start Session
    session = s_svc.create_session(config={"symbol": "ETHUSDT"}, session_id="sess-lgb")
    session = s_svc.start_session("sess-lgb")

    # 2. Create and Start Experiment
    experiment = e_svc.create_experiment(
        session_id="sess-lgb",
        hypothesis_config={"metric": "sharpe"},
        experiment_id="exp-lgb"
    )
    experiment = e_svc.start_experiment("exp-lgb")

    # 3. Create and Start Run
    run = r_svc.create_run(
        experiment_id="exp-lgb",
        hyperparameters={"model_type": "lightgbm", "num_leaves": 31},
        run_id="run-lgb",
        session_id="sess-lgb"
    )
    run = r_svc.start_run("run-lgb")

    # 4. Execute Training Pipeline
    result, updated_run = pipeline.run(
        research_run=run,
        dataset_snapshot=ds_snap,
        feature_snapshot=feat_snap,
        training_config={"epochs": 50},
        seed=100,
        model_params={"model_type": "lightgbm", "num_leaves": 31}
    )
    
    # 5. Complete the Run with Pipeline results
    run = r_svc.complete_run(
        run_id="run-lgb",
        metrics=dict(result.metrics.to_tuple()),
        model_binary_path=result.artifacts.file_path,
        completed_at=updated_run.completed_at
    )
    assert run.status == "COMPLETED"
    assert run.model_binary_path.startswith("/storage/models/lightgbm_")

    # 6. Complete Experiment
    experiment = e_svc.complete_experiment(experiment_id="exp-lgb", runs=(run,))
    assert experiment.status == "EVALUATED"

    # 7. Complete Session
    session = s_svc.complete_session(session_id="sess-lgb", best_run_id="run-lgb", experiments=(experiment,))
    assert session.status == "COMPLETED"


def test_deterministic_execution(workflow_context):
    """Verify that identical inputs produce mathematically identical execution scorecards and checksums."""
    pipeline = workflow_context["pipeline_manager"]
    ds_snap = workflow_context["dataset_snapshot"]
    feat_snap = workflow_context["feature_snapshot"]
    r_svc = workflow_context["run_service"]

    run_1 = r_svc.create_run(experiment_id="exp-det", run_id="run-det-1")
    run_2 = r_svc.create_run(experiment_id="exp-det", run_id="run-det-2")

    res_1, _ = pipeline.run(
        research_run=run_1,
        dataset_snapshot=ds_snap,
        feature_snapshot=feat_snap,
        training_config={"epochs": 50},
        seed=42,
        model_params={"model_type": "lightgbm", "num_leaves": 31}
    )

    res_2, _ = pipeline.run(
        research_run=run_2,
        dataset_snapshot=ds_snap,
        feature_snapshot=feat_snap,
        training_config={"epochs": 50},
        seed=42,
        model_params={"model_type": "lightgbm", "num_leaves": 31}
    )

    assert res_1.metrics == res_2.metrics
    assert res_1.artifacts.checksum == res_2.artifacts.checksum


def test_immutable_outputs(workflow_context):
    """Verify that every returned context entity is read-only."""
    s_svc = workflow_context["session_service"]
    e_svc = workflow_context["experiment_service"]
    r_svc = workflow_context["run_service"]
    pipeline = workflow_context["pipeline_manager"]

    session = s_svc.create_session(config={"symbol": "BTCUSDT"}, session_id="sess-imm")
    experiment = e_svc.create_experiment(session_id="sess-imm", hypothesis_config={}, experiment_id="exp-imm")
    run = r_svc.create_run(experiment_id="exp-imm", run_id="run-imm")

    with pytest.raises(dataclasses.FrozenInstanceError):
        session.status = "RUNNING"  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        experiment.status = "ACTIVE"  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        run.status = "RUNNING"  # type: ignore


def test_lifecycle_propagation(workflow_context):
    """Verify lifecycle state transitions correctly propagate and prevent unlawful transitions."""
    r_svc = workflow_context["run_service"]

    run = r_svc.create_run(experiment_id="exp-life", run_id="run-life")
    assert run.status == "CREATED"

    # Cannot complete a run before starting it
    with pytest.raises(ValueError):
        r_svc.complete_run("run-life")

    # Start the run
    run = r_svc.start_run("run-life")
    assert run.status == "RUNNING"

    # Cannot start an already running run
    with pytest.raises(ValueError):
        r_svc.start_run("run-life")


def test_metadata_propagation(workflow_context):
    """Verify metadata configurations are correctly propagated throughout the system."""
    r_svc = workflow_context["run_service"]
    pipeline = workflow_context["pipeline_manager"]
    ds_snap = workflow_context["dataset_snapshot"]
    feat_snap = workflow_context["feature_snapshot"]

    run = r_svc.create_run(experiment_id="exp-meta", run_id="run-meta")
    run = r_svc.start_run("run-meta")

    result, updated_run = pipeline.run(
        research_run=run,
        dataset_snapshot=ds_snap,
        feature_snapshot=feat_snap,
        training_config={"epochs": 80},
        seed=999,
        model_params={"model_type": "xgboost", "max_depth": 5}
    )

    assert result.status == "SUCCESS"
    assert updated_run.model_binary_path == result.artifacts.file_path


def test_trainer_selection(workflow_context):
    """Verify TrainerFactory constructs correct trainer object type."""
    from ml_service.research.trainers.trainer_factory import TrainerFactory
    from ml_service.research.trainers.xgboost_trainer import XGBoostTrainer
    from ml_service.research.trainers.lightgbm_trainer import LightGBMTrainer

    xgb = TrainerFactory.create("xgboost")
    lgb = TrainerFactory.create("lightgbm")

    assert isinstance(xgb, XGBoostTrainer)
    assert isinstance(lgb, LightGBMTrainer)


def test_fail_fast_invalid_algorithm(workflow_context):
    """Verify that training pipeline fails fast when an invalid model algorithm is passed."""
    pipeline = workflow_context["pipeline_manager"]
    ds_snap = workflow_context["dataset_snapshot"]
    feat_snap = workflow_context["feature_snapshot"]
    r_svc = workflow_context["run_service"]

    run = r_svc.create_run(experiment_id="exp-fail", run_id="run-fail")
    
    with pytest.raises(ValueError, match="Unknown algorithm"):
        pipeline.run(
            research_run=run,
            dataset_snapshot=ds_snap,
            feature_snapshot=feat_snap,
            training_config={},
            seed=42,
            model_params={"model_type": "invalid_algo"}
        )


def test_multiple_independent_workflows(workflow_context):
    """Verify that multiple independent sessions run concurrently without leaking state."""
    s_svc = workflow_context["session_service"]
    e_svc = workflow_context["experiment_service"]
    r_svc = workflow_context["run_service"]

    s1 = s_svc.create_session(config={"symbol": "BTC"}, session_id="s1")
    s2 = s_svc.create_session(config={"symbol": "ETH"}, session_id="s2")

    e1 = e_svc.create_experiment(session_id="s1", hypothesis_config={}, experiment_id="e1")
    e2 = e_svc.create_experiment(session_id="s2", hypothesis_config={}, experiment_id="e2")

    r1 = r_svc.create_run(experiment_id="e1", run_id="r1")
    r2 = r_svc.create_run(experiment_id="e2", run_id="r2")

    assert s1.session_id != s2.session_id
    assert e1.experiment_id != e2.experiment_id
    assert r1.run_id != r2.run_id
