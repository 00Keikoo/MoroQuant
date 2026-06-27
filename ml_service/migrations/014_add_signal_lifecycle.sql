-- 014: Add signal lifecycle columns to signals table
--
-- valid_until:       ISO timestamp when signal expires (computed at generation)
-- signal_status:     ACTIVE, TP_HIT, SL_HIT, or EXPIRED
-- status_updated_at: when status last changed from ACTIVE to terminal

ALTER TABLE signals ADD COLUMN valid_until TEXT;
ALTER TABLE signals ADD COLUMN signal_status TEXT DEFAULT 'ACTIVE';
ALTER TABLE signals ADD COLUMN status_updated_at TIMESTAMP;
