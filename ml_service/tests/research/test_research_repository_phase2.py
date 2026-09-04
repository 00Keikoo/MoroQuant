"""Phase 2 SQLite Research Repository Tests

Tests for Sprint 3.9D-16 Phase 2: SQLite session persistence with UPSERT,
nested reconstruction, atomic transactions, and cascade deletion.
"""

import tempfile
import pytest
import sqlite3
from pathlib import Path
from datetime import datetime

from ml_service.bootstrap.research_database import bootstrap_research_tables
from ml_service.research.research_repository import ResearchRepository
from ml_service.research.models import ResearchSession, ResearchExperiment, ResearchRun


def create_test_session(session_id: str = "test_session_001", status: str = "PENDING") -> ResearchSession:
    """Create a test session with minimal required fields."""
    return ResearchSession(
        session_id=session_id,
        status=status,
        config_snapshot=(("param1", "value1"), ("param2", 42)),
        created_at=datetime.utcnow().isoformat()
    )


def create_test_experiment(
    experiment_id: str = "exp_001",
    session_id: str = "test_session_001",
    status: str = "INITIALIZED"
) -> ResearchExperiment:
    """Create a test experiment with runs."""
    run1 = ResearchRun(
        run_id=f"{experiment_id}_run_001",
        experiment_id=experiment_id,
        session_id=session_id,
        status="COMPLETED",
        hyperparameters=(("learning_rate", 0.001), ("batch_size", 32)),
        metrics=(("accuracy", 0.95), ("loss", 0.05)),
        created_at=datetime.utcnow().isoformat()
    )
    run2 = ResearchRun(
        run_id=f"{experiment_id}_run_002",
        experiment_id=experiment_id,
        session_id=session_id,
        status="COMPLETED",
        hyperparameters=(("learning_rate", 0.01), ("batch_size", 64)),
        metrics=(("accuracy", 0.93), ("loss", 0.07)),
        created_at=datetime.utcnow().isoformat()
    )
    return ResearchExperiment(
        experiment_id=experiment_id,
        session_id=session_id,
        status=status,
        hypothesis_config=(("hypothesis", "test"), ("version", 1)),
        runs=(run1, run2),
        created_at=datetime.utcnow().isoformat()
    )


class TestRepositoryBasics:
    """Test basic repository operations."""

    def test_save_session_creates_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            session = create_test_session()
            result = repo.save_session(session)

            assert result.session_id == session.session_id
            assert result.status == session.status

    def test_get_session_missing_raises_key_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            with pytest.raises(KeyError) as exc_info:
                repo.get_session("nonexistent_session")
            assert "not found" in str(exc_info.value)

    def test_list_sessions_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            sessions = repo.list_sessions()
            assert sessions == []

    def test_list_sessions_sorted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            repo.save_session(create_test_session("session_003"))
            repo.save_session(create_test_session("session_001"))
            repo.save_session(create_test_session("session_002"))

            sessions = repo.list_sessions()
            assert len(sessions) == 3
            assert sessions[0].session_id == "session_001"
            assert sessions[1].session_id == "session_002"
            assert sessions[2].session_id == "session_003"

    def test_delete_session_missing_raises_key_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            with pytest.raises(KeyError) as exc_info:
                repo.delete_session("nonexistent_session")
            assert "not found" in str(exc_info.value)


