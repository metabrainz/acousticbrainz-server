BEGIN;

ALTER TABLE lowlevel ALTER COLUMN submission_offset SET NOT NULL;
CREATE INDEX submission_offset_ndx_lowlevel ON lowlevel (submission_offset);

COMMIT;