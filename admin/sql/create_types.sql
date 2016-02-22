CREATE TYPE eval_job_status AS ENUM ('pending', 'running', 'done', 'failed');
CREATE TYPE model_status AS ENUM ('hidden', 'evaluation', 'show');
CREATE TYPE version_type AS ENUM ('lowlevel', 'highlevel');
