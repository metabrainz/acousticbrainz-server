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
  ADD CONSTRAINT dataset_eval_jobs_fk_dataset_snapshot
  FOREIGN KEY (snapshot_id)
  REFERENCES dataset_snapshot (id);

ALTER TABLE dataset_eval_jobs
  ADD CONSTRAINT dataset_eval_jobs_fk_training_snapshot
  FOREIGN KEY (training_snapshot)
  REFERENCES dataset_eval_sets (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_eval_jobs
  ADD CONSTRAINT dataset_eval_jobs_fk_testing_snapshot
  FOREIGN KEY (testing_snapshot)
  REFERENCES dataset_eval_sets (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_snapshot
  ADD CONSTRAINT dataset_id_fk_dataset
  FOREIGN KEY (dataset_id)
  REFERENCES dataset (id);

ALTER TABLE challenge
  ADD CONSTRAINT challenge_fk_dataset_snapshot
  FOREIGN KEY (validation_snapshot)
  REFERENCES dataset_snapshot (id);

ALTER TABLE challenge
  ADD CONSTRAINT challenge_fk_user
  FOREIGN KEY (creator)
  REFERENCES "user" (id);

ALTER TABLE dataset_eval_challenge
  ADD CONSTRAINT dataset_eval_challenge_fk_dataset_eval_job
  FOREIGN KEY (dataset_eval_job)
  REFERENCES dataset_eval_jobs (id);

ALTER TABLE dataset_eval_challenge
  ADD CONSTRAINT dataset_eval_challenge_fk_challenge
  FOREIGN KEY (challenge_id)
  REFERENCES challenge (id);

ALTER TABLE api_key
  ADD CONSTRAINT api_key_fk_user
  FOREIGN KEY (owner)
  REFERENCES "user" (id);

ALTER TABLE feedback
  ADD CONSTRAINT feedback_fk_highlevel_model
  FOREIGN KEY (highlevel_model_id)
  REFERENCES highlevel_model (id);

ALTER TABLE feedback
  ADD CONSTRAINT feedback_fk_user
  FOREIGN KEY (user_id)
  REFERENCES "user" (id);


ALTER TABLE musicbrainz.artist
  ADD CONSTRAINT artist_fk_type
  FOREIGN KEY (type)
  REFERENCES musicbrainz.artist_type(id);

ALTER TABLE musicbrainz.artist
  ADD CONSTRAINT artist_fk_area
  FOREIGN KEY (area)
  REFERENCES musicbrainz.area(id);

ALTER TABLE musicbrainz.artist
  ADD CONSTRAINT artist_fk_gender
  FOREIGN KEY (gender)
  REFERENCES musicbrainz.gender(id);

ALTER TABLE musicbrainz.artist
  ADD CONSTRAINT artist_fk_begin_area
  FOREIGN KEY (begin_area)
  REFERENCES musicbrainz.area(id);

ALTER TABLE musicbrainz.artist
  ADD CONSTRAINT artist_fk_end_area
  FOREIGN KEY (end_area)
  REFERENCES musicbrainz.area(id);

ALTER TABLE musicbrainz.artist_credit_name
  ADD CONSTRAINT artist_credit_name_fk_artist_credit
  FOREIGN KEY (artist_credit)
  REFERENCES musicbrainz.artist_credit(id)
  ON DELETE CASCADE;

ALTER TABLE musicbrainz.artist_credit_name
  ADD CONSTRAINT artist_credit_name_fk_artist
  FOREIGN KEY (artist)
  REFERENCES musicbrainz.artist(id)
  ON DELETE CASCADE;

ALTER TABLE musicbrainz.artist_gid_redirect
  ADD CONSTRAINT artist_gid_redirect_fk_new_id
  FOREIGN KEY (new_id)
  REFERENCES musicbrainz.artist(id);

ALTER TABLE musicbrainz.area
  ADD CONSTRAINT area_fk_type
  FOREIGN KEY (type)
  REFERENCES musicbrainz.area_type(id);

ALTER TABLE musicbrainz.area_type
  ADD CONSTRAINT area_type_fk_parent
  FOREIGN KEY (parent)
REFERENCES musicbrainz.area_type(id);

ALTER TABLE musicbrainz.recording
  ADD CONSTRAINT recording_fk_artist_credit
  FOREIGN KEY (artist_credit)
  REFERENCES musicbrainz.artist_credit(id);

ALTER TABLE musicbrainz.recording_gid_redirect
  ADD CONSTRAINT recording_gid_redirect_fk_new_id
  FOREIGN KEY (new_id)
  REFERENCES musicbrainz.recording(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_artist_credit
  FOREIGN KEY (artist_credit)
  REFERENCES musicbrainz.artist_credit(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_release_group
  FOREIGN KEY (release_group)
  REFERENCES musicbrainz.release_group(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_status
  FOREIGN KEY (status)
  REFERENCES musicbrainz.release_status(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_packaging
  FOREIGN KEY (packaging)
  REFERENCES musicbrainz.release_packaging(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_language
  FOREIGN KEY (language)
  REFERENCES musicbrainz.language(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_script
  FOREIGN KEY (script)
  REFERENCES musicbrainz.script(id);

ALTER TABLE musicbrainz.release_gid_redirect
  ADD CONSTRAINT release_gid_redirect_fk_new_id
  FOREIGN KEY (new_id)
  REFERENCES musicbrainz.release(id);

ALTER TABLE musicbrainz.track
  ADD CONSTRAINT track_fk_recording
  FOREIGN KEY (recording)
  REFERENCES musicbrainz.recording(id);

ALTER TABLE musicbrainz.track
  ADD CONSTRAINT track_fk_medium
  FOREIGN KEY (medium)
  REFERENCES musicbrainz.medium(id);

ALTER TABLE musicbrainz.track
  ADD CONSTRAINT track_fk_artist_credit
  FOREIGN KEY (artist_credit)
  REFERENCES musicbrainz.artist_credit(id);

ALTER TABLE musicbrainz.track_gid_redirect
  ADD CONSTRAINT track_gid_redirect_fk_new_id
  FOREIGN KEY (new_id)
  REFERENCES musicbrainz.track(id);

ALTER TABLE musicbrainz.release_group
  ADD CONSTRAINT release_group_fk_artist_credit
  FOREIGN KEY (artist_credit)
  REFERENCES musicbrainz.artist_credit(id);

ALTER TABLE musicbrainz.release_group
  ADD CONSTRAINT release_group_fk_type
  FOREIGN KEY (type)
  REFERENCES musicbrainz.release_group_primary_type(id);

ALTER TABLE musicbrainz.release_group_primary_type
  ADD CONSTRAINT release_group_primary_type_fk_parent
  FOREIGN KEY (parent)
  REFERENCES musicbrainz.release_group_primary_type;

ALTER TABLE musicbrainz.release_group_gid_redirect
  ADD CONSTRAINT release_group_gid_redirect_fk_new_id
  FOREIGN KEY (new_id)
  REFERENCES musicbrainz.release_group(id);

ALTER TABLE musicbrainz.medium
  ADD CONSTRAINT medium_fk_release
  FOREIGN KEY (release)
  REFERENCES musicbrainz.release(id);

ALTER TABLE musicbrainz.medium
  ADD CONSTRAINT medium_fk_format
  FOREIGN KEY (format)
  REFERENCES musicbrainz.medium_format(id);

ALTER TABLE musicbrainz.medium_format
  ADD CONSTRAINT medium_format_fk_parent
  FOREIGN KEY (parent)
REFERENCES musicbrainz.medium_format(id);

ALTER TABLE musicbrainz.release_status
  ADD CONSTRAINT release_status_fk_parent
  FOREIGN KEY (parent)
  REFERENCES musicbrainz.release_status(id);

ALTER TABLE musicbrainz.release_packaging
  ADD CONSTRAINT release_packaging_fk_parent
  FOREIGN KEY (parent)
  REFERENCES musicbrainz.release_packaging(id);

ALTER TABLE musicbrainz.gender
  ADD CONSTRAINT gender_fk_parent
  FOREIGN KEY (parent)
  REFERENCES musicbrainz.gender(id);

ALTER TABLE musicbrainz.artist_type
  ADD CONSTRAINT artist_type_fk_parent
  FOREIGN KEY (parent)
  REFERENCES musicbrainz.artist_type(id);

COMMIT;
