BEGIN;

-- Add submission offset for all missing items
UPDATE lowlevel
   SET submission_offset = offset_table.submission_offset
  FROM (
SELECT id, ROW_NUMBER ()
   	   OVER (PARTITION BY gid ORDER BY submitted) - 1 submission_offset
  FROM lowlevel )
    AS offset_table
 WHERE lowlevel.id = offset_table.id 
   AND lowlevel.submission_offset IS NULL;

END;