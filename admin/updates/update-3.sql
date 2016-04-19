BEGIN;

CREATE TABLE challenge (
  id         UUID,
  name       TEXT                     NOT NULL,
  creator    INTEGER                  NOT NULL,
  created    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  start_time TIMESTAMP WITH TIME ZONE NOT NULL,
  end_time   TIMESTAMP WITH TIME ZONE NOT NULL
);

ALTER TABLE challenge ADD CONSTRAINT challenge_pkey PRIMARY KEY (id);

ALTER TABLE challenge
  ADD CONSTRAINT challenge_fk_user
  FOREIGN KEY (creator)
  REFERENCES "user" (id);

COMMIT;
