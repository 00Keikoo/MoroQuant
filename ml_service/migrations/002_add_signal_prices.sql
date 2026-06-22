-- Migration: Add price fields to signals table
-- Date: 2026-06-19
-- Purpose: Store immutable entry_price, take_profit, stop_loss at signal generation time

-- Forward migration: Add nullable columns
ALTER TABLE signals ADD COLUMN entry_price REAL;
ALTER TABLE signals ADD COLUMN take_profit REAL;
ALTER TABLE signals ADD COLUMN stop_loss REAL;

-- Add index for performance queries
CREATE INDEX IF NOT EXISTS idx_signals_entry_price
ON signals(entry_price) WHERE entry_price IS NOT NULL;

-- Rollback instructions (manual):
-- DROP INDEX IF EXISTS idx_signals_entry_price;
-- ALTER TABLE signals DROP COLUMN stop_loss;
-- ALTER TABLE signals DROP COLUMN take_profit;
-- ALTER TABLE signals DROP COLUMN entry_price;
