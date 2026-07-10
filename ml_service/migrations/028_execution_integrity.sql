-- Migration 028: Paper Trading Execution Integrity
-- Add execution metadata to separate signal price from actual execution price

-- Add execution metadata columns
ALTER TABLE paper_positions ADD COLUMN signal_price REAL;
ALTER TABLE paper_positions ADD COLUMN execution_price REAL;
ALTER TABLE paper_positions ADD COLUMN execution_timestamp TIMESTAMP;
ALTER TABLE paper_positions ADD COLUMN slippage_pct REAL;
ALTER TABLE paper_positions ADD COLUMN execution_latency_ms INTEGER;

-- Backfill existing positions: signal_price = entry_price (best approximation)
UPDATE paper_positions
SET signal_price = entry_price,
    execution_price = entry_price,
    execution_timestamp = opened_at,
    slippage_pct = 0.0,
    execution_latency_ms = 0
WHERE signal_price IS NULL;

-- Create index for execution analysis
CREATE INDEX IF NOT EXISTS idx_paper_positions_execution_timestamp
ON paper_positions(execution_timestamp);
