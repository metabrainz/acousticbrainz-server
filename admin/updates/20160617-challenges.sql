BEGIN;

CREATE TABLE challenge (
  id                  UUID,
  name                TEXT                     NOT NULL,
  validation_snapshot UUID                     NOT NULL, -- FK to dataset_snapshot
  creator             INTEGER                  NOT NULL, -- FK to user
  created             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  start_time          TIMESTAMP WITH TIME ZONE NOT NULL,
  end_time            TIMESTAMP WITH TIME ZONE NOT NULL,
  classes             TEXT                     NOT NULL,
  concluded           BOOLEAN                  NOT NULL DEFAULT FALSE
);

CREATE TABLE dataset_eval_challenge (
  dataset_eval_job UUID, -- PK, FK to dataset_eval_jobs
  challenge_id     UUID, -- PK, FK to challenge
  result           JSONB
);


ALTER TABLE challenge ADD CONSTRAINT challenge_pkey PRIMARY KEY (id);
ALTER TABLE dataset_eval_challenge ADD CONSTRAINT dataset_eval_challenge_pkey PRIMARY KEY (dataset_eval_job, challenge_id);


ALTER TABLE challenge
  ADD CONSTRAINT challenge_fk_dataset_snapshot
  FOREIGN KEY (validation_snapshot)
  REFERENCES dataset_snapshot (id);

ALTER TABLE challenge
  ADD CONSTRAINT challenge_fk_user
  FOREIGN KEY (creator)
  REFERENCES "user" (id);

ALTER TABLE dataset_eval_challenge
  ADD CONSTRAINT dataset_eval_challenge_fk_dataset_eval_job
  FOREIGN KEY (dataset_eval_job)
  REFERENCES dataset_eval_jobs (id);

ALTER TABLE dataset_eval_challenge
  ADD CONSTRAINT dataset_eval_challenge_fk_challenge
  FOREIGN KEY (challenge_id)
  REFERENCES challenge (id);

COMMIT;
