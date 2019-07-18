BEGIN;

CREATE TYPE eval_type AS ENUM ('less similar', 'accurate', 'more similar');

CREATE TABLE eval_params (
  id            SERIAL, -- PK
  metric        TEXT, -- FK to similarity_metrics
  distance_type TEXT,
  n_trees       INTEGER
);

ALTER TABLE eval_params ADD CONSTRAINT eval_params_pkey PRIMARY KEY (id);

ALTER TABLE eval_params
  ADD CONSTRAINT eval_params_fk_metric
  FOREIGN KEY (metric)
  REFERENCES similarity_metrics (metric);


CREATE TABLE eval_results (
  id          SERIAL, -- PK
  query_id    INTEGER, -- FK to lowlevel
  similar_ids INTEGER[],
  distances   DOUBLE PRECISION[],
  params      INTEGER -- FK to eval_params
);

ALTER TABLE eval_results ADD CONSTRAINT eval_results_pkey PRIMARY KEY (id);

ALTER TABLE eval_results
  ADD CONSTRAINT eval_results_fk_lowlevel
  FOREIGN KEY (query_id)
  REFERENCES lowlevel (id);

ALTER TABLE eval_results
  ADD CONSTRAINT eval_results_fk_eval_params
  FOREIGN KEY (params)
  REFERENCES eval_params (id); 


CREATE TABLE eval_feedback (
  user_id    INTEGER, -- FK to user
  query_id   INTEGER, -- FK to eval_results
  result_id  INTEGER,
  rating     eval_type,
  suggestion TEXT
);

ALTER TABLE eval_feedback
  ADD CONSTRAINT eval_feedback_fk_user
  FOREIGN KEY (user_id)
  REFERENCES "user" (id);

ALTER TABLE eval_feedback
  ADD CONSTRAINT eval_feedback_fk_query_id
  FOREIGN KEY (query_id)
  REFERENCES eval_results (id);

COMMIT;