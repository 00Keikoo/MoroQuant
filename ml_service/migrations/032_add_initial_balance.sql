-- 032_add_initial_balance.sql
-- Add initial_balance column to paper_account for accurate return % calculations.
-- Sprint 2.2B - Backend Portfolio Normalization
--
-- Replaces unreachable Python migration: 0012_add_initial_balance.py

-- SQLite supports ALTER TABLE ADD COLUMN but not conditional column addition.
-- This migration will fail if column already exists (expected for production).
-- The migration runner handles this gracefully by checking schema_migrations.

ALTER TABLE paper_account
ADD COLUMN initial_balance REAL DEFAULT 10000.0;

-- Backfill existing row with default starting capital
UPDATE paper_account
SET initial_balance = 10000.0
WHERE id = 1 AND initial_balance IS NULL;
