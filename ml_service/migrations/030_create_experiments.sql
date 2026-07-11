-- Migration 030: Create Experiments Table
-- Experiment Registry for tracking ML training runs and research iterations

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identifiers
    experiment_id TEXT NOT NULL,
    run_id TEXT NOT NULL UNIQUE,

    -- Status
    status TEXT NOT NULL CHECK(status IN ('CREATED', 'RUNNING', 'COMPLETED', 'FAILED')),

    -- Inputs
    dataset_version TEXT,
    feature_version TEXT,
    model_version TEXT,
    hyperparameters TEXT,

    -- Performance Metrics
    train_loss REAL,
    validation_loss REAL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    calmar_ratio REAL,
    profit_factor REAL,
    win_rate REAL,
    max_drawdown REAL,
    ece REAL,
    brier_score REAL,

    -- Metadata
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_experiments_experiment_id
    ON experiments(experiment_id);

CREATE INDEX IF NOT EXISTS idx_experiments_run_id
    ON experiments(run_id);

CREATE INDEX IF NOT EXISTS idx_experiments_status
    ON experiments(status);

CREATE INDEX IF NOT EXISTS idx_experiments_created_at
    ON experiments(created_at);

CREATE INDEX IF NOT EXISTS idx_experiments_sharpe_ratio
    ON experiments(sharpe_ratio)
    WHERE status = 'COMPLETED';