class TestUpsertSemantics:
    """Test save_session UPSERT behavior."""

    def test_save_session_upsert(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            session_v1 = create_test_session("session_001", "PENDING")
            repo.save_session(session_v1)

            session_v2 = ResearchSession(
                session_id="session_001",
                status="COMPLETED",
                config_snapshot=(("param1", "updated_value"), ("param2", 99)),
                dataset_fingerprint="fingerprint_123",
                created_at=session_v1.created_at,
                completed_at=datetime.utcnow().isoformat()
            )
            repo.save_session(session_v2)

            sessions = repo.list_sessions()
            assert len(sessions) == 1

            retrieved = repo.get_session("session_001")
            assert retrieved.status == "COMPLETED"
            assert retrieved.config_snapshot == (("param1", "updated_value"), ("param2", 99))
            assert retrieved.dataset_fingerprint == "fingerprint_123"
            assert retrieved.completed_at is not None


class TestNestedPersistence:
    """Test nested experiments and runs persistence."""

    def test_save_session_with_experiments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            experiment = create_test_experiment("exp_001", "session_001")
            session = ResearchSession(
                session_id="session_001",
                status="EXPERIMENT",
                config_snapshot=(("param", "value"),),
                experiments=(experiment,),
                created_at=datetime.utcnow().isoformat()
            )

            repo.save_session(session)
            retrieved = repo.get_session("session_001")

            assert len(retrieved.experiments) == 1
            assert retrieved.experiments[0].experiment_id == "exp_001"

    def test_save_session_with_nested_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            experiment = create_test_experiment("exp_001", "session_001")
            session = ResearchSession(
                session_id="session_001",
                status="EXPERIMENT",
                config_snapshot=(("param", "value"),),
                experiments=(experiment,),
                created_at=datetime.utcnow().isoformat()
            )

            repo.save_session(session)
            retrieved = repo.get_session("session_001")

            assert len(retrieved.experiments) == 1
            assert len(retrieved.experiments[0].runs) == 2
            assert retrieved.experiments[0].runs[0].run_id == "exp_001_run_001"
            assert retrieved.experiments[0].runs[1].run_id == "exp_001_run_002"

    def test_get_session_reconstructs_nested_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            exp1 = create_test_experiment("exp_001", "session_001")
            exp2 = create_test_experiment("exp_002", "session_001")
            session = ResearchSession(
                session_id="session_001",
                status="EXPERIMENT",
                config_snapshot=(("param", "value"),),
                experiments=(exp1, exp2),
                created_at=datetime.utcnow().isoformat()
            )

            repo.save_session(session)
            retrieved = repo.get_session("session_001")

            assert len(retrieved.experiments) == 2
            assert retrieved.experiments[0].experiment_id == "exp_001"
            assert retrieved.experiments[1].experiment_id == "exp_002"
            assert len(retrieved.experiments[0].runs) == 2
            assert len(retrieved.experiments[1].runs) == 2


class TestDeterministicOrdering:
    """Test deterministic ordering of experiments and runs."""

    def test_experiments_sorted_by_experiment_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            exp3 = create_test_experiment("exp_003", "session_001")
            exp1 = create_test_experiment("exp_001", "session_001")
            exp2 = create_test_experiment("exp_002", "session_001")

            session = ResearchSession(
                session_id="session_001",
                status="EXPERIMENT",
                config_snapshot=(("param", "value"),),
                experiments=(exp3, exp1, exp2),
                created_at=datetime.utcnow().isoformat()
            )

            repo.save_session(session)
            retrieved = repo.get_session("session_001")

            assert len(retrieved.experiments) == 3
            assert retrieved.experiments[0].experiment_id == "exp_001"
            assert retrieved.experiments[1].experiment_id == "exp_002"
            assert retrieved.experiments[2].experiment_id == "exp_003"

    def test_runs_sorted_by_run_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            run3 = ResearchRun(
                run_id="run_003",
                experiment_id="exp_001",
                session_id="session_001",
                status="COMPLETED",
                hyperparameters=(("lr", 0.001),),
                metrics=(("acc", 0.95),),
                created_at=datetime.utcnow().isoformat()
            )
            run1 = ResearchRun(
                run_id="run_001",
                experiment_id="exp_001",
                session_id="session_001",
                status="COMPLETED",
                hyperparameters=(("lr", 0.01),),
                metrics=(("acc", 0.93),),
                created_at=datetime.utcnow().isoformat()
            )
            run2 = ResearchRun(
                run_id="run_002",
                experiment_id="exp_001",
                session_id="session_001",
                status="COMPLETED",
                hyperparameters=(("lr", 0.1),),
                metrics=(("acc", 0.90),),
                created_at=datetime.utcnow().isoformat()
            )

            experiment = ResearchExperiment(
                experiment_id="exp_001",
                session_id="session_001",
                status="EVALUATED",
                hypothesis_config=(("test", "value"),),
                runs=(run3, run1, run2),
                created_at=datetime.utcnow().isoformat()
            )

            session = ResearchSession(
                session_id="session_001",
                status="EXPERIMENT",
                config_snapshot=(("param", "value"),),
                experiments=(experiment,),
                created_at=datetime.utcnow().isoformat()
            )

            repo.save_session(session)
            retrieved = repo.get_session("session_001")

            runs = retrieved.experiments[0].runs
            assert len(runs) == 3
            assert runs[0].run_id == "run_001"
            assert runs[1].run_id == "run_002"
            assert runs[2].run_id == "run_003"


class TestCascadeDeletion:
    """Test cascade deletion of child records."""

    def test_delete_session_cascades_experiments_and_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            experiment = create_test_experiment("exp_001", "session_001")
            session = ResearchSession(
                session_id="session_001",
                status="EXPERIMENT",
                config_snapshot=(("param", "value"),),
                experiments=(experiment,),
                created_at=datetime.utcnow().isoformat()
            )

            repo.save_session(session)
            repo.delete_session("session_001")

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                exp_count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM research_experiments WHERE session_id = ?",
                    ("session_001",)
                ).fetchone()["cnt"]
                run_count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM research_runs WHERE session_id = ?",
                    ("session_001",)
                ).fetchone()["cnt"]

                assert exp_count == 0
                assert run_count == 0
            finally:
                conn.close()


