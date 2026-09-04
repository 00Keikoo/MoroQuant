import json
import sqlite3
from typing import List, Optional, Tuple, Union, Any, Dict

from ml_service.repositories.database import get_connection
from ml_service.research.models import (
    ResearchSession,
    ResearchExperiment,
    ResearchRun,
    DatasetSnapshot,
    FeatureSnapshot,
)


class ResearchRepository:
    """
    SQLite-backed repository for research session persistence.

    Stores immutable research objects in normalized tables with atomic UPSERT
    and nested reconstruction.

    Note: Dataset and feature snapshot methods remain in-memory for backward
    compatibility. They are not used by the canonical orchestrator and are
    outside Phase 2 SQLite persistence scope.
    """
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        self._dataset_snapshots = {}
        self._feature_snapshots = {}
        self._experiments = {}
        self._in_memory_conn = None

        if db_path is None:
            self._in_memory_conn = sqlite3.connect(":memory:")
            self._in_memory_conn.row_factory = sqlite3.Row
            self._in_memory_conn.execute("PRAGMA foreign_keys = ON")
            self._bootstrap_in_memory_schema()

    def _bootstrap_in_memory_schema(self) -> None:
        """Bootstrap schema for in-memory database."""
        from ml_service.bootstrap.research_database import bootstrap_research_tables
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            bootstrap_research_tables(tmp_path)
            tmp_conn = sqlite3.connect(tmp_path)
            for line in tmp_conn.iterdump():
                if line.startswith("CREATE TABLE") or line.startswith("CREATE INDEX"):
                    self._in_memory_conn.execute(line)
            tmp_conn.close()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        if self._in_memory_conn is not None:
            return self._in_memory_conn
        conn = get_connection(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _close_conn(self, conn: sqlite3.Connection) -> None:
        """Close connection only if not in-memory."""
        if conn is not self._in_memory_conn:
            conn.close()

    def create_session(self, session: ResearchSession) -> ResearchSession:
        """Create a new session. Raises ValueError if session_id already exists."""
        if not isinstance(session, ResearchSession):
            raise TypeError("Expected a ResearchSession instance.")

        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM research_sessions WHERE session_id = ?",
                (session.session_id,)
            )
            if cursor.fetchone() is not None:
                raise ValueError(f"Session with ID '{session.session_id}' already exists.")

            return self.save_session(session)
        finally:
            self._close_conn(conn)

    def save_session(self, session: ResearchSession) -> ResearchSession:
        """Atomically persist session with nested experiments and runs using UPSERT."""
        if not isinstance(session, ResearchSession):
            raise TypeError("Expected a ResearchSession instance.")

        conn = self._get_conn()
        try:
            conn.execute("BEGIN")

            config_json = json.dumps([list(item) for item in sorted(session.config_snapshot, key=lambda x: x[0])])

            conn.execute("""
                INSERT INTO research_sessions (
                    session_id, status, dataset_version_id, snapshot_id, feature_dataset_id,
                    best_run_id, random_seed, config_json, dataset_fingerprint, feature_fingerprint,
                    replay_fingerprint, experiment_fingerprint, evaluation_fingerprint,
                    model_fingerprint, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    status = excluded.status,
                    dataset_version_id = excluded.dataset_version_id,
                    snapshot_id = excluded.snapshot_id,
                    feature_dataset_id = excluded.feature_dataset_id,
                    best_run_id = excluded.best_run_id,
                    random_seed = excluded.random_seed,
                    config_json = excluded.config_json,
                    dataset_fingerprint = excluded.dataset_fingerprint,
                    feature_fingerprint = excluded.feature_fingerprint,
                    replay_fingerprint = excluded.replay_fingerprint,
                    experiment_fingerprint = excluded.experiment_fingerprint,
                    evaluation_fingerprint = excluded.evaluation_fingerprint,
                    model_fingerprint = excluded.model_fingerprint,
                    created_at = excluded.created_at,
                    completed_at = excluded.completed_at
            """, (
                session.session_id, session.status, session.dataset_version_id,
                session.snapshot_id, session.feature_dataset_id, session.best_run_id,
                session.random_seed, config_json, session.dataset_fingerprint,
                session.feature_fingerprint, session.replay_fingerprint,
                session.experiment_fingerprint, session.evaluation_fingerprint,
                session.model_fingerprint, session.created_at, session.completed_at
            ))

            conn.execute("DELETE FROM research_experiments WHERE session_id = ?", (session.session_id,))

            for experiment in session.experiments:
                hypothesis_json = json.dumps([list(item) for item in sorted(experiment.hypothesis_config, key=lambda x: x[0])])
                conn.execute("""
                    INSERT INTO research_experiments (
                        experiment_id, session_id, status, hypothesis_json, created_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    experiment.experiment_id, experiment.session_id, experiment.status,
                    hypothesis_json, experiment.created_at, experiment.completed_at
                ))

                for run in experiment.runs:
                    hyperparameters_json = json.dumps([list(item) for item in sorted(run.hyperparameters, key=lambda x: x[0])])
                    metrics_json = json.dumps([list(item) for item in sorted(run.metrics, key=lambda x: x[0])])
                    conn.execute("""
                        INSERT INTO research_runs (
                            run_id, experiment_id, session_id, status, hyperparameters_json,
                            metrics_json, model_binary_path, created_at, completed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        run.run_id, run.experiment_id, run.session_id, run.status,
                        hyperparameters_json, metrics_json, run.model_binary_path,
                        run.created_at, run.completed_at
                    ))

            conn.commit()
            return session
        except Exception:
            conn.rollback()
            raise
        finally:
            self._close_conn(conn)

    def get_session(self, session_id: str) -> ResearchSession:
        """Reconstruct session with nested experiments and runs."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM research_sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()

            if row is None:
                raise KeyError(f"Session with ID '{session_id}' not found.")

            exp_rows = conn.execute(
                "SELECT * FROM research_experiments WHERE session_id = ? ORDER BY experiment_id",
                (session_id,)
            ).fetchall()

            experiments = []
            for exp_row in exp_rows:
                run_rows = conn.execute(
                    "SELECT * FROM research_runs WHERE experiment_id = ? ORDER BY run_id",
                    (exp_row["experiment_id"],)
                ).fetchall()

                runs = tuple(
                    ResearchRun(
                        run_id=run_row["run_id"],
                        experiment_id=run_row["experiment_id"],
                        session_id=run_row["session_id"],
                        status=run_row["status"],
                        hyperparameters=tuple(tuple(item) for item in json.loads(run_row["hyperparameters_json"])),
                        metrics=tuple(tuple(item) for item in json.loads(run_row["metrics_json"])),
                        model_binary_path=run_row["model_binary_path"],
                        created_at=run_row["created_at"],
                        completed_at=run_row["completed_at"]
                    )
                    for run_row in run_rows
                )

                experiments.append(
                    ResearchExperiment(
                        experiment_id=exp_row["experiment_id"],
                        session_id=exp_row["session_id"],
                        status=exp_row["status"],
                        hypothesis_config=tuple(tuple(item) for item in json.loads(exp_row["hypothesis_json"])),
                        runs=runs,
                        created_at=exp_row["created_at"],
                        completed_at=exp_row["completed_at"]
                    )
                )

            return ResearchSession(
                session_id=row["session_id"],
                status=row["status"],
                config_snapshot=tuple(tuple(item) for item in json.loads(row["config_json"])),
                snapshot_id=row["snapshot_id"],
                dataset_version_id=row["dataset_version_id"],
                feature_dataset_id=row["feature_dataset_id"],
                best_run_id=row["best_run_id"],
                experiments=tuple(experiments),
                created_at=row["created_at"],
                completed_at=row["completed_at"],
                dataset_fingerprint=row["dataset_fingerprint"],
                feature_fingerprint=row["feature_fingerprint"],
                replay_fingerprint=row["replay_fingerprint"],
                experiment_fingerprint=row["experiment_fingerprint"],
                evaluation_fingerprint=row["evaluation_fingerprint"],
                model_fingerprint=row["model_fingerprint"],
                random_seed=row["random_seed"]
            )
        finally:
            self._close_conn(conn)

    def list_sessions(self) -> List[ResearchSession]:
        """Return all sessions sorted by session_id."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT session_id FROM research_sessions ORDER BY session_id"
            ).fetchall()

            return [self.get_session(row["session_id"]) for row in rows]
        finally:
            self._close_conn(conn)

    def delete_session(self, session_id: str) -> None:
        """Delete session with cascade to experiments and runs."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM research_sessions WHERE session_id = ?",
                (session_id,)
            )
            if cursor.fetchone() is None:
                raise KeyError(f"Session with ID '{session_id}' not found.")

            conn.execute("DELETE FROM research_experiments WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM research_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        finally:
            self._close_conn(conn)

    def save_experiment(self, experiment: ResearchExperiment) -> ResearchExperiment:
        """Save experiment (in-memory, backward compatibility only)."""
        if not isinstance(experiment, ResearchExperiment):
            raise TypeError("Expected a ResearchExperiment instance.")
        if experiment.experiment_id in self._experiments:
            raise ValueError(f"Experiment with ID '{experiment.experiment_id}' already exists.")
        self._experiments[experiment.experiment_id] = experiment
        return experiment

    def get_experiment(self, experiment_id: str) -> ResearchExperiment:
        """Get experiment (in-memory, backward compatibility only)."""
        if experiment_id not in self._experiments:
            raise KeyError(f"Experiment with ID '{experiment_id}' not found.")
        return self._experiments[experiment_id]

    def list_experiments(self, session_id: str) -> List[ResearchExperiment]:
        """List experiments for session (in-memory, backward compatibility only)."""
        experiments = [e for e in self._experiments.values() if e.session_id == session_id]
        return sorted(experiments, key=lambda e: e.experiment_id)

    def delete_experiment(self, experiment_id: str) -> None:
        """Delete experiment (in-memory, backward compatibility only)."""
        if experiment_id not in self._experiments:
            raise KeyError(f"Experiment with ID '{experiment_id}' not found.")
        del self._experiments[experiment_id]

    def save_dataset_snapshot(self, snapshot: DatasetSnapshot) -> DatasetSnapshot:
        """Save dataset snapshot (in-memory, backward compatibility only)."""
        if not isinstance(snapshot, DatasetSnapshot):
            raise TypeError("Expected a DatasetSnapshot instance.")
        if snapshot.dataset_version_id in self._dataset_snapshots:
            raise ValueError(f"Dataset snapshot with ID '{snapshot.dataset_version_id}' already exists.")
        self._dataset_snapshots[snapshot.dataset_version_id] = snapshot
        return snapshot

    def get_dataset_snapshot(self, dataset_version_id: str) -> DatasetSnapshot:
        """Get dataset snapshot (in-memory, backward compatibility only)."""
        if dataset_version_id not in self._dataset_snapshots:
            raise KeyError(f"Dataset snapshot with ID '{dataset_version_id}' not found.")
        return self._dataset_snapshots[dataset_version_id]

    def save_feature_snapshot(self, snapshot: FeatureSnapshot) -> FeatureSnapshot:
        """Save feature snapshot (in-memory, backward compatibility only)."""
        if not isinstance(snapshot, FeatureSnapshot):
            raise TypeError("Expected a FeatureSnapshot instance.")
        if snapshot.feature_dataset_id in self._feature_snapshots:
            raise ValueError(f"Feature snapshot with ID '{snapshot.feature_dataset_id}' already exists.")
        self._feature_snapshots[snapshot.feature_dataset_id] = snapshot
        return snapshot

    def get_feature_snapshot(self, feature_dataset_id: str) -> FeatureSnapshot:
        """Get feature snapshot (in-memory, backward compatibility only)."""
        if feature_dataset_id not in self._feature_snapshots:
            raise KeyError(f"Feature snapshot with ID '{feature_dataset_id}' not found.")
        return self._feature_snapshots[feature_dataset_id]
