BEGIN;

CREATE TABLE feedback (
  user_id            INTEGER, -- PK, FK to user
  highlevel_model_id INTEGER, -- PK, FK to highlevel_model
  correct            BOOLEAN NOT NULL,
  suggestion         TEXT
);


ALTER TABLE feedback ADD CONSTRAINT feedback_pkey PRIMARY KEY (user_id, highlevel_model_id);


ALTER TABLE feedback
  ADD CONSTRAINT feedback_fk_highlevel_model
  FOREIGN KEY (highlevel_model_id)
  REFERENCES highlevel_model (id);

ALTER TABLE feedback
  ADD CONSTRAINT feedback_fk_user
  FOREIGN KEY (user_id)
  REFERENCES "user" (id);

COMMIT;
