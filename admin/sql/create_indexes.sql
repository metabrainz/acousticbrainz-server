BEGIN;

CREATE INDEX mbid_ndx_lowlevel ON lowlevel (mbid);
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

CREATE UNIQUE INDEX lower_musicbrainz_id_ndx_user ON "user" (lower(musicbrainz_id));

COMMIT;
