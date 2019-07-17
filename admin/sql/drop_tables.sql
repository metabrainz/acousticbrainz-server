BEGIN;

DROP TABLE IF EXISTS highlevel_model        CASCADE;
DROP TABLE IF EXISTS highlevel_meta         CASCADE;
DROP TABLE IF EXISTS highlevel              CASCADE;
DROP TABLE IF EXISTS model                  CASCADE;
DROP TABLE IF EXISTS lowlevel_json          CASCADE;
DROP TABLE IF EXISTS lowlevel               CASCADE;
DROP TABLE IF EXISTS version                CASCADE;
DROP TABLE IF EXISTS statistics             CASCADE;
DROP TABLE IF EXISTS incremental_dumps      CASCADE;
DROP TABLE IF EXISTS dataset_snapshot       CASCADE;
DROP TABLE IF EXISTS dataset_eval_jobs      CASCADE;
DROP TABLE IF EXISTS dataset_class_member   CASCADE;
DROP TABLE IF EXISTS dataset_class          CASCADE;
DROP TABLE IF EXISTS dataset                CASCADE;
DROP TABLE IF EXISTS dataset_eval_sets      CASCADE;
DROP TABLE IF EXISTS "user"                 CASCADE;
DROP TABLE IF EXISTS api_key                CASCADE;
DROP TABLE IF EXISTS challenge              CASCADE;
DROP TABLE IF EXISTS dataset_eval_challenge CASCADE;
DROP TABLE IF EXISTS feedback               CASCADE;
DROP TABLE IF EXISTS similarity             CASCADE;
DROP TABLE IF EXISTS similarity_metrics     CASCADE;
DROP TABLE IF EXISTS similarity_stats       CASCADE;
DROP TABLE IF EXISTS similarity_eval        CASCADE;

COMMIT;