BEGIN;

CREATE TABLE lowlevel (
  id                SERIAL,
  gid               UUID      NOT NULL,
  build_sha1        TEXT      NOT NULL,
  lossless          BOOLEAN                  DEFAULT 'n',
  submitted         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  gid_type          gid_type  NOT NULL,
  submission_offset INTEGER   NOT NULL
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
  status        model_status NOT NULL    DEFAULT 'hidden',
  class_mapping JSONB
);

CREATE TABLE statistics (
  collected TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  stats     JSONB                    NOT NULL
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

CREATE TABLE similarity.similarity (
  id          INTEGER, -- PK, FK to lowlevel
  mfccs       DOUBLE PRECISION[] NOT NULL,
  mfccsw      DOUBLE PRECISION[] NOT NULL,
  gfccs       DOUBLE PRECISION[] NOT NULL,
  gfccsw      DOUBLE PRECISION[] NOT NULL,
  key         DOUBLE PRECISION[] NOT NULL,
  bpm         DOUBLE PRECISION[] NOT NULL,
  onsetrate   DOUBLE PRECISION[] NOT NULL,
  moods       DOUBLE PRECISION[] NOT NULL,
  instruments DOUBLE PRECISION[] NOT NULL,
  dortmund    DOUBLE PRECISION[] NOT NULL,
  rosamerica  DOUBLE PRECISION[] NOT NULL,
  tzanetakis  DOUBLE PRECISION[] NOT NULL
);

CREATE TABLE similarity.similarity_metrics (
  metric TEXT, -- PK
  is_hybrid BOOLEAN,
  description TEXT,
  category TEXT,
  visible BOOLEAN
);

CREATE TABLE similarity.similarity_stats (
  metric TEXT,
  means DOUBLE PRECISION[],
  stddevs DOUBLE PRECISION[]
);

CREATE TABLE similarity.eval_params (
  id            SERIAL, -- PK
  metric        TEXT, -- FK to similarity_metrics
  distance_type TEXT,
  n_trees       INTEGER
);
ALTER TABLE similarity.eval_params ADD CONSTRAINT unique_params_constraint UNIQUE(metric, distance_type, n_trees);

CREATE TABLE similarity.eval_results (
  id          SERIAL, -- PK
  query_id    INTEGER, -- FK to lowlevel
  similar_ids INTEGER[],
  distances   DOUBLE PRECISION[],
  params      INTEGER -- FK to eval_params
);
ALTER TABLE similarity.eval_results ADD CONSTRAINT unique_eval_query_constraint UNIQUE(query_id, params);

CREATE TABLE similarity.eval_feedback (
  user_id    INTEGER, -- FK to user
  eval_id   INTEGER, -- FK to eval_results
  result_id  INTEGER,
  rating     similarity.eval_type,
  suggestion TEXT
);

COMMIT;
