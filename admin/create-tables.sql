BEGIN;

REATE TABLE lowlevel (
    id      SERIAL,
    mbid        UUID NOT NULL,
    build_sha1  TEXT NOT NULL,
    lossless    BOOLEAN DEFAULT ‘n’,
    data        JSON NOT NULL,
    submitted   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE lowlevel ADD CONSTRAINT lowlevel_pkey PRIMARY KEY (id);
CREATE INDEX mbid_ndx_lowlevel ON lowlevel (mbid);
CREATE INDEX build_sha1_ndx_lowlevel ON lowlevel (build_sha1);

COMMIT;
