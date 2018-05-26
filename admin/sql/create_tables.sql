BEGIN;

CREATE TABLE lowlevel (
  id         SERIAL,
  gid        UUID      NOT NULL,
  build_sha1 TEXT      NOT NULL,
  lossless   BOOLEAN                  DEFAULT 'n',
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  gid_type   gid_type  NOT NULL
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
  musicbrainz_id VARCHAR,
  admin          BOOLEAN NOT NULL         DEFAULT FALSE,
  gdpr_agreed    TIMESTAMP WITH TIME ZONE
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

CREATE TABLE dataset_snapshot (
  id         UUID, -- PK
  dataset_id UUID, -- FK to dataset
  data       JSONB                    NOT NULL,
  created    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE dataset_eval_jobs (
  id                UUID,
  snapshot_id       UUID                     NOT NULL, -- FK to snapshot
  status            eval_job_status          NOT NULL DEFAULT 'pending',
  status_msg        VARCHAR,
  options           JSONB,
  training_snapshot INT,                     -- FK to dataset_eval_sets
  testing_snapshot  INT,                     -- FK to dataset_eval_sets
  created           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  result            JSONB,
  eval_location     eval_location_type       NOT NULL DEFAULT 'local'
);

CREATE TABLE dataset_eval_sets (
  id   SERIAL,
  data JSONB NOT NULL
);

CREATE TABLE challenge (
  id                  UUID,
  name                TEXT                     NOT NULL,
  validation_snapshot UUID                     NOT NULL, -- FK to dataset_snapshot
  creator             INTEGER                  NOT NULL, -- FK to user
  created             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  start_time          TIMESTAMP WITH TIME ZONE NOT NULL,
  end_time            TIMESTAMP WITH TIME ZONE NOT NULL,
  classes             TEXT                     NOT NULL,
  concluded           BOOLEAN                  NOT NULL DEFAULT FALSE
);

CREATE TABLE dataset_eval_challenge (
  dataset_eval_job UUID, -- PK, FK to dataset_eval_jobs
  challenge_id     UUID, -- PK, FK to challenge
  result           JSONB
);

CREATE TABLE api_key (
  value     TEXT    NOT NULL,
  is_active BOOLEAN NOT NULL         DEFAULT TRUE,
  owner     INTEGER NOT NULL,
  created   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE feedback (
  user_id            INTEGER, -- PK, FK to user
  highlevel_model_id INTEGER, -- PK, FK to highlevel_model
  correct            BOOLEAN NOT NULL,
  suggestion         TEXT
);


CREATE SCHEMA IF NOT EXISTS musicbrainz;

CREATE TABLE musicbrainz.artist (
  id                  SERIAL,
  gid                 UUID NOT NULL,
  name                VARCHAR NOT NULL,
  sort_name           VARCHAR NOT NULL,
  begin_date_year     SMALLINT,
  begin_date_month    SMALLINT,
  begin_date_day      SMALLINT,
  end_date_year       SMALLINT,
  end_date_month      SMALLINT,
  end_date_day        SMALLINT,
  type                INTEGER, -- references artist_type.id
  area                INTEGER, -- references area.id
  gender              INTEGER, -- references gender.id
  comment             VARCHAR(255) NOT NULL DEFAULT '',
  edits_pending       INTEGER NOT NULL DEFAULT 0 CHECK (edits_pending >= 0),
  last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ended               BOOLEAN NOT NULL DEFAULT FALSE
    CONSTRAINT artist_ended_check CHECK (
      (
        -- If any end date fields are not null, then ended must be true
        (end_date_year IS NOT NULL OR
         end_date_month IS NOT NULL OR
         end_date_day IS NOT NULL) AND
        ended = TRUE
      ) OR (
        -- Otherwise, all end date fields must be null
        (end_date_year IS NULL AND
         end_date_month IS NULL AND
         end_date_day IS NULL)
      )
    ),
  begin_area          INTEGER, -- references area.id
  end_area            INTEGER -- references area.id
);

CREATE TABLE musicbrainz.artist_credit (
  id                  SERIAL,
  name                VARCHAR NOT NULL,
  artist_count        SMALLINT NOT NULL,
  ref_count           INTEGER DEFAULT 0,
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE musicbrainz.artist_credit_name (
  artist_credit       INTEGER NOT NULL, -- PK, references artist_credit.id CASCADE
  position            SMALLINT NOT NULL, -- PK
  artist              INTEGER NOT NULL, -- references artist.id CASCADE
  name                VARCHAR NOT NULL,
  join_phrase         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE musicbrainz.artist_gid_redirect (
  gid                 UUID NOT NULL, -- PK
  new_id              INTEGER NOT NULL, -- references artist.id
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE musicbrainz.area (
  id                  SERIAL, -- PK
  gid                 uuid NOT NULL,
  name                VARCHAR NOT NULL,
  type                INTEGER, -- references area_type.id
  edits_pending       INTEGER NOT NULL DEFAULT 0 CHECK (edits_pending >=0),
  last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  begin_date_year     SMALLINT,
  begin_date_month    SMALLINT,
  begin_date_day      SMALLINT,
  end_date_year       SMALLINT,
  end_date_month      SMALLINT,
  end_date_day        SMALLINT,
  ended               BOOLEAN NOT NULL DEFAULT FALSE
    CHECK (
      (
        -- If any end date fields are not null, then ended must be true
        (end_date_year IS NOT NULL OR
         end_date_month IS NOT NULL OR
         end_date_day IS NOT NULL) AND
        ended = TRUE
      ) OR (
        -- Otherwise, all end date fields must be null
        (end_date_year IS NULL AND
         end_date_month IS NULL AND
         end_date_day IS NULL)
      )
    ),
  comment             VARCHAR(255) NOT NULL DEFAULT ''
);

CREATE TABLE musicbrainz.area_type (
    id                  SERIAL, -- PK
    name                VARCHAR(255) NOT NULL,
    parent              INTEGER, -- references area_type.id
    child_order         INTEGER NOT NULL DEFAULT 0,
    description         TEXT,
    gid                 uuid NOT NULL
);

CREATE TABLE musicbrainz.recording (
  id                  SERIAL,
  gid                 UUID NOT NULL,
  name                VARCHAR NOT NULL,
  artist_credit       INTEGER NOT NULL, -- references artist_credit.id
  length              INTEGER CHECK (length IS NULL OR length > 0),
  comment             VARCHAR(255) NOT NULL DEFAULT '',
  edits_pending       INTEGER NOT NULL DEFAULT 0 CHECK (edits_pending >= 0),
  last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  video               BOOLEAN NOT NULL DEFAULT FALSE
);


CREATE TABLE musicbrainz.recording_gid_redirect (
  gid                 UUID NOT NULL, -- PK
  new_id              INTEGER NOT NULL, -- references recording.id
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE musicbrainz.release (
  id                  SERIAL,
  gid                 UUID NOT NULL,
  name                VARCHAR NOT NULL,
  artist_credit       INTEGER NOT NULL, -- references artist_credit.id
  release_group       INTEGER NOT NULL, -- references release_group.id
  status              INTEGER, -- references release_status.id
  packaging           INTEGER, -- references release_packaging.id
  language            INTEGER, -- references language.id
  script              INTEGER, -- references script.id
  barcode             VARCHAR(255),
  comment             VARCHAR(255) NOT NULL DEFAULT '',
  edits_pending       INTEGER NOT NULL DEFAULT 0 CHECK (edits_pending >= 0),
  quality             SMALLINT NOT NULL DEFAULT -1,
  last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE musicbrainz.release_gid_redirect (
  gid                 UUID NOT NULL, -- PK
  new_id              INTEGER NOT NULL, -- references release.id
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE musicbrainz.track (
  id                  SERIAL,
  gid                 UUID NOT NULL,
  recording           INTEGER NOT NULL, -- references recording.id
  medium              INTEGER NOT NULL, -- references medium.id
  position            INTEGER NOT NULL,
  number              TEXT NOT NULL,
  name                VARCHAR NOT NULL,
  artist_credit       INTEGER NOT NULL, -- references artist_credit.id
  length              INTEGER CHECK (length IS NULL OR length > 0),
  edits_pending       INTEGER NOT NULL DEFAULT 0 CHECK (edits_pending >= 0),
  last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_data_track       BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE musicbrainz.track_gid_redirect (
  gid                 UUID NOT NULL, -- PK
  new_id              INTEGER NOT NULL, -- references track.id
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE musicbrainz.release_group (
  id                  SERIAL,
  gid                 UUID NOT NULL,
  name                VARCHAR NOT NULL,
  artist_credit       INTEGER NOT NULL, -- references artist_credit.id
  type                INTEGER, -- references release_group_primary_type.id
  comment             VARCHAR(255) NOT NULL DEFAULT '',
  edits_pending       INTEGER NOT NULL DEFAULT 0 CHECK (edits_pending >= 0),
  last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE musicbrainz.release_group_gid_redirect (
  gid                 UUID NOT NULL, -- PK
  new_id              INTEGER NOT NULL, -- references release_group.id
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE musicbrainz.medium (
  id                  SERIAL,
  release             INTEGER NOT NULL, -- references release.id
  position            INTEGER NOT NULL,
  format              INTEGER, -- references medium_format.id
  name                VARCHAR NOT NULL DEFAULT '',
  edits_pending       INTEGER NOT NULL DEFAULT 0 CHECK (edits_pending >= 0),
  last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  track_count         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE musicbrainz.medium_format (
  id                  SERIAL,
  name                VARCHAR(100) NOT NULL,
  parent              INTEGER, -- references medium_format.id
  child_order         INTEGER NOT NULL DEFAULT 0,
  year                SMALLINT,
  has_discids         BOOLEAN NOT NULL DEFAULT FALSE,
  description         TEXT,
  gid                 uuid NOT NULL
);

CREATE TABLE musicbrainz.release_status (
  id                  SERIAL,
  name                VARCHAR(255) NOT NULL,
  parent              INTEGER, -- references release_status.id
  child_order         INTEGER NOT NULL DEFAULT 0,
  description         TEXT,
  gid                 uuid NOT NULL
);

CREATE TABLE musicbrainz.release_group_primary_type (
  id                  SERIAL,
  name                VARCHAR(255) NOT NULL,
  parent              INTEGER, -- references release_group_primary_type.id
  child_order         INTEGER NOT NULL DEFAULT 0,
  description         TEXT,
  gid                 uuid NOT NULL
);

CREATE TABLE musicbrainz.language (
  id                  SERIAL,
  iso_code_2t         CHAR(3), -- ISO 639-2 (T)
  iso_code_2b         CHAR(3), -- ISO 639-2 (B)
  iso_code_1          CHAR(2), -- ISO 639
  name                VARCHAR(100) NOT NULL,
  frequency           INTEGER NOT NULL DEFAULT 0,
  iso_code_3          CHAR(3)  -- ISO 639-3
);
ALTER TABLE musicbrainz.language
    ADD CONSTRAINT iso_code_check
    CHECK (iso_code_2t IS NOT NULL OR iso_code_3 IS NOT NULL);

CREATE TABLE musicbrainz.release_packaging (
  id                  SERIAL,
  name                VARCHAR(255) NOT NULL,
  parent              INTEGER, -- references release_packaging.id
  child_order         INTEGER NOT NULL DEFAULT 0,
  description         TEXT,
  gid                 uuid NOT NULL
);

CREATE TABLE musicbrainz.script (
  id                  SERIAL,
  iso_code            CHAR(4) NOT NULL, -- ISO 15924
  iso_number          CHAR(3) NOT NULL, -- ISO 15924
  name                VARCHAR(100) NOT NULL,
  frequency           INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE musicbrainz.gender (
  id                  SERIAL,
  name                VARCHAR(255) NOT NULL,
  parent              INTEGER, -- references gender.id
  child_order         INTEGER NOT NULL DEFAULT 0,
  description         TEXT,
  gid                 uuid NOT NULL
);

CREATE TABLE musicbrainz.artist_type (
  id                  SERIAL,
  name                VARCHAR(255) NOT NULL,
  parent              INTEGER, -- references artist_type.id
  child_order         INTEGER NOT NULL DEFAULT 0,
  description         TEXT,
  gid                 uuid NOT NULL
);

COMMIT;
