BEGIN;

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

ALTER TABLE musicbrainz.artist ADD CONSTRAINT artist_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.artist_credit ADD CONSTRAINT artist_credit_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.artist_credit_name ADD CONSTRAINT artist_credit_name_pkey PRIMARY KEY (artist_credit, position);
ALTER TABLE musicbrainz.artist_gid_redirect ADD CONSTRAINT artist_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.area ADD CONSTRAINT area_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.area_type ADD CONSTRAINT area_type_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.recording ADD CONSTRAINT recording_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.recording_gid_redirect ADD CONSTRAINT recording_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.release ADD CONSTRAINT release_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_gid_redirect ADD CONSTRAINT release_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.track ADD CONSTRAINT track_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.track_gid_redirect ADD CONSTRAINT track_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.release_group ADD CONSTRAINT release_group_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_group_gid_redirect ADD CONSTRAINT release_group_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.medium ADD CONSTRAINT medium_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.medium_format ADD CONSTRAINT medium_format_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_status ADD CONSTRAINT release_status_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_group_primary_type ADD CONSTRAINT release_group_primary_type_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.language ADD CONSTRAINT language_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_packaging ADD CONSTRAINT release_packaging_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.script ADD CONSTRAINT script_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.gender ADD CONSTRAINT gender_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.artist_type ADD CONSTRAINT artist_type_pkey PRIMARY KEY (id);

ALTER TABLE musicbrainz.artist
  ADD CONSTRAINT artist_fk_type
  FOREIGN KEY (type)
  REFERENCES musicbrainz.artist_type(id);

ALTER TABLE musicbrainz.artist
  ADD CONSTRAINT artist_fk_area
  FOREIGN KEY (area)
  REFERENCES musicbrainz.area(id);

ALTER TABLE musicbrainz.artist
  ADD CONSTRAINT artist_fk_gender
  FOREIGN KEY (gender)
  REFERENCES musicbrainz.gender(id);

ALTER TABLE musicbrainz.artist
  ADD CONSTRAINT artist_fk_begin_area
  FOREIGN KEY (begin_area)
  REFERENCES musicbrainz.area(id);

ALTER TABLE musicbrainz.artist
  ADD CONSTRAINT artist_fk_end_area
  FOREIGN KEY (end_area)
  REFERENCES musicbrainz.area(id);

ALTER TABLE musicbrainz.artist_credit_name
  ADD CONSTRAINT artist_credit_name_fk_artist_credit
  FOREIGN KEY (artist_credit)
  REFERENCES musicbrainz.artist_credit(id)
  ON DELETE CASCADE;

ALTER TABLE musicbrainz.artist_credit_name
  ADD CONSTRAINT artist_credit_name_fk_artist
  FOREIGN KEY (artist)
  REFERENCES musicbrainz.artist(id)
  ON DELETE CASCADE;

ALTER TABLE musicbrainz.artist_gid_redirect
  ADD CONSTRAINT artist_gid_redirect_fk_new_id
  FOREIGN KEY (new_id)
  REFERENCES musicbrainz.artist(id);

ALTER TABLE musicbrainz.area
  ADD CONSTRAINT area_fk_type
  FOREIGN KEY (type)
  REFERENCES musicbrainz.area_type(id);

ALTER TABLE musicbrainz.area_type
  ADD CONSTRAINT area_type_fk_parent
  FOREIGN KEY (parent)
REFERENCES musicbrainz.area_type(id);

ALTER TABLE musicbrainz.recording
  ADD CONSTRAINT recording_fk_artist_credit
  FOREIGN KEY (artist_credit)
  REFERENCES musicbrainz.artist_credit(id);

