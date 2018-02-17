BEGIN;

ALTER TABLE "dataset_eval_jobs" ADD COLUMN c_value VARCHAR;
ALTER TABLE "dataset_eval_jobs" ADD COLUMN gamma_value VARCHAR;
ALTER TABLE "dataset_eval_jobs" ADD COLUMN preprocessing_values VARCHAR;

COMMIT;