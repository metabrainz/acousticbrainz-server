BEGIN;

CREATE TABLE similarity_eval (
  user_id INTEGER, -- FK to user
  query_mbid UUID,
  result_mbids UUID[],
  metric TEXT, -- FK to metric
  rating SMALLINT, -- 1 through 5, 1 being this should be much more similar, 5 being much less similar, 3 similarity is ranked appropriately
  suggestion TEXT
);

ALTER TABLE similarity_eval
  ADD CONSTRAINT similarity_eval_fk_user
  FOREIGN KEY (user_id)
  REFERENCES "user" (id);

ALTER TABLE similarity_eval
  ADD CONSTRAINT similarity_eval_fk_metric
  FOREIGN KEY (metric)
  REFERENCES similarity_metrics (metric);

COMMIT;