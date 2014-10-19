BEGIN;

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

ALTER TABLE lowlevel ADD CONSTRAINT lowlevel_pkey PRIMARY KEY (id);
CREATE INDEX mbid_ndx_lowlevel ON lowlevel (mbid);
CREATE INDEX build_sha1_ndx_lowlevel ON lowlevel (build_sha1);
CREATE UNIQUE INDEX data_sha256_ndx_lowlevel ON lowlevel (data_sha256);

ALTER TABLE statistics ADD CONSTRAINT statistics_pkey PRIMARY KEY (name, collected);

COMMIT;
