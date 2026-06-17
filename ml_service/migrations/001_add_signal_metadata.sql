-- Migration: Add TP/SL and labeling metadata to signals table
-- Date: 2026-06-17
-- Purpose: Enable complete signal attribution for trade performance analysis

-- Add TP/SL multipliers (optimized per symbol/timeframe)
ALTER TABLE signals ADD COLUMN tp_multiplier REAL;
ALTER TABLE signals ADD COLUMN sl_multiplier REAL;

-- Add labeling method (triple_barrier, fixed_horizon, etc.)
ALTER TABLE signals ADD COLUMN labeling_method TEXT;

-- Add ATR value (needed to reconstruct TP/SL prices)
ALTER TABLE signals ADD COLUMN atr REAL;

-- Add regime classification (for quick filtering without JSON parsing)
ALTER TABLE signals ADD COLUMN regime TEXT;
