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

CREATE INDEX collected_ndx_statistics ON statistics (collected);
CREATE INDEX collected_hour_ndx_statistics ON statistics (date_part('hour'::text, timezone('UTC'::text, collected)));

CREATE INDEX submission_offset_ndx_lowlevel ON lowlevel (submission_offset);

COMMIT;
