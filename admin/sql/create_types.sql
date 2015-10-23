CREATE TYPE eval_job_status AS ENUM ('pending', 'running', 'done', 'failed');
CREATE TYPE eval_filter_type AS ENUM ('artist');
CREATE TYPE model_status AS ENUM ('hidden', 'evaluation', 'show');
