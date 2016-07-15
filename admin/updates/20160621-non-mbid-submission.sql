BEGIN;

CREATE TYPE id_type AS ENUM ('mbid', 'msid');
ALTER TABLE "lowlevel" RENAME COLUMN mbid TO gid;
ALTER TABLE "lowlevel" ADD COLUMN is_mbid id_type;
UPDATE "lowlevel" SET is_mbid = 'mbid';
ALTER TABLE "lowlevel" ALTER COLUMN is_mbid SET NOT NULL;
CREATE INDEX is_mbid_ndx_lowlevel ON lowlevel (is_mbid);

COMMIT;
