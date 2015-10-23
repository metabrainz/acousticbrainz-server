BEGIN;

CREATE TYPE eval_filter_type AS ENUM ('artist');

ALTER TABLE dataset_eval_jobs ADD COLUMN filter_type eval_filter_type;

ALTER TABLE dataset_eval_jobs ADD COLUMN normalize BOOLEAN;
UPDATE dataset_eval_jobs SET normalize = FALSE;
ALTER TABLE dataset_eval_jobs ALTER COLUMN normalize SET NOT NULL;

COMMIT;
