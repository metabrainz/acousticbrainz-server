BEGIN;

ALTER TABLE "lowlevel" RENAME COLUMN mbid TO gid;
ALTER TABLE "lowlevel" ADD COLUMN is_mbid BOOLEAN;
UPDATE "lowlevel" SET is_mbid = TRUE;
ALTER TABLE "lowlevel" ALTER COLUMN is_mbid SET NOT NULL;

COMMIT;
