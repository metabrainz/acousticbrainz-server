BEGIN;

ALTER TABLE dataset_snapshot RENAME TO dataset_eval_sets;
ALTER TABLE dataset_eval_sets RENAME CONSTRAINT dataset_snapshot_pkey TO dataset_eval_sets_pkey;

CREATE TABLE dataset_snapshot (
  id         UUID, -- PK
  dataset_id UUID, -- FK to dataset
  data       JSONB                    NOT NULL,
  created    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE dataset_snapshot ADD CONSTRAINT dataset_snapshot_pkey PRIMARY KEY (id);

ALTER TABLE dataset_snapshot
  ADD CONSTRAINT dataset_id_fk_dataset
  FOREIGN KEY (dataset_id)
  REFERENCES dataset (id);

ALTER TABLE dataset_eval_jobs DROP CONSTRAINT dataset_eval_jobs_fk_dataset;

COMMIT;
