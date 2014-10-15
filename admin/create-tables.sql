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

ALTER TABLE lowlevel ADD CONSTRAINT lowlevel_pkey PRIMARY KEY (id);
CREATE INDEX mbid_ndx_lowlevel ON lowlevel (mbid);
CREATE INDEX build_sha1_ndx_lowlevel ON lowlevel (build_sha1);
CREATE INDEX data_sha256_ndx_lowlevel ON lowlevel (data_sha256);

COMMIT;
