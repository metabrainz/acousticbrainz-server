BEGIN;

-- rename table to data_dump
ALTER TABLE incremental_dumps RENAME TO data_dump;

-- create a dump_type type
CREATE TYPE dump_type AS ENUM ('full', 'partial');

ALTER TABLE data_dump ADD COLUMN dump_type dump_type;
ALTER INDEX incremental_dumps_pkey RENAME to data_dump_pkey;

COMMIT;
