-- Migration 011: Add confidence pipeline diagnostic fields to signals table
-- Date: 2026-06-22
-- Purpose: Confidence pipeline repair — persist calibration and MTF diagnostics.
--
-- mtf_alignment: replaces the old confidence mutation (×1.15/×0.80 multipliers).
--   Values: AGREE | DISAGREE | NEUTRAL. Confidence is now purely probabilistic
--   (max of calibrated predict_proba), never mutated by MTF.
--
-- raw_probability_max: max(raw_predict_proba) before calibration, for
--   comparing calibration impact.
--
-- calibrated_probability_max: max(predict_proba) after calibration (or equal
--   to raw_probability_max when no calibration available), for diagnostics.

ALTER TABLE signals ADD COLUMN mtf_alignment TEXT DEFAULT 'NEUTRAL';
ALTER TABLE signals ADD COLUMN raw_probability_max REAL;
ALTER TABLE signals ADD COLUMN calibrated_probability_max REAL;
