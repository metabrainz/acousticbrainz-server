BEGIN;

ALTER TABLE lowlevel DROP CONSTRAINT lowlevel_pkey;
ALTER TABLE lowlevel_json DROP CONSTRAINT lowlevel_json_pkey;
ALTER TABLE highlevel DROP CONSTRAINT highlevel_pkey;
ALTER TABLE highlevel_meta DROP CONSTRAINT highlevel_meta_pkey;
ALTER TABLE highlevel_model DROP CONSTRAINT highlevel_model_pkey;
ALTER TABLE model DROP CONSTRAINT model_pkey;
ALTER TABLE version DROP CONSTRAINT version_pkey;
ALTER TABLE statistics DROP CONSTRAINT statistics_pkey;
ALTER TABLE incremental_dumps DROP CONSTRAINT incremental_dumps_pkey;
ALTER TABLE "user" DROP CONSTRAINT user_pkey;
ALTER TABLE dataset DROP CONSTRAINT dataset_pkey;
ALTER TABLE dataset_class DROP CONSTRAINT dataset_class_pkey;
ALTER TABLE dataset_class_member DROP CONSTRAINT dataset_class_member_pkey;
ALTER TABLE dataset_eval_jobs DROP CONSTRAINT dataset_eval_jobs_pkey;
ALTER TABLE dataset_eval_sets DROP CONSTRAINT dataset_eval_sets_pkey;
ALTER TABLE dataset_snapshot DROP CONSTRAINT dataset_snapshot_pkey;
ALTER TABLE challenge DROP CONSTRAINT challenge_pkey;
ALTER TABLE dataset_eval_challenge DROP CONSTRAINT dataset_eval_challenge_pkey;
ALTER TABLE api_key DROP CONSTRAINT api_key_pkey;
ALTER TABLE feedback DROP CONSTRAINT feedback_pkey;

COMMIT;