class TestTransactionAtomicity:
    """Test transaction atomicity during save operations."""

    def test_transaction_rollback_on_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            session = create_test_session("session_001", "PENDING")
            repo.save_session(session)

            invalid_session = ResearchSession(
                session_id="session_002",
                status="INVALID_STATUS_THAT_VIOLATES_CHECK_CONSTRAINT_HOPEFULLY_CAUSING_ERROR",
                config_snapshot=(("param", "value"),),
                created_at=datetime.utcnow().isoformat()
            )

            try:
                repo.save_session(invalid_session)
            except sqlite3.IntegrityError:
                pass

            sessions = repo.list_sessions()
            assert len(sessions) == 1
            assert sessions[0].session_id == "session_001"


class TestRoundTrip:
    """Test complete round-trip preservation."""

    def test_session_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            experiment = create_test_experiment("exp_001", "session_001")
            original = ResearchSession(
                session_id="session_001",
                status="COMPLETED",
                config_snapshot=(("param1", "value1"), ("param2", 42), ("param3", True)),
                snapshot_id="snap_001",
                dataset_version_id="dataset_v1",
                feature_dataset_id="feature_v1",
                best_run_id="run_001",
                experiments=(experiment,),
                created_at="2024-01-01T00:00:00",
                completed_at="2024-01-01T12:00:00",
                dataset_fingerprint="fp_dataset",
                feature_fingerprint="fp_feature",
                replay_fingerprint="fp_replay",
                experiment_fingerprint="fp_experiment",
                evaluation_fingerprint="fp_evaluation",
                model_fingerprint="fp_model",
                random_seed=42
            )

            repo.save_session(original)
            retrieved = repo.get_session("session_001")

            assert retrieved.session_id == original.session_id
            assert retrieved.status == original.status
            assert retrieved.config_snapshot == original.config_snapshot
            assert retrieved.snapshot_id == original.snapshot_id
            assert retrieved.dataset_version_id == original.dataset_version_id
            assert retrieved.feature_dataset_id == original.feature_dataset_id
            assert retrieved.best_run_id == original.best_run_id
            assert retrieved.created_at == original.created_at
            assert retrieved.completed_at == original.completed_at
            assert retrieved.dataset_fingerprint == original.dataset_fingerprint
            assert retrieved.feature_fingerprint == original.feature_fingerprint
            assert retrieved.replay_fingerprint == original.replay_fingerprint
            assert retrieved.experiment_fingerprint == original.experiment_fingerprint
            assert retrieved.evaluation_fingerprint == original.evaluation_fingerprint
            assert retrieved.model_fingerprint == original.model_fingerprint
            assert retrieved.random_seed == original.random_seed
            assert len(retrieved.experiments) == 1


