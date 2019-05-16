BEGIN;

ALTER TABLE lowlevel ADD COLUMN submission_offset INTEGER;

COMMIT;