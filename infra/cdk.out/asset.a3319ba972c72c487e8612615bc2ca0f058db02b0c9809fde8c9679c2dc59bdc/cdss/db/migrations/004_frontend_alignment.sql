-- CDSS migration 004: Frontend API alignment.
-- Add any columns that may be missing when DB was created from 001/002/003
-- so that handlers (engagement, activity, admin) work correctly.
-- Safe to run multiple times (ADD COLUMN IF NOT EXISTS / DO blocks).

-- visits: extracted_entities for AI summary and consultation history
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'visits' AND column_name = 'extracted_entities'
  ) THEN
    ALTER TABLE visits ADD COLUMN extracted_entities JSONB;
  END IF;
END $$;

-- audit_log: ensure resource is not null for admin/audit list (handler expects r.resource)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'audit_log' AND column_name = 'resource'
  ) THEN
    UPDATE audit_log SET resource = '' WHERE resource IS NULL;
    ALTER TABLE audit_log ALTER COLUMN resource SET NOT NULL;
    ALTER TABLE audit_log ALTER COLUMN resource SET DEFAULT '';
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    NULL; -- column may already be NOT NULL or not exist
END $$;

-- Index for audit list by timestamp (admin/audit)
CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log(timestamp DESC);