ALTER TABLE musicbrainz.recording_gid_redirect
  ADD CONSTRAINT recording_gid_redirect_fk_new_id
  FOREIGN KEY (new_id)
  REFERENCES musicbrainz.recording(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_artist_credit
  FOREIGN KEY (artist_credit)
  REFERENCES musicbrainz.artist_credit(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_release_group
  FOREIGN KEY (release_group)
  REFERENCES musicbrainz.release_group(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_status
  FOREIGN KEY (status)
  REFERENCES musicbrainz.release_status(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_packaging
  FOREIGN KEY (packaging)
  REFERENCES musicbrainz.release_packaging(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_language
  FOREIGN KEY (language)
  REFERENCES musicbrainz.language(id);

ALTER TABLE musicbrainz.release
  ADD CONSTRAINT release_fk_script
  FOREIGN KEY (script)
  REFERENCES musicbrainz.script(id);

ALTER TABLE musicbrainz.release_gid_redirect
  ADD CONSTRAINT release_gid_redirect_fk_new_id
  FOREIGN KEY (new_id)
  REFERENCES musicbrainz.release(id);

ALTER TABLE musicbrainz.track
  ADD CONSTRAINT track_fk_recording
  FOREIGN KEY (recording)
  REFERENCES musicbrainz.recording(id);

ALTER TABLE musicbrainz.track
  ADD CONSTRAINT track_fk_medium
  FOREIGN KEY (medium)
  REFERENCES musicbrainz.medium(id);

ALTER TABLE musicbrainz.track
  ADD CONSTRAINT track_fk_artist_credit
  FOREIGN KEY (artist_credit)
  REFERENCES musicbrainz.artist_credit(id);

ALTER TABLE musicbrainz.track_gid_redirect
  ADD CONSTRAINT track_gid_redirect_fk_new_id
  FOREIGN KEY (new_id)
  REFERENCES musicbrainz.track(id);

ALTER TABLE musicbrainz.release_group
  ADD CONSTRAINT release_group_fk_artist_credit
  FOREIGN KEY (artist_credit)
  REFERENCES musicbrainz.artist_credit(id);

ALTER TABLE musicbrainz.release_group
  ADD CONSTRAINT release_group_fk_type
  FOREIGN KEY (type)
  REFERENCES musicbrainz.release_group_primary_type(id);

ALTER TABLE musicbrainz.release_group_primary_type
  ADD CONSTRAINT release_group_primary_type_fk_parent
  FOREIGN KEY (parent)
  REFERENCES musicbrainz.release_group_primary_type;

ALTER TABLE musicbrainz.release_group_gid_redirect
  ADD CONSTRAINT release_group_gid_redirect_fk_new_id
  FOREIGN KEY (new_id)
  REFERENCES musicbrainz.release_group(id);

ALTER TABLE musicbrainz.medium
  ADD CONSTRAINT medium_fk_release
  FOREIGN KEY (release)
  REFERENCES musicbrainz.release(id);

ALTER TABLE musicbrainz.medium
  ADD CONSTRAINT medium_fk_format
  FOREIGN KEY (format)
  REFERENCES musicbrainz.medium_format(id);

ALTER TABLE musicbrainz.medium_format
  ADD CONSTRAINT medium_format_fk_parent
  FOREIGN KEY (parent)
REFERENCES musicbrainz.medium_format(id);

ALTER TABLE musicbrainz.release_status
  ADD CONSTRAINT release_status_fk_parent
  FOREIGN KEY (parent)
  REFERENCES musicbrainz.release_status(id);

ALTER TABLE musicbrainz.release_packaging
  ADD CONSTRAINT release_packaging_fk_parent
  FOREIGN KEY (parent)
  REFERENCES musicbrainz.release_packaging(id);

ALTER TABLE musicbrainz.gender
  ADD CONSTRAINT gender_fk_parent
  FOREIGN KEY (parent)
  REFERENCES musicbrainz.gender(id);

ALTER TABLE musicbrainz.artist_type
  ADD CONSTRAINT artist_type_fk_parent
  FOREIGN KEY (parent)
  REFERENCES musicbrainz.artist_type(id);

CREATE UNIQUE INDEX artist_idx_gid ON musicbrainz.artist (gid);
CREATE INDEX artist_idx_name ON musicbrainz.artist (name);
CREATE INDEX artist_idx_sort_name ON musicbrainz.artist (sort_name);
CREATE INDEX artist_idx_area ON musicbrainz.artist (area);
CREATE UNIQUE INDEX artist_idx_null_comment ON musicbrainz.artist (name) WHERE comment IS NULL;
CREATE UNIQUE INDEX artist_idx_uniq_name_comment ON musicbrainz.artist (name, comment) WHERE comment IS NOT NULL;

CREATE UNIQUE INDEX area_idx_gid ON musicbrainz.area (gid);
CREATE INDEX area_idx_name ON musicbrainz.area (name)

CREATE INDEX artist_credit_name_idx_artist ON musicbrainz.artist_credit_name (artist);

CREATE UNIQUE INDEX recording_idx_gid ON musicbrainz.recording (gid);
CREATE INDEX recording_idx_name ON musicbrainz.recording (name);
CREATE INDEX recording_idx_artist_credit ON musicbrainz.recording (artist_credit);

CREATE UNIQUE INDEX release_idx_gid ON musicbrainz.release (gid);
CREATE INDEX release_idx_name ON musicbrainz.release (name);
CREATE INDEX release_idx_release_group ON musicbrainz.release (release_group);
CREATE INDEX release_idx_artist_credit ON musicbrainz.release (artist_credit);

CREATE UNIQUE INDEX track_idx_gid ON musicbrainz.track (gid);
CREATE INDEX track_idx_recording ON musicbrainz.track (recording);
CREATE INDEX track_idx_name ON musicbrainz.track (name);
CREATE INDEX track_idx_artist_credit ON musicbrainz.track (artist_credit);

CREATE INDEX artist_gid_redirect_idx_new_id ON musicbrainz.artist_gid_redirect (new_id);

CREATE INDEX recording_gid_redirect_idx_new_id ON musicbrainz.recording_gid_redirect (new_id);

CREATE INDEX release_gid_redirect_idx_new_id ON musicbrainz.release_gid_redirect (new_id);

CREATE INDEX release_group_gid_redirect_idx_new_id ON musicbrainz.release_group_gid_redirect (new_id);

CREATE INDEX track_gid_redirect_idx_new_id ON musicbrainz.track_gid_redirect (new_id);

CREATE UNIQUE INDEX release_group_idx_gid ON musicbrainz.release_group (gid);
CREATE INDEX release_group_idx_name ON musicbrainz.release_group (name);
CREATE INDEX release_group_idx_artist_credit ON musicbrainz.release_group (artist_credit);

CREATE INDEX medium_idx_track_count ON musicbrainz.medium (track_count);

CREATE INDEX artist_idx_begin_area ON musicbrainz.artist (begin_area);
CREATE INDEX artist_idx_end_area ON musicbrainz.artist (end_area);

CREATE UNIQUE INDEX area_type_idx_gid ON musicbrainz.area_type (gid);

CREATE UNIQUE INDEX medium_format_idx_gid ON musicbrainz.medium_format (gid);

CREATE UNIQUE INDEX release_status_idx_gid ON musicbrainz.release_status (gid);

CREATE UNIQUE INDEX language_idx_iso_code_2b ON musicbrainz.language (iso_code_2b);
CREATE UNIQUE INDEX language_idx_iso_code_2t ON musicbrainz.language (iso_code_2t);
CREATE UNIQUE INDEX language_idx_iso_code_1 ON musicbrainz.language (iso_code_1);
CREATE UNIQUE INDEX language_idx_iso_code_3 ON musicbrainz.language (iso_code_3);

CREATE UNIQUE INDEX release_packaging_idx_gid ON musicbrainz.release_packaging (gid);

CREATE UNIQUE INDEX script_idx_iso_code ON musicbrainz.script (iso_code);

CREATE UNIQUE INDEX gender_idx_gid ON musicbrainz.gender (gid);

CREATE UNIQUE INDEX artist_type_idx_gid ON musicbrainz.artist_type (gid);

COMMIT;