class TestHistoricalReconstruction:
    """Test historical session reconstruction without side effects."""

    def test_historical_session_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            experiment = create_test_experiment("exp_001", "session_001", "EVALUATED")
            session = ResearchSession(
                session_id="session_001",
                status="COMPLETED",
                config_snapshot=(("param", "value"),),
                experiments=(experiment,),
                dataset_fingerprint="fp_dataset",
                feature_fingerprint="fp_feature",
                replay_fingerprint="fp_replay",
                experiment_fingerprint="fp_experiment",
                evaluation_fingerprint="fp_evaluation",
                model_fingerprint="fp_model",
                created_at="2024-01-01T00:00:00",
                completed_at="2024-01-01T12:00:00"
            )

            repo.save_session(session)
            retrieved = repo.get_session("session_001")

            assert retrieved.status == "COMPLETED"
            assert retrieved.dataset_fingerprint == "fp_dataset"
            assert retrieved.feature_fingerprint == "fp_feature"
            assert retrieved.replay_fingerprint == "fp_replay"
            assert retrieved.experiment_fingerprint == "fp_experiment"
            assert retrieved.evaluation_fingerprint == "fp_evaluation"
            assert retrieved.model_fingerprint == "fp_model"


class TestExperimentMethods:
    """Test existing experiment repository methods."""

    def test_save_experiment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            session = create_test_session("session_001")
            repo.save_session(session)

            experiment = create_test_experiment("exp_001", "session_001")
            result = repo.save_experiment(experiment)

            assert result.experiment_id == "exp_001"

    def test_save_experiment_duplicate_raises_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            session = create_test_session("session_001")
            repo.save_session(session)

            experiment = create_test_experiment("exp_001", "session_001")
            repo.save_experiment(experiment)

            with pytest.raises(ValueError) as exc_info:
                repo.save_experiment(experiment)
            assert "already exists" in str(exc_info.value)

    def test_get_experiment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            session = create_test_session("session_001")
            repo.save_session(session)

            experiment = create_test_experiment("exp_001", "session_001")
            repo.save_experiment(experiment)

            retrieved = repo.get_experiment("exp_001")
            assert retrieved.experiment_id == "exp_001"
            assert len(retrieved.runs) == 2

    def test_get_experiment_missing_raises_key_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            with pytest.raises(KeyError):
                repo.get_experiment("nonexistent")

    def test_list_experiments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            session = create_test_session("session_001")
            repo.save_session(session)

            exp1 = create_test_experiment("exp_001", "session_001")
            exp2 = create_test_experiment("exp_002", "session_001")
            repo.save_experiment(exp2)
            repo.save_experiment(exp1)

            experiments = repo.list_experiments("session_001")
            assert len(experiments) == 2
            assert experiments[0].experiment_id == "exp_001"
            assert experiments[1].experiment_id == "exp_002"

    def test_delete_experiment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            session = create_test_session("session_001")
            repo.save_session(session)

            experiment = create_test_experiment("exp_001", "session_001")
            repo.save_experiment(experiment)

            repo.delete_experiment("exp_001")

            with pytest.raises(KeyError):
                repo.get_experiment("exp_001")

    def test_delete_experiment_missing_raises_key_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            bootstrap_research_tables(db_path)
            repo = ResearchRepository(db_path)

            with pytest.raises(KeyError):
                repo.delete_experiment("nonexistent")
