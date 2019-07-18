BEGIN;

DROP TYPE IF EXISTS eval_job_status     CASCADE;
DROP TYPE IF EXISTS model_status        CASCADE;
DROP TYPE IF EXISTS version_type        CASCADE;
DROP TYPE IF EXISTS eval_location_type  CASCADE;
DROP TYPE IF EXISTS gid_type            CASCADE;
DROP TYPE IF EXISTS eval_type           CASCADE;

COMMIT;