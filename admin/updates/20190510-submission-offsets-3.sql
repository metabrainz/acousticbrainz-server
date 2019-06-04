BEGIN;

ALTER TABLE lowlevel ALTER COLUMN submission_offset SET NOT NULL;
CREATE INDEX gid_submission_offset_ndx_lowlevel ON lowlevel (gid, submission_offset);

COMMIT;