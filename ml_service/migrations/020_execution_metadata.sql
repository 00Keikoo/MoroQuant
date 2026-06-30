-- 020_execution_metadata.sql
-- Extend paper_positions with execution intelligence metadata.

ALTER TABLE paper_positions ADD COLUMN confidence INTEGER;
ALTER TABLE paper_positions ADD COLUMN regime TEXT;
ALTER TABLE paper_positions ADD COLUMN timeframe TEXT;

ALTER TABLE paper_positions ADD COLUMN prob_short REAL;
ALTER TABLE paper_positions ADD COLUMN prob_neutral REAL;
ALTER TABLE paper_positions ADD COLUMN prob_long REAL;

ALTER TABLE paper_positions ADD COLUMN execution_edge REAL;
ALTER TABLE paper_positions ADD COLUMN skip_reason TEXT;
