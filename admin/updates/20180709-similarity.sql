BEGIN;

CREATE EXTENSION IF NOT EXISTS "cube";

CREATE TABLE similarity (
  id INTEGER -- PK, FK to lowlevel
);

ALTER TABLE similarity ADD CONSTRAINT similarity_pkey PRIMARY KEY (id);

ALTER TABLE similarity
  ADD CONSTRAINT similarity_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);


CREATE TABLE similarity_stats (
  metric TEXT,
  means DOUBLE PRECISION[],
  stddevs DOUBLE PRECISION[]
);

ALTER TABLE similarity_stats ADD CONSTRAINT similarity_stats_pkey PRIMARY KEY (metric);

CREATE TABLE similarity_eval (
  user_id INTEGER, -- FK to user
  query_mbid UUID,
  result_mbids UUID[],
  metric TEXT,
  rating SMALLINT,
  suggestion TEXT
);

ALTER TABLE similarity_eval
  ADD CONSTRAINT similarity_eval_fk_user
  FOREIGN KEY (user_id)
  REFERENCES "user" (id);

COMMIT;
