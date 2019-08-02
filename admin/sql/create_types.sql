CREATE TYPE eval_job_status AS ENUM ('pending', 'running', 'done', 'failed');
CREATE TYPE model_status AS ENUM ('hidden', 'evaluation', 'show');
CREATE TYPE version_type AS ENUM ('lowlevel', 'highlevel');
CREATE TYPE eval_location_type AS ENUM ('local', 'remote');
CREATE TYPE gid_type AS ENUM ('mbid', 'msid');
CREATE TYPE similarity.eval_type AS ENUM ('less similar', 'accurate', 'more similar');
