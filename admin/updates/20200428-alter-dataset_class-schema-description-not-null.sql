BEGIN;

-- Update the NULL values of the description column of the dataset_class to and empty string
UPDATE dataset_class SET description = '' WHERE description IS NULL;
-- Alter the table schema by adding the NOT NULL contraint to the description column of the dataset_class table
ALTER TABLE dataset_class ALTER COLUMN description SET NOT NULL;

COMMIT;
