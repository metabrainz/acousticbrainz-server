BEGIN;

ALTER TABLE dataset_eval_jobs RENAME COLUMN dataset_id TO snapshot_id;
ALTER TABLE dataset_eval_jobs
  ADD CONSTRAINT dataset_eval_jobs_fk_dataset_snapshot
  FOREIGN KEY (snapshot_id)
  REFERENCES dataset_snapshot (id);

COMMIT;
