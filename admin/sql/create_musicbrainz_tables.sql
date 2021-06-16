BEGIN;

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

CREATE TABLE musicbrainz.replication_control (
  id                              SERIAL,
  current_replication_sequence    INTEGER,
  last_replication_date           TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMIT;
