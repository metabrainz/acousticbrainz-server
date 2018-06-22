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


CREATE OR REPLACE FUNCTION vector_bpm(jsonb) RETURNS DOUBLE PRECISION[]
LANGUAGE plpgsql IMMUTABLE
AS
$$
DECLARE temp double precision;
BEGIN
  temp := $1->'rhythm'->'bpm';
  temp := log(2.0, temp::numeric);
  RETURN ARRAY[cos(temp), sin(temp)];
END
$$;

COMMIT;
