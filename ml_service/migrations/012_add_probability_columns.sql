-- Migration: Add probability tracking columns
-- Date: 2026-06-22

ALTER TABLE signals ADD COLUMN prob_short REAL;
ALTER TABLE signals ADD COLUMN prob_neutral REAL;
ALTER TABLE signals ADD COLUMN prob_long REAL;
