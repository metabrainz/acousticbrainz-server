BEGIN;

CREATE TABLE lowlevel (
  id          SERIAL,
  mbid        UUID NOT NULL,
  build_sha1  TEXT NOT NULL,
  lossless    BOOLEAN                  DEFAULT 'n',
  data        JSON NOT NULL,
  submitted   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  data_sha256 TEXT NOT NULL
);

CREATE TABLE highlevel (
  id         INTEGER, -- FK to lowlevel.id
  mbid       UUID    NOT NULL,
  build_sha1 TEXT    NOT NULL,
  data       INTEGER NOT NULL, -- FK to highlevel_json.data
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE highlevel_json (
  id          SERIAL,
  data        JSON     NOT NULL,
  data_sha256 CHAR(64) NOT NULL
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
  id          SERIAL,
  name        VARCHAR NOT NULL,
  description TEXT,
  owner       INT, -- FK to user
  created     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE class (
  id          SERIAL,
  name        VARCHAR NOT NULL,
  description TEXT,
  dataset     INT -- FK to dataset
);

CREATE TABLE class_member (
  class    INT, -- FK to class
  lowlevel INT -- FK to lowlevel
);

COMMIT;
