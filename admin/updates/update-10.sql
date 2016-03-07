BEGIN;

DROP TABLE dataset_eval_jobs;

CREATE TABLE dataset_eval_jobs (
  id                UUID,
  dataset_id        UUID                     NOT NULL,
  status            eval_job_status          NOT NULL DEFAULT 'pending',
  status_msg        VARCHAR,
  options           JSONB,
  training_snapshot INT,                     -- FK to dataset_snapshot
  testing_snapshot  INT,                     -- FK to dataset_snapshot
  created           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  result            JSONB
);

CREATE TABLE dataset_snapshot (
  id   SERIAL,
  data JSONB NOT NULL
);

ALTER TABLE dataset_eval_jobs ADD CONSTRAINT dataset_eval_jobs_pkey PRIMARY KEY (id);
ALTER TABLE dataset_snapshot ADD CONSTRAINT dataset_snapshot_pkey PRIMARY KEY (id);

ALTER TABLE dataset_eval_jobs
  ADD CONSTRAINT dataset_eval_jobs_fk_training_snapshot
  FOREIGN KEY (training_snapshot)
  REFERENCES dataset_snapshot (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_eval_jobs
  ADD CONSTRAINT dataset_eval_jobs_fk_testing_snapshot
  FOREIGN KEY (testing_snapshot)
  REFERENCES dataset_snapshot (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

COMMIT;
