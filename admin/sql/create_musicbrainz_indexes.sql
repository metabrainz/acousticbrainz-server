BEGIN;

CREATE UNIQUE INDEX artist_idx_gid ON musicbrainz.artist (gid);
CREATE INDEX artist_idx_name ON musicbrainz.artist (name);
CREATE INDEX artist_idx_sort_name ON musicbrainz.artist (sort_name);
CREATE INDEX artist_idx_area ON musicbrainz.artist (area);
CREATE INDEX artist_idx_begin_area ON musicbrainz.artist (begin_area);
CREATE INDEX artist_idx_end_area ON musicbrainz.artist (end_area);

CREATE UNIQUE INDEX artist_idx_null_comment ON musicbrainz.artist (name) WHERE comment IS NULL;
CREATE UNIQUE INDEX artist_idx_uniq_name_comment ON musicbrainz.artist (name, comment) WHERE comment IS NOT NULL;

CREATE UNIQUE INDEX area_type_idx_gid ON musicbrainz.area_type (gid);

CREATE UNIQUE INDEX area_idx_gid ON musicbrainz.area (gid);
CREATE INDEX area_idx_name ON musicbrainz.area (name);

CREATE INDEX artist_credit_name_idx_artist ON musicbrainz.artist_credit_name (artist);

CREATE UNIQUE INDEX recording_idx_gid ON musicbrainz.recording (gid);
CREATE INDEX recording_idx_name ON musicbrainz.recording (name);
CREATE INDEX recording_idx_artist_credit ON musicbrainz.recording (artist_credit);

CREATE UNIQUE INDEX release_idx_gid ON musicbrainz.release (gid);
CREATE INDEX release_idx_name ON musicbrainz.release (name);
CREATE INDEX release_idx_release_group ON musicbrainz.release (release_group);
CREATE INDEX release_idx_artist_credit ON musicbrainz.release (artist_credit);

CREATE UNIQUE INDEX track_idx_gid ON musicbrainz.track (gid);
CREATE INDEX track_idx_recording ON musicbrainz.track (recording);
CREATE INDEX track_idx_name ON musicbrainz.track (name);
CREATE INDEX track_idx_artist_credit ON musicbrainz.track (artist_credit);

CREATE INDEX artist_gid_redirect_idx_new_id ON musicbrainz.artist_gid_redirect (new_id);

CREATE INDEX recording_gid_redirect_idx_new_id ON musicbrainz.recording_gid_redirect (new_id);

CREATE INDEX release_gid_redirect_idx_new_id ON musicbrainz.release_gid_redirect (new_id);

CREATE INDEX release_group_gid_redirect_idx_new_id ON musicbrainz.release_group_gid_redirect (new_id);

CREATE INDEX track_gid_redirect_idx_new_id ON musicbrainz.track_gid_redirect (new_id);

CREATE UNIQUE INDEX release_group_idx_gid ON musicbrainz.release_group (gid);
CREATE INDEX release_group_idx_name ON musicbrainz.release_group (name);
CREATE INDEX release_group_idx_artist_credit ON musicbrainz.release_group (artist_credit);

CREATE INDEX medium_idx_track_count ON musicbrainz.medium (track_count);

CREATE UNIQUE INDEX medium_format_idx_gid ON musicbrainz.medium_format (gid);

CREATE UNIQUE INDEX release_status_idx_gid ON musicbrainz.release_status (gid);

CREATE UNIQUE INDEX language_idx_iso_code_2b ON musicbrainz.language (iso_code_2b);
CREATE UNIQUE INDEX language_idx_iso_code_2t ON musicbrainz.language (iso_code_2t);
CREATE UNIQUE INDEX language_idx_iso_code_1 ON musicbrainz.language (iso_code_1);
CREATE UNIQUE INDEX language_idx_iso_code_3 ON musicbrainz.language (iso_code_3);

CREATE UNIQUE INDEX release_packaging_idx_gid ON musicbrainz.release_packaging (gid);

CREATE UNIQUE INDEX script_idx_iso_code ON musicbrainz.script (iso_code);

CREATE UNIQUE INDEX gender_idx_gid ON musicbrainz.gender (gid);

CREATE UNIQUE INDEX artist_type_idx_gid ON musicbrainz.artist_type (gid);

COMMIT;
