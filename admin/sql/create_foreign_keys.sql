BEGIN;

ALTER TABLE lowlevel_json
  ADD CONSTRAINT lowlevel_json_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);

ALTER TABLE lowlevel_json
  ADD CONSTRAINT lowlevel_json_fk_version
  FOREIGN KEY (version)
  REFERENCES version (id);

ALTER TABLE highlevel
  ADD CONSTRAINT highlevel_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);

ALTER TABLE highlevel_meta
  ADD CONSTRAINT highlevel_meta_fk_highlevel
  FOREIGN KEY (id)
  REFERENCES highlevel (id);

ALTER TABLE highlevel_model
  ADD CONSTRAINT highlevel_model_fk_highlevel
  FOREIGN KEY (highlevel)
  REFERENCES highlevel (id);

ALTER TABLE highlevel_model
  ADD CONSTRAINT highlevel_model_fk_version
  FOREIGN KEY (version)
  REFERENCES version (id);

ALTER TABLE highlevel_model
  ADD CONSTRAINT highlevel_model_fk_model
  FOREIGN KEY (model)
  REFERENCES model (id);

ALTER TABLE dataset
  ADD CONSTRAINT dataset_fk_user
  FOREIGN KEY (author)
  REFERENCES "user" (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_class
  ADD CONSTRAINT class_fk_dataset
  FOREIGN KEY (dataset)
  REFERENCES dataset (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_class_member
  ADD CONSTRAINT class_member_fk_class
  FOREIGN KEY (class)
  REFERENCES dataset_class (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_eval_jobs
  ADD CONSTRAINT dataset_eval_jobs_fk_dataset_snapshot
  FOREIGN KEY (snapshot_id)
  REFERENCES dataset_snapshot (id);

ALTER TABLE dataset_eval_jobs
  ADD CONSTRAINT dataset_eval_jobs_fk_training_snapshot
  FOREIGN KEY (training_snapshot)
  REFERENCES dataset_eval_sets (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_eval_jobs
  ADD CONSTRAINT dataset_eval_jobs_fk_testing_snapshot
  FOREIGN KEY (testing_snapshot)
  REFERENCES dataset_eval_sets (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_snapshot
  ADD CONSTRAINT dataset_id_fk_dataset
  FOREIGN KEY (dataset_id)
  REFERENCES dataset (id);

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

ALTER TABLE api_key
  ADD CONSTRAINT api_key_fk_user
  FOREIGN KEY (owner)
  REFERENCES "user" (id);

ALTER TABLE feedback
  ADD CONSTRAINT feedback_fk_highlevel_model
  FOREIGN KEY (highlevel_model_id)
  REFERENCES highlevel_model (id);

ALTER TABLE feedback
  ADD CONSTRAINT feedback_fk_user
  FOREIGN KEY (user_id)
  REFERENCES "user" (id);

ALTER TABLE similarity.similarity
  ADD CONSTRAINT similarity_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);
  
ALTER TABLE similarity.similarity_stats
  ADD CONSTRAINT similarity_stats_fk_metric
  FOREIGN KEY (metric)
  REFERENCES similarity.similarity_metrics (metric);

ALTER TABLE similarity_eval
  ADD CONSTRAINT similarity_eval_fk_user
  FOREIGN KEY (user_id)
  REFERENCES "user" (id);

ALTER TABLE similarity_eval
  ADD CONSTRAINT similarity_eval_fk_metric
  FOREIGN KEY (metric)
  REFERENCES similarity_metrics (metric);

COMMIT;
