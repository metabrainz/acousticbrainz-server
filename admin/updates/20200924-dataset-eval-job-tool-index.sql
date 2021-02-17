BEGIN;
CREATE INDEX training_tool_dataset_eval_jobs ON dataset_eval_jobs((options->>'training_tool'));
COMMIT;