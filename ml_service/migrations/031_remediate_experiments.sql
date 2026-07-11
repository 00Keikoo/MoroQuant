-- Migration 031: Remediate Experiments Table Architecture
-- Remove coupled metrics and fix rigid state machine per ADR-017

-- Drop the old table with rigid CHECK constraints
DROP TABLE IF EXISTS experiments;

-- Recreate with flexible lifecycle and clean domain model
CREATE TABLE experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identifiers
    experiment_id TEXT NOT NULL,
    run_id TEXT NOT NULL UNIQUE,

    -- Flexible lifecycle state machine
    -- Supports: CREATED, TRAINING, VALIDATING, CALIBRATING, PAPER, PROMOTION, PRODUCTION, ARCHIVED, FAILED
    status TEXT NOT NULL,

    -- Inputs (references to other registries)
    dataset_version TEXT,
    feature_version TEXT,
    model_version TEXT,
    hyperparameters TEXT,

    -- Training-specific metrics (acceptable in experiment domain)
    train_loss REAL,
    validation_loss REAL,

    -- Metadata
    notes TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX idx_experiments_experiment_id
    ON experiments(experiment_id);

CREATE INDEX idx_experiments_run_id
    ON experiments(run_id);

CREATE INDEX idx_experiments_status
    ON experiments(status);

CREATE INDEX idx_experiments_created_at
    ON experiments(created_at);

-- Note: Removed metrics that belong to other registries:
-- - sharpe_ratio, sortino_ratio, calmar_ratio, profit_factor, win_rate, max_drawdown (Model Registry)
-- - ece, brier_score (Calibration Center)
-- These should be stored in their respective registries and linked by run_id
