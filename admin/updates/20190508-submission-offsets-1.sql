BEGIN;

ALTER TABLE lowlevel ADD COLUMN submission_offset INTEGER;

-- Updating the submission offset column based on determination of offset
UPDATE lowlevel 
   SET submission_offset = offset_table.submission_offset
  FROM (
SELECT id, ROW_NUMBER () 
	   OVER (PARTITION BY gid ORDER BY submitted) - 1 submission_offset 
  FROM lowlevel)
    AS offset_table
 WHERE lowlevel.id = offset_table.id;

COMMIT;