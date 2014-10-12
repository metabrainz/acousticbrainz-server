BEGIN;

CREATE TABLE lowlevel (
    id          SERIAL,
    mbid        UUID NOT NULL,
    build_sha1  TEXT NOT NULL,
    lossless    BOOLEAN DEFAULT 'n',
    data        INTEGER NOT NULL,
    submitted   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE lowlevel_data (
    id               SERIAL,
    main_data        INTEGER,
    metadata_version INTEGER,
    metadata_audio   INTEGER,
    metadata_tags    INTEGER
);

CREATE TABLE raw_json (
    id           SERIAL,
    data         JSON NOT NULL,
    data_sha256  CHAR(64) NOT NULL
);

CREATE OR REPLACE VIEW lowlevel_data_json AS
SELECT lowlevel_data.id, row_to_json(
    (select main_json_subquery FROM
        (select main_data_json.data->'lowlevel' AS lowlevel,
                main_data_json.data->'rhythm' AS rhythm,
                main_data_json.data->'tonal' AS tonal,
                (select metadata_subquery FROM (
                    select m_v.data AS version,
                           m_a.data AS audio_properties,
                           m_t.data AS tags
                      from lowlevel_data l_m
                      join raw_json m_v ON l_m.metadata_version = m_v.id
                      join raw_json m_a ON l_m.metadata_audio = m_a.id
                      join raw_json m_t ON l_m.metadata_tags = m_t.id
                     where l_m.id = l.id
                ) metadata_subquery) AS metadata
           from lowlevel_data l
           join raw_json main_data_json on l.main_data = main_data_json.id
          where l.id = lowlevel_data.id) main_json_subquery
    )
) AS json FROM lowlevel_data;

ALTER TABLE lowlevel ADD CONSTRAINT lowlevel_pkey PRIMARY KEY (id);
ALTER TABLE lowlevel_data ADD CONSTRAINT lowlevel_data_pkey PRIMARY KEY (id);
ALTER TABLE raw_json ADD CONSTRAINT raw_json_pkey PRIMARY KEY (id);

ALTER TABLE lowlevel ADD CONSTRAINT lowlevel_fk_data
    FOREIGN KEY (data) REFERENCES lowlevel_data(id);
ALTER TABLE lowlevel_data ADD CONSTRAINT lowlevel_data_fk_main_data
    FOREIGN KEY (main_data) REFERENCES raw_json(id);
ALTER TABLE lowlevel_data ADD CONSTRAINT lowlevel_data_fk_metadata_version
    FOREIGN KEY (metadata_version) REFERENCES raw_json(id);
ALTER TABLE lowlevel_data ADD CONSTRAINT lowlevel_data_fk_metadata_audio
    FOREIGN KEY (metadata_audio) REFERENCES raw_json(id);
ALTER TABLE lowlevel_data ADD CONSTRAINT lowlevel_data_fk_metadata_tags
    FOREIGN KEY (metadata_tags) REFERENCES raw_json(id);

CREATE INDEX mbid_ndx_lowlevel ON lowlevel (mbid);
CREATE INDEX build_sha1_ndx_lowlevel ON lowlevel (build_sha1);

CREATE INDEX data_sha256_ndx_raw_json ON raw_json (data_sha256);

COMMIT;
