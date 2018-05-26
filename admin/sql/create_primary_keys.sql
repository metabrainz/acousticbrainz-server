BEGIN;

ALTER TABLE lowlevel ADD CONSTRAINT lowlevel_pkey PRIMARY KEY (id);
ALTER TABLE lowlevel_json ADD CONSTRAINT lowlevel_json_pkey PRIMARY KEY (id);
ALTER TABLE highlevel ADD CONSTRAINT highlevel_pkey PRIMARY KEY (id);
ALTER TABLE highlevel_meta ADD CONSTRAINT highlevel_meta_pkey PRIMARY KEY (id);
ALTER TABLE highlevel_model ADD CONSTRAINT highlevel_model_pkey PRIMARY KEY (id);
ALTER TABLE model ADD CONSTRAINT model_pkey PRIMARY KEY (id);
ALTER TABLE version ADD CONSTRAINT version_pkey PRIMARY KEY (id);
ALTER TABLE statistics ADD CONSTRAINT statistics_pkey PRIMARY KEY (name, collected);
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


ALTER TABLE musicbrainz.artist ADD CONSTRAINT artist_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.artist_credit ADD CONSTRAINT artist_credit_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.artist_credit_name ADD CONSTRAINT artist_credit_name_pkey PRIMARY KEY (artist_credit, position);
ALTER TABLE musicbrainz.artist_gid_redirect ADD CONSTRAINT artist_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.area ADD CONSTRAINT area_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.area_type ADD CONSTRAINT area_type_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.recording ADD CONSTRAINT recording_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.recording_gid_redirect ADD CONSTRAINT recording_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.release ADD CONSTRAINT release_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_gid_redirect ADD CONSTRAINT release_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.track ADD CONSTRAINT track_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.track_gid_redirect ADD CONSTRAINT track_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.release_group ADD CONSTRAINT release_group_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_group_gid_redirect ADD CONSTRAINT release_group_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.medium ADD CONSTRAINT medium_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.medium_format ADD CONSTRAINT medium_format_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_status ADD CONSTRAINT release_status_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_group_primary_type ADD CONSTRAINT release_group_primary_type_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.language ADD CONSTRAINT language_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_packaging ADD CONSTRAINT release_packaging_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.script ADD CONSTRAINT script_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.gender ADD CONSTRAINT gender_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.artist_type ADD CONSTRAINT artist_type_pkey PRIMARY KEY (id);

COMMIT;
