BEGIN;

CREATE TYPE similarity.eval_type AS ENUM ('less similar', 'accurate', 'more similar');

CREATE TABLE similarity.eval_params (
  id            SERIAL, -- PK
  metric        TEXT, -- FK to similarity_metrics
  distance_type TEXT,
  n_trees       INTEGER
);

ALTER TABLE similarity.eval_params ADD CONSTRAINT unique_params_constraint UNIQUE(metric, distance_type, n_trees);
ALTER TABLE similarity.eval_params ADD CONSTRAINT eval_params_pkey PRIMARY KEY (id);

ALTER TABLE similarity.eval_params
  ADD CONSTRAINT eval_params_fk_metric
  FOREIGN KEY (metric)
  REFERENCES similarity.similarity_metrics (metric);


CREATE TABLE similarity.eval_results (
  id          SERIAL, -- PK
  query_id    INTEGER, -- FK to lowlevel
  similar_ids INTEGER[],
  distances   DOUBLE PRECISION[],
  params      INTEGER -- FK to eval_params
);

ALTER TABLE similarity.eval_results ADD CONSTRAINT UNIQUE(query_id, params);
ALTER TABLE similarity.eval_results ADD CONSTRAINT eval_results_pkey PRIMARY KEY (id);

ALTER TABLE similarity.eval_results
  ADD CONSTRAINT eval_results_fk_lowlevel
  FOREIGN KEY (query_id)
  REFERENCES lowlevel (id);

ALTER TABLE similarity.eval_results
  ADD CONSTRAINT eval_results_fk_eval_params
  FOREIGN KEY (params)
  REFERENCES similarity.eval_params (id); 


CREATE TABLE similarity.eval_feedback (
  user_id    INTEGER, -- FK to user
  eval_id   INTEGER, -- FK to eval_results
  result_id  INTEGER,
  rating     similarity.eval_type,
  suggestion TEXT
);

ALTER TABLE similarity.eval_feedback
  ADD CONSTRAINT eval_feedback_fk_user
  FOREIGN KEY (user_id)
  REFERENCES "user" (id);

ALTER TABLE similarity.eval_feedback
  ADD CONSTRAINT eval_feedback_fk_query_id
  FOREIGN KEY (eval_id)
  REFERENCES similarity.eval_results (id);

COMMIT;