BEGIN;

CREATE EXTENSION IF NOT EXISTS "cube";

DROP TABLE IF EXISTS similarity;

CREATE TABLE similarity (
  -- lowlevel
  id    INTEGER, -- PK, FK to lowlevel
  mfccs DOUBLE PRECISION[], -- 13
  mfccs_w DOUBLE PRECISION[], -- 13
  bpm DOUBLE PRECISION[], -- 2
  key DOUBLE PRECISION[], -- 2
  -- highlevel
  moods DOUBLE PRECISION[], -- 5
  instruments DOUBLE PRECISION[], -- 3
  genres_dortmund DOUBLE PRECISION[], -- 9
  genres_rosamerica DOUBLE PRECISION[], -- 8
  genres_tzenakis DOUBLE PRECISION[] -- 10
);

ALTER TABLE similarity ADD CONSTRAINT similarity_pkey PRIMARY KEY (id);

ALTER TABLE similarity
  ADD CONSTRAINT similarity_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);

CREATE INDEX mfccs_ndx_similarity ON similarity USING gist(cube(mfccs));
CREATE INDEX bpm_ndx_similarity ON similarity USING gist(cube(bpm));
CREATE INDEX key_ndx_similarity ON similarity USING gist(cube(key));
CREATE INDEX moods_ndx_similarity ON similarity USING gist(cube(moods));
CREATE INDEX instruments_ndx_similarity ON similarity USING gist(cube(instruments));
CREATE INDEX genres_dortmund_ndx_similarity ON similarity USING gist(cube(genres_dortmund));
CREATE INDEX genres_rosamerica_ndx_similarity ON similarity USING gist(cube(genres_rosamerica));
CREATE INDEX genres_tzenakis_ndx_similarity ON similarity USING gist(cube(genres_tzenakis));

-- hybrid metrics
CREATE INDEX bpm_key_ndx_similarity ON similarity USING gist(cube(array_cat(bpm, key)));


-- populate data

-- INSERT INTO similarity (id, mfcc)
--   SELECT
--     id,
--     ARRAY(SELECT jsonb_array_elements_text(data->'lowlevel'->'mfcc'->'mean')::float)
--   FROM lowlevel_json;

COMMIT;
