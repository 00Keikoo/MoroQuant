-- 021_execution_intelligence.sql
-- Milestone 5: Execution Intelligence & Trade Quality Engine
-- Add MAE/MFE tracking, EQS, and trailing stop research metadata

ALTER TABLE paper_positions ADD COLUMN mae REAL DEFAULT 0.0;
ALTER TABLE paper_positions ADD COLUMN mfe REAL DEFAULT 0.0;
ALTER TABLE paper_positions ADD COLUMN mae_timestamp TIMESTAMP;
ALTER TABLE paper_positions ADD COLUMN mfe_timestamp TIMESTAMP;

ALTER TABLE paper_positions ADD COLUMN eqs INTEGER;
ALTER TABLE paper_positions ADD COLUMN profit_capture_ratio REAL;
ALTER TABLE paper_positions ADD COLUMN final_exit_reason TEXT;

ALTER TABLE paper_positions ADD COLUMN trailing_stop_enabled INTEGER DEFAULT 0;
ALTER TABLE paper_positions ADD COLUMN trailing_stop_activated INTEGER DEFAULT 0;
ALTER TABLE paper_positions ADD COLUMN sl_move_count INTEGER DEFAULT 0;
ALTER TABLE paper_positions ADD COLUMN break_even_triggered INTEGER DEFAULT 0;
