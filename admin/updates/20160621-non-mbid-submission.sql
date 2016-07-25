BEGIN;

CREATE TYPE gid_type AS ENUM ('mbid', 'msid');
ALTER TABLE "lowlevel" RENAME COLUMN mbid TO gid;
ALTER TABLE "lowlevel" ADD COLUMN gid_type gid_type;
UPDATE "lowlevel" SET gid_type = 'mbid';
ALTER TABLE "lowlevel" ALTER COLUMN gid_type SET NOT NULL;
CREATE INDEX gid_type_ndx_lowlevel ON lowlevel (gid_type);

COMMIT;
