BEGIN;

CREATE EXTENSION IF NOT EXISTS "cube";

DROP TABLE IF EXISTS similarity;

CREATE TABLE similarity (
  id    INTEGER, -- PK, FK to lowlevel
  mfcc DOUBLE PRECISION[]
);

ALTER TABLE similarity ADD CONSTRAINT similarity_pkey PRIMARY KEY (id);

ALTER TABLE similarity
  ADD CONSTRAINT similarity_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);

DROP
CREATE INDEX mfcc_ndx_similarity ON similarity USING gist(cube(mfcc));

-- populate data

INSERT INTO similarity (id, mfcc)
  SELECT
    id,
    ARRAY(SELECT jsonb_array_elements_text(data->'lowlevel'->'mfcc'->'mean')::float)
  FROM lowlevel_json;

COMMIT;
