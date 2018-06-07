BEGIN;

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
