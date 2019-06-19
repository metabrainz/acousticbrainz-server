BEGIN;

-- CREATE EXTENSION IF NOT EXISTS "cube"; -- Only required for postgres similarity


CREATE TABLE similarity (
  id INTEGER -- PK, FK to lowlevel
);

ALTER TABLE similarity ADD CONSTRAINT similarity_pkey PRIMARY KEY (id);

ALTER TABLE similarity
  ADD CONSTRAINT similarity_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);


CREATE TABLE similarity_metrics (
  metric 	  TEXT, -- PK
  is_hybrid   BOOLEAN,
  description TEXT,
  category    TEXT,
  visible     BOOLEAN
);

ALTER TABLE similarity_metrics ADD CONSTRAINT similarity_metrics_pkey PRIMARY KEY (metric);


CREATE TABLE similarity_stats (
  metric  TEXT,  -- FK to metric
  means   DOUBLE PRECISION[],
  stddevs DOUBLE PRECISION[]
);

ALTER TABLE similarity_stats ADD CONSTRAINT similarity_stats_pkey PRIMARY KEY (metric);

ALTER TABLE similarity_stats
  ADD CONSTRAINT similarity_stats_fk_metric
  FOREIGN KEY (metric)
  REFERENCES similarity_metrics (metric);

COMMIT;