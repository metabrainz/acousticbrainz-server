BEGIN;
CREATE TYPE eval_location_type AS ENUM ('local', 'remote');
ALTER TABLE dataset_eval_jobs ADD COLUMN eval_location eval_location_type NOT NULL DEFAULT 'local';
UPDATE dataset_eval_jobs SET eval_location = 'local';

COMMIT;


