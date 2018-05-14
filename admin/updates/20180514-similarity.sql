BEGIN;

CREATE EXTENSION IF NOT EXISTS "cube";

DROP TABLE IF EXISTS similarity_highlevel;

CREATE TABLE similarity_highlevel (
  id    INTEGER, -- PK, FK to highlevel_model
  vector CUBE
);

ALTER TABLE similarity_highlevel ADD CONSTRAINT similarity_highlevel_pkey PRIMARY KEY (id);

ALTER TABLE similarity_highlevel
  ADD CONSTRAINT similarity_highlevel_fk_highlevel_model
  FOREIGN KEY (id)
  REFERENCES highlevel_model (id);

CREATE INDEX vector_gist_ndx_similarity_highlevel ON similarity_highlevel USING gist(vector);

COMMIT;
