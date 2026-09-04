-- Migration 033: Create Research Sessions Tables
-- Sprint 3.9D-16 Phase 1: ResearchSession persistence schema

-- Research Sessions: top-level orchestration units
CREATE TABLE IF NOT EXISTS research_sessions (
    session_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(
        status IN (
            'PENDING', 'SNAPSHOT', 'REPLAY', 'EXPERIMENT',
            'EVALUATION', 'REPORTING', 'BENCHMARK', 'PROMOTION',
            'COMPLETED', 'CREATED', 'RUNNING', 'FAILED', 'CANCELLED'
        ) OR status LIKE 'FAILED/%'
    ),

    -- Input references
    dataset_version_id TEXT,
    snapshot_id TEXT,
    feature_dataset_id TEXT,

    -- Best result tracking
    best_run_id TEXT,

    -- Reproducibility
    random_seed INTEGER,
    config_json TEXT NOT NULL,

    -- Content-addressable fingerprints
    dataset_fingerprint TEXT,
    feature_fingerprint TEXT,
    replay_fingerprint TEXT,
    experiment_fingerprint TEXT,
    evaluation_fingerprint TEXT,
    model_fingerprint TEXT,

    -- Temporal tracking
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_research_sessions_status
    ON research_sessions(status);

CREATE INDEX IF NOT EXISTS idx_research_sessions_created_at
    ON research_sessions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_research_sessions_dataset_version_id
    ON research_sessions(dataset_version_id);

CREATE INDEX IF NOT EXISTS idx_research_sessions_model_fingerprint
    ON research_sessions(model_fingerprint);

-- Research Experiments: hypothesis testing within a session
CREATE TABLE IF NOT EXISTS research_experiments (
    experiment_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('INITIALIZED', 'ACTIVE', 'EVALUATED', 'FAILED', 'CANCELLED')),
    hypothesis_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,

    FOREIGN KEY (session_id) REFERENCES research_sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_research_experiments_session_id
    ON research_experiments(session_id);

CREATE INDEX IF NOT EXISTS idx_research_experiments_status
    ON research_experiments(status);

-- Research Runs: individual model training attempts
CREATE TABLE IF NOT EXISTS research_runs (
    run_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('CREATED', 'RUNNING', 'COMPLETED', 'FAILED')),
    hyperparameters_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    model_binary_path TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,

    FOREIGN KEY (experiment_id) REFERENCES research_experiments(experiment_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES research_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_research_runs_experiment_id
    ON research_runs(experiment_id);

CREATE INDEX IF NOT EXISTS idx_research_runs_session_id
    ON research_runs(session_id);

CREATE INDEX IF NOT EXISTS idx_research_runs_status
    ON research_runs(status);
