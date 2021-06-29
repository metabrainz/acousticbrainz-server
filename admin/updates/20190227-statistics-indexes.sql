BEGIN;

CREATE INDEX collected_ndx_statistics ON statistics (collected);
CREATE INDEX collected_hour_ndx_statistics ON statistics (date_part('hour'::text, timezone('UTC'::text, collected)));

COMMIT;
