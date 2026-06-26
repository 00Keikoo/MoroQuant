-- 013: Add calibration_method column to signals table
--
-- Persists which calibration method was actually used during inference
-- (after isotonic→platt override). Enables telemetry for the confidence
-- integrity audit.

ALTER TABLE signals ADD COLUMN calibration_method TEXT;
