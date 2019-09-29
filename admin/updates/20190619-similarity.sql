BEGIN;

CREATE SCHEMA similarity;

CREATE TABLE similarity.similarity (
  id          INTEGER, -- PK, FK to lowlevel
  mfccs       DOUBLE PRECISION[] NOT NULL,
  mfccsw      DOUBLE PRECISION[] NOT NULL,
  gfccs       DOUBLE PRECISION[] NOT NULL,
  gfccsw      DOUBLE PRECISION[] NOT NULL,
  key         DOUBLE PRECISION[] NOT NULL,
  bpm         DOUBLE PRECISION[] NOT NULL,
  onsetrate   DOUBLE PRECISION[] NOT NULL,
  moods       DOUBLE PRECISION[] NOT NULL,
  instruments DOUBLE PRECISION[] NOT NULL,
  dortmund    DOUBLE PRECISION[] NOT NULL,
  rosamerica  DOUBLE PRECISION[] NOT NULL,
  tzanetakis  DOUBLE PRECISION[] NOT NULL
);

ALTER TABLE similarity.similarity
  ADD CONSTRAINT similarity_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);

CREATE TABLE similarity.similarity_metrics (
  metric TEXT, -- PK
  is_hybrid BOOLEAN,
  description TEXT,
  category TEXT
);

ALTER TABLE similarity.similarity_metrics ADD CONSTRAINT similarity_metrics_pkey PRIMARY KEY (metric);
-- Add base metrics when db is initialized, before similarity stats are computed
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('mfccs', 'FALSE', 'MFCCs', 'timbre');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('mfccsw', 'FALSE', 'MFCCs (weighted)', 'timbre');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('gfccs', 'FALSE', 'GFCCs', 'timbre');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('gfccsw', 'FALSE', 'GFCCs (weighted)', 'timbre');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('key', 'FALSE', 'Key/Scale', 'rhythm');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('bpm', 'FALSE', 'BPM', 'rhythm');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('onsetrate', 'FALSE', 'MFCCs', 'timbre');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('moods', 'FALSE', 'Moods', 'high-level');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('instruments', 'FALSE', 'Instruments', 'high-level');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('dortmund','FALSE', 'Genre (dortmund model)', 'high-level');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('rosamerica', 'FALSE', 'Genre (rosamerica model)', 'high-level');
INSERT INTO similarity.similarity_metrics (metric, is_hybrid, description, category) VALUES ('tzanetakis', 'FALSE', 'Genre (tzanetakis model)', 'high-level');


CREATE TABLE similarity.similarity_stats (
  metric TEXT,  -- FK to metric
  means DOUBLE PRECISION[],
  stddevs DOUBLE PRECISION[]
);

ALTER TABLE similarity.similarity_stats ADD CONSTRAINT similarity_stats_pkey PRIMARY KEY (metric);

ALTER TABLE similarity.similarity_stats
  ADD CONSTRAINT similarity_stats_fk_metric
  FOREIGN KEY (metric)
  REFERENCES similarity.similarity_metrics (metric);

COMMIT;
