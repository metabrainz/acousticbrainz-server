BEGIN;

CREATE TABLE lowlevel (
  id          SERIAL,
  mbid        UUID NOT NULL,
  build_sha1  TEXT NOT NULL,
  lossless    BOOLEAN                  DEFAULT 'n',
  submitted   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE lowlevel_json (
  id          INTEGER, -- FK to lowlevel.id
  data        JSONB    NOT NULL,
  data_sha256 CHAR(64) NOT NULL,
  version     INTEGER  NOT NULL-- FK to version.id
);

CREATE TABLE highlevel (
  id         INTEGER, -- FK to lowlevel.id
  mbid       UUID    NOT NULL,
  build_sha1 TEXT    NOT NULL,
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE highlevel_meta (
  id          INTEGER, -- FK to highlevel.id
  data        JSONB    NOT NULL,
  data_sha256 CHAR(64) NOT NULL
);

CREATE TABLE highlevel_model (
  id          SERIAL,
  highlevel   INTEGER, -- FK to highlevel.id
  data        JSONB    NOT NULL,
  data_sha256 CHAR(64) NOT NULL,
  model       INTEGER  NOT NULL, -- FK to model.id
  version     INTEGER  NOT NULL, -- FK to version.id
  created     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE version (
  id          SERIAL,
  data        JSONB    NOT NULL,
  data_sha256 CHAR(64) NOT NULL,
  type        version_type NOT NULL,
  created     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE model (
  id            SERIAL,
  model         TEXT         NOT NULL,
  model_version TEXT         NOT NULL,
  date          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  status        model_status NOT NULL    DEFAULT 'hidden'
);

CREATE TABLE statistics (
  collected TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  name      TEXT                     NOT NULL,
  value     INTEGER                  NOT NULL
);

CREATE TABLE incremental_dumps (
  id      SERIAL,
  created TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE "user" (
  id             SERIAL,
  created        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  musicbrainz_id VARCHAR
);
ALTER TABLE "user" ADD CONSTRAINT user_musicbrainz_id_key UNIQUE (musicbrainz_id);

CREATE TABLE dataset (
  id          UUID,
  name        VARCHAR NOT NULL,
  description TEXT,
  author      INT NOT NULL, -- FK to user
  public      BOOLEAN NOT NULL,
  created     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_edited TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE dataset_class (
  id          SERIAL,
  name        VARCHAR NOT NULL,
  description TEXT,
  dataset     UUID    NOT NULL -- FK to dataset
);

CREATE TABLE dataset_class_member (
  class INT, -- FK to class
  mbid  UUID
);

CREATE TABLE dataset_eval_jobs (
  id                UUID,
  dataset_id        UUID                     NOT NULL,
  status            eval_job_status          NOT NULL DEFAULT 'pending',
  status_msg        VARCHAR,
  options           JSONB,
  training_snapshot INT,                     -- FK to dataset_snapshot
  testing_snapshot  INT,                     -- FK to dataset_snapshot
  created           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  result            JSONB
);

CREATE TABLE dataset_snapshot (
  id   SERIAL,
  data JSONB NOT NULL
);

COMMIT;
