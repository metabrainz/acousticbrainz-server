BEGIN;

-- rename table to data_dump
ALTER TABLE incremental_dumps RENAME TO data_dump;

-- create a dump_type type
CREATE TYPE dump_type AS ENUM ('full', 'partial');

-- Add dump_type column to data_dump table
ALTER TABLE data_dump ADD COLUMN dump_type dump_type;

COMMIT;
