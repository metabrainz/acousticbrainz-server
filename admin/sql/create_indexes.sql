BEGIN;

CREATE INDEX gid_ndx_lowlevel ON lowlevel (gid);
CREATE INDEX gid_type_ndx_lowlevel ON lowlevel (gid_type);
CREATE INDEX build_sha1_ndx_lowlevel ON lowlevel (build_sha1);
CREATE INDEX submitted_ndx_lowlevel ON lowlevel (submitted);
CREATE INDEX lossless_ndx_lowlevel ON lowlevel (lossless);

CREATE UNIQUE INDEX data_sha256_ndx_lowlevel_json ON lowlevel_json (data_sha256);

CREATE INDEX mbid_ndx_highlevel ON highlevel (mbid);
CREATE INDEX build_sha1_ndx_highlevel ON highlevel (build_sha1);

-- This should not be unique because the exact same file could be submitted twice
-- and for now we should just store the meta block twice
CREATE INDEX data_sha256_ndx_highlevel_meta ON highlevel_meta (data_sha256);
-- This index should not be unique on data, because it's possible to have the same estimate for
-- two different recordings. Instead map it over data, model, and the id of the item
CREATE UNIQUE INDEX data_sha256_ndx_highlevel_model ON highlevel_model (data_sha256, highlevel, model);
CREATE INDEX model_ndx_highlevel_model ON highlevel_model (model);
CREATE INDEX version_ndx_highlevel_model ON highlevel_model (version);
CREATE INDEX highlevel_ndx_highlevel_model ON highlevel_model (highlevel);

CREATE UNIQUE INDEX lower_musicbrainz_id_ndx_user ON "user" (lower(musicbrainz_id));


CREATE UNIQUE INDEX artist_idx_gid ON musicbrainz.artist (gid);
CREATE INDEX artist_idx_name ON musicbrainz.artist (name);
CREATE INDEX artist_idx_sort_name ON musicbrainz.artist (sort_name);
CREATE INDEX artist_idx_area ON musicbrainz.artist (area);
CREATE UNIQUE INDEX artist_idx_null_comment ON musicbrainz.artist (name) WHERE comment IS NULL;
CREATE UNIQUE INDEX artist_idx_uniq_name_comment ON musicbrainz.artist (name, comment) WHERE comment IS NOT NULL;

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

COMMIT;