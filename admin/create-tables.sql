BEGIN;

-- low level tables

CREATE TABLE lowlevel (
    id      SERIAL,
    mbid        UUID NOT NULL,
    build_sha1  TEXT NOT NULL,
    lossless    BOOLEAN DEFAULT 'n',
    data        JSON NOT NULL,
    submitted   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_sha256 TEXT NOT NULL
);

CREATE TABLE statistics (
    collected   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    name        TEXT NOT NULL,
    value       INTEGER NOT NULL
);

-- high level tables

CREATE TABLE highlevel (
    id          SERIAL,
    mbid        UUID NOT NULL,
    build_sha1  TEXT NOT NULL,
    data        INTEGER NOT NULL,
    submitted   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE highlevel_json (
    id           SERIAL,
    data         JSON NOT NULL,
    data_sha256  CHAR(64) NOT NULL
);

-- primary keys

ALTER TABLE lowlevel ADD CONSTRAINT lowlevel_pkey PRIMARY KEY (id);
ALTER TABLE statistics ADD CONSTRAINT statistics_pkey PRIMARY KEY (name, collected);
ALTER TABLE highlevel ADD CONSTRAINT highlevel_pkey PRIMARY KEY (id);
ALTER TABLE highlevel_json ADD CONSTRAINT highlevel_json_pkey PRIMARY KEY (id);

-- foreign keys

ALTER TABLE highlevel ADD CONSTRAINT highlevel_fk_lowlevel
    FOREIGN KEY (id) REFERENCES lowlevel(id);
ALTER TABLE highlevel ADD CONSTRAINT highlevel_fk_highlevel_json
    FOREIGN KEY (data) REFERENCES highlevel_json(id);

-- indexes

CREATE INDEX mbid_ndx_lowlevel ON lowlevel (mbid);
CREATE INDEX build_sha1_ndx_lowlevel ON lowlevel (build_sha1);
CREATE UNIQUE INDEX data_sha256_ndx_lowlevel ON lowlevel (data_sha256);

CREATE INDEX mbid_ndx_highlevel ON highlevel (mbid);
CREATE INDEX build_sha1_ndx_highlevel ON lowlevel (build_sha1);

COMMIT;
