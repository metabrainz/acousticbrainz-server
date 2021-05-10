BEGIN;

ALTER TABLE lowlevel DROP CONSTRAINT IF EXISTS lowlevel_pkey;
ALTER TABLE lowlevel_json DROP CONSTRAINT IF EXISTS lowlevel_json_pkey;
ALTER TABLE highlevel DROP CONSTRAINT IF EXISTS highlevel_pkey;
ALTER TABLE highlevel_meta DROP CONSTRAINT IF EXISTS highlevel_meta_pkey;
ALTER TABLE highlevel_model DROP CONSTRAINT IF EXISTS highlevel_model_pkey;
ALTER TABLE model DROP CONSTRAINT IF EXISTS model_pkey;
ALTER TABLE version DROP CONSTRAINT IF EXISTS version_pkey;
ALTER TABLE statistics DROP CONSTRAINT IF EXISTS statistics_pkey;
ALTER TABLE incremental_dumps DROP CONSTRAINT IF EXISTS incremental_dumps_pkey;
ALTER TABLE "user" DROP CONSTRAINT IF EXISTS user_pkey;
ALTER TABLE dataset DROP CONSTRAINT IF EXISTS dataset_pkey;
ALTER TABLE dataset_class DROP CONSTRAINT IF EXISTS dataset_class_pkey;
ALTER TABLE dataset_class_member DROP CONSTRAINT IF EXISTS dataset_class_member_pkey;
ALTER TABLE dataset_eval_jobs DROP CONSTRAINT IF EXISTS dataset_eval_jobs_pkey;
ALTER TABLE dataset_eval_sets DROP CONSTRAINT IF EXISTS dataset_eval_sets_pkey;
ALTER TABLE dataset_snapshot DROP CONSTRAINT IF EXISTS dataset_snapshot_pkey;
ALTER TABLE challenge DROP CONSTRAINT IF EXISTS challenge_pkey;
ALTER TABLE dataset_eval_challenge DROP CONSTRAINT IF EXISTS dataset_eval_challenge_pkey;
ALTER TABLE api_key DROP CONSTRAINT IF EXISTS api_key_pkey;
ALTER TABLE feedback DROP CONSTRAINT IF EXISTS feedback_pkey;

COMMIT;
