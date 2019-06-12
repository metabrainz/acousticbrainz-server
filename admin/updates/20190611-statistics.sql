BEGIN;

-- Add a column to store json values of statistics
ALTER TABLE statistics ADD COLUMN stats JSONB;

-- For each day at 00h00m00s, make a json object representing the stats for that
-- timestamp and add it to the column (This duplicates the same data for all 6 types, but we'll delete 5 of them)
UPDATE statistics SET stats = subquery.stats
    FROM (SELECT collected
               , jsonb_object_agg(name, value) as stats
      FROM statistics
     WHERE date_part('hour', timezone('UTC'::text, collected)) = 0
    GROUP BY collected
    ORDER BY collected DESC) as subquery
WHERE statistics.collected = subquery.collected;

-- Once we have combined stats in each row, delete the rows without stats (old hourly stats)
DELETE FROM statistics WHERE stats is NULL;
-- and keep only one stat per timestamp
DELETE FROM statistics WHERE name <> 'lowlevel-total';
-- And we no longer need name/value columns because we have the stats jsonb column
ALTER TABLE statistics DROP COLUMN name;
ALTER TABLE statistics DROP COLUMN value;

-- We no longer need a specific index for getting daily stats because stats are now only daily
DROP INDEX IF EXISTS collected_hour_ndx_statistics;

-- now that the stats column is populated, set it not null
ALTER TABLE statistics ALTER COLUMN stats SET NOT NULL;

COMMIT;
