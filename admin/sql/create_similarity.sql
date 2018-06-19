BEGIN;

CREATE EXTENSION IF NOT EXISTS "cube";

DROP TABLE IF EXISTS similarity;

CREATE TABLE similarity (
  id INTEGER -- PK, FK to lowlevel
);

ALTER TABLE similarity ADD CONSTRAINT similarity_pkey PRIMARY KEY (id);

ALTER TABLE similarity
  ADD CONSTRAINT similarity_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);


DROP TABLE IF EXISTS similarity_stats;

CREATE TABLE similarity_stats (
  metric TEXT,
  means DOUBLE PRECISION[],
  stddevs DOUBLE PRECISION[]
);

ALTER TABLE similarity_stats ADD CONSTRAINT similarity_stats_pkey PRIMARY KEY (metric);

COMMIT;
