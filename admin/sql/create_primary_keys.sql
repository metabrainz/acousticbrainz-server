BEGIN;

ALTER TABLE lowlevel ADD CONSTRAINT lowlevel_pkey PRIMARY KEY (id);
ALTER TABLE lowlevel_json ADD CONSTRAINT lowlevel_json_pkey PRIMARY KEY (id);
ALTER TABLE highlevel ADD CONSTRAINT highlevel_pkey PRIMARY KEY (id);
ALTER TABLE highlevel_meta ADD CONSTRAINT highlevel_meta_pkey PRIMARY KEY (id);
ALTER TABLE highlevel_model ADD CONSTRAINT highlevel_model_pkey PRIMARY KEY (id);
ALTER TABLE model ADD CONSTRAINT model_pkey PRIMARY KEY (id);
ALTER TABLE version ADD CONSTRAINT version_pkey PRIMARY KEY (id);
ALTER TABLE statistics ADD CONSTRAINT statistics_pkey PRIMARY KEY (collected);
ALTER TABLE incremental_dumps ADD CONSTRAINT incremental_dumps_pkey PRIMARY KEY (id);
ALTER TABLE "user" ADD CONSTRAINT user_pkey PRIMARY KEY (id);
ALTER TABLE dataset ADD CONSTRAINT dataset_pkey PRIMARY KEY (id);
ALTER TABLE dataset_class ADD CONSTRAINT dataset_class_pkey PRIMARY KEY (id);
ALTER TABLE dataset_class_member ADD CONSTRAINT dataset_class_member_pkey PRIMARY KEY (class, mbid);
ALTER TABLE dataset_eval_jobs ADD CONSTRAINT dataset_eval_jobs_pkey PRIMARY KEY (id);
ALTER TABLE dataset_eval_sets ADD CONSTRAINT dataset_eval_sets_pkey PRIMARY KEY (id);
ALTER TABLE dataset_snapshot ADD CONSTRAINT dataset_snapshot_pkey PRIMARY KEY (id);
ALTER TABLE challenge ADD CONSTRAINT challenge_pkey PRIMARY KEY (id);
ALTER TABLE dataset_eval_challenge ADD CONSTRAINT dataset_eval_challenge_pkey PRIMARY KEY (dataset_eval_job, challenge_id);
ALTER TABLE api_key ADD CONSTRAINT api_key_pkey PRIMARY KEY (value);
ALTER TABLE feedback ADD CONSTRAINT feedback_pkey PRIMARY KEY (user_id, highlevel_model_id);
ALTER TABLE similarity.similarity_metrics ADD CONSTRAINT similarity_metrics_pkey PRIMARY KEY (metric);
ALTER TABLE similarity.similarity_stats ADD CONSTRAINT similarity_stats_pkey PRIMARY KEY (metric);
ALTER TABLE similarity.eval_params ADD CONSTRAINT eval_params_pkey PRIMARY KEY (id);
ALTER TABLE similarity.eval_results ADD CONSTRAINT eval_results_pkey PRIMARY KEY (id);

COMMIT;
