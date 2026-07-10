"""Production-safe bootstrap for research database tables.

Creates all required research metadata tables with proper constraints and indexes.
Safe to run multiple times (idempotent).
"""

import sqlite3
from pathlib import Path
from typing import Optional


def bootstrap_research_tables(db_path: Optional[str] = None) -> None:
    """Initialize all research infrastructure tables.

    Creates:
    - dataset_metadata (Dataset Manager)
    - feature_definitions, feature_versions, feature_datasets (Feature Store)
    - experiments, experiment_configs, experiment_results (Experiment Registry)
    - models, model_versions, model_lineage, model_evaluations (Model Registry)

    All operations use IF NOT EXISTS - safe to run multiple times.
    """
    if db_path is None:
        db_path = Path(__file__).parent.parent.parent / "storage" / "database.db"

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Dataset Manager tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dataset_metadata (
                dataset_id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                fingerprint TEXT NOT NULL UNIQUE,
                snapshot_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                is_frozen INTEGER DEFAULT 0,
                schema_json TEXT NOT NULL,
                preprocessing_json TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dataset_snapshot
            ON dataset_metadata(snapshot_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dataset_fingerprint
            ON dataset_metadata(fingerprint)
        """)

        # Feature Store tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_definitions (
                feature_name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                formula_ref TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_versions (
                feature_version_id TEXT PRIMARY KEY,
                feature_name TEXT NOT NULL,
                version TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (feature_name) REFERENCES feature_definitions(feature_name)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_datasets (
                feature_dataset_id TEXT PRIMARY KEY,
                source_dataset_id TEXT NOT NULL,
                feature_version_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL UNIQUE,
                storage_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                is_frozen INTEGER DEFAULT 0,
                FOREIGN KEY (feature_version_id) REFERENCES feature_versions(feature_version_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_dataset_source
            ON feature_datasets(source_dataset_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_dataset_version
            ON feature_datasets(feature_version_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_dataset_fingerprint
            ON feature_datasets(fingerprint)
        """)

        # Experiment Registry tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                snapshot_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_configs (
                experiment_id TEXT NOT NULL,
                config_id TEXT NOT NULL,
                threshold_long REAL NOT NULL,
                threshold_short REAL NOT NULL,
                regime_filter TEXT,
                PRIMARY KEY (experiment_id, config_id),
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_results (
                experiment_id TEXT NOT NULL,
                config_id TEXT NOT NULL,
                pnl REAL NOT NULL,
                winrate REAL NOT NULL,
                sharpe REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                consistency_score REAL NOT NULL,
                trade_count INTEGER NOT NULL,
                PRIMARY KEY (experiment_id, config_id),
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)

        # Model Registry tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_versions (
                model_version_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                version TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                fingerprint TEXT NOT NULL UNIQUE,
                storage_path TEXT NOT NULL,
                hyperparameters_json TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                created_at TEXT NOT NULL,
                promoted_at TEXT,
                promoted_by TEXT,
                git_commit TEXT,
                git_tag TEXT,
                is_frozen INTEGER DEFAULT 0,
                FOREIGN KEY (model_id) REFERENCES models(model_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_lineage (
                model_version_id TEXT PRIMARY KEY,
                snapshot_id TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                feature_dataset_id TEXT NOT NULL,
                experiment_id TEXT NOT NULL,
                best_config_id TEXT NOT NULL,
                FOREIGN KEY (model_version_id) REFERENCES model_versions(model_version_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_evaluations (
                model_version_id TEXT PRIMARY KEY,
                sharpe_ratio REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                ece REAL NOT NULL,
                brier_score REAL NOT NULL,
                win_rate REAL NOT NULL,
                profit_factor REAL NOT NULL,
                sortino_ratio REAL NOT NULL,
                trade_count INTEGER NOT NULL,
                is_approved INTEGER DEFAULT 0,
                approved_by TEXT,
                approved_at TEXT,
                FOREIGN KEY (model_version_id) REFERENCES model_versions(model_version_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_version_state
            ON model_versions(lifecycle_state)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_version_symbol
            ON model_versions(symbol, timeframe, algorithm)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_version_fingerprint
            ON model_versions(fingerprint)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_lineage_dataset
            ON model_lineage(dataset_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_lineage_feature_dataset
            ON model_lineage(feature_dataset_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_lineage_experiment
            ON model_lineage(experiment_id)
        """)

        # Research Orchestrator tables (Sprint 4.5)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_jobs (
                job_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                config_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                created_by TEXT NOT NULL DEFAULT 'system',
                error_message TEXT,
                error_stage TEXT,
                CONSTRAINT check_state CHECK (state IN ('CREATED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'))
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_jobs_state ON research_jobs(state)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_jobs_created_at ON research_jobs(created_at DESC)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_job_steps (
                step_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                stage_type TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                output_metadata_json TEXT,
                error_message TEXT,
                FOREIGN KEY (job_id) REFERENCES research_jobs(job_id),
                CONSTRAINT check_stage_type CHECK (stage_type IN (
                    'SNAPSHOT', 'DATASET', 'FEATURE', 'EXPERIMENT',
                    'EVALUATION', 'REGISTRY', 'DASHBOARD'
                )),
                CONSTRAINT check_status CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED'))
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_job_steps_job_id ON research_job_steps(job_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_job_steps_stage_type ON research_job_steps(stage_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_job_steps_status ON research_job_steps(status)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_job_logs (
                log_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                stage_type TEXT,
                FOREIGN KEY (job_id) REFERENCES research_jobs(job_id),
                CONSTRAINT check_level CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR'))
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_job_logs_job_id ON research_job_logs(job_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_job_logs_level ON research_job_logs(level)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_job_logs_timestamp ON research_job_logs(timestamp DESC)
        """)

        conn.commit()
        print("✓ Research database bootstrap complete")
        print("  Tables created: 14")
        print("  Indexes created: 20")

    finally:
        conn.close()


if __name__ == "__main__":
    bootstrap_research_tables()
    print("\nRun verification:")
    print("  python -m ml_service.research.dataset_manager.verify_dataset_manager")
    print("  python -m ml_service.research.feature_store.verify_feature_store")
    print("  python -m ml_service.research.research_dashboard.verify_research_dashboard")
    print("  python -m ml_service.research.model_registry.verify_model_registry")
