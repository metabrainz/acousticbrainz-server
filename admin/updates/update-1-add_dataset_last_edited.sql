BEGIN;

ALTER TABLE dataset ADD COLUMN last_edited TIMESTAMP WITH TIME ZONE DEFAULT NOW();
UPDATE dataset SET last_edited = created;

COMMIT;

