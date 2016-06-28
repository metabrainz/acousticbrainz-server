BEGIN;

CREATE TABLE api_key (
  value     TEXT    NOT NULL,
  is_active BOOLEAN NOT NULL         DEFAULT TRUE,
  owner     INTEGER NOT NULL,
  created   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE api_key ADD CONSTRAINT api_key_pkey PRIMARY KEY (value);

ALTER TABLE api_key
  ADD CONSTRAINT api_key_fk_user
  FOREIGN KEY (owner)
  REFERENCES "user" (id);

COMMIT;
