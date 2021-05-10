BEGIN;

ALTER TABLE lowlevel_json DROP CONSTRAINT IF EXISTS lowlevel_json_fk_lowlevel;
ALTER TABLE lowlevel_json DROP CONSTRAINT IF EXISTS lowlevel_json_fk_version;
ALTER TABLE highlevel     DROP CONSTRAINT IF EXISTS highlevel_fk_lowlevel;
ALTER TABLE highlevel_meta DROP CONSTRAINT IF EXISTS highlevel_meta_fk_highlevel;
ALTER TABLE highlevel_model DROP CONSTRAINT IF EXISTS highlevel_model_fk_highlevel;
ALTER TABLE highlevel_model DROP CONSTRAINT IF EXISTS highlevel_model_fk_version;
ALTER TABLE highlevel_model DROP CONSTRAINT IF EXISTS highlevel_model_fk_model;
ALTER TABLE dataset DROP CONSTRAINT IF EXISTS dataset_fk_user;
ALTER TABLE dataset_class DROP CONSTRAINT IF EXISTS class_fk_dataset;
ALTER TABLE dataset_class_member DROP CONSTRAINT IF EXISTS class_member_fk_class;
ALTER TABLE dataset_eval_jobs DROP CONSTRAINT IF EXISTS dataset_eval_jobs_fk_dataset_snapshot;
ALTER TABLE dataset_eval_jobs DROP CONSTRAINT IF EXISTS dataset_eval_jobs_fk_training_snapshot;
ALTER TABLE dataset_eval_jobs DROP CONSTRAINT IF EXISTS dataset_eval_jobs_fk_testing_snapshot;
ALTER TABLE dataset_snapshot DROP CONSTRAINT IF EXISTS dataset_id_fk_dataset;
ALTER TABLE challenge DROP CONSTRAINT IF EXISTS challenge_fk_dataset_snapshot;
ALTER TABLE challenge DROP CONSTRAINT IF EXISTS challenge_fk_user;
ALTER TABLE dataset_eval_challenge DROP CONSTRAINT IF EXISTS dataset_eval_challenge_fk_dataset_eval_job;
ALTER TABLE dataset_eval_challenge DROP CONSTRAINT IF EXISTS dataset_eval_challenge_fk_challenge;
ALTER TABLE api_key DROP CONSTRAINT IF EXISTS api_key_fk_user;
ALTER TABLE feedback DROP CONSTRAINT IF EXISTS feedback_fk_highlevel_model;
ALTER TABLE feedback DROP CONSTRAINT IF EXISTS feedback_fk_user;

COMMIT;
