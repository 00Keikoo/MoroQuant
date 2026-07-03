-- Migration 024: Regime Execution Policy - Structural Blocking Support
--
-- Creates table to support manual structural blocking of regimes as defined in
-- docs/research/regime_execution_policy.md Section 6 (Decision Rules).
--
-- Structural blocks are static overrides for regimes that cannot be traded due to
-- system design limits (e.g., API constraints, execution infrastructure gaps).

CREATE TABLE IF NOT EXISTS regime_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regime TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_regime_blocks_regime ON regime_blocks(regime);
CREATE INDEX IF NOT EXISTS idx_regime_blocks_active ON regime_blocks(is_active);
