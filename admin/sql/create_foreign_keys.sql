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
  ADD CONSTRAINT dataset_eval_jobs_fk_dataset
  FOREIGN KEY (dataset_id)
  REFERENCES dataset (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

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
