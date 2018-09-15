BEGIN;

ALTER TABLE lowlevel_json DROP CONSTRAINT lowlevel_json_fk_lowlevel;
ALTER TABLE lowlevel_json DROP CONSTRAINT lowlevel_json_fk_version;
ALTER TABLE highlevel     DROP CONSTRAINT highlevel_fk_lowlevel;
ALTER TABLE highlevel_meta DROP CONSTRAINT highlevel_meta_fk_highlevel;
ALTER TABLE highlevel_model DROP CONSTRAINT highlevel_model_fk_highlevel;
ALTER TABLE highlevel_model DROP CONSTRAINT highlevel_model_fk_version;
ALTER TABLE highlevel_model DROP CONSTRAINT highlevel_model_fk_model;
ALTER TABLE dataset DROP CONSTRAINT dataset_fk_user;
ALTER TABLE dataset_class DROP CONSTRAINT class_fk_dataset;
ALTER TABLE dataset_class_member DROP CONSTRAINT class_member_fk_class;
ALTER TABLE dataset_eval_jobs DROP CONSTRAINT dataset_eval_jobs_fk_dataset_snapshot;
ALTER TABLE dataset_eval_jobs DROP CONSTRAINT dataset_eval_jobs_fk_training_snapshot;
ALTER TABLE dataset_eval_jobs DROP CONSTRAINT dataset_eval_jobs_fk_testing_snapshot;
ALTER TABLE dataset_snapshot DROP CONSTRAINT dataset_id_fk_dataset;
ALTER TABLE challenge DROP CONSTRAINT challenge_fk_dataset_snapshot;
ALTER TABLE challenge DROP CONSTRAINT challenge_fk_user;
ALTER TABLE dataset_eval_challenge DROP CONSTRAINT dataset_eval_challenge_fk_dataset_eval_job;
ALTER TABLE dataset_eval_challenge DROP CONSTRAINT dataset_eval_challenge_fk_challenge;
ALTER TABLE api_key DROP CONSTRAINT api_key_fk_user;
ALTER TABLE feedback DROP CONSTRAINT feedback_fk_highlevel_model;
ALTER TABLE feedback DROP CONSTRAINT feedback_fk_user;

COMMIT;
