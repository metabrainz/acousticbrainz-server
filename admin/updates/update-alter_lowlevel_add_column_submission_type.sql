BEGIN;

ALTER TABLE "lowlevel" ADD COLUMN sumbission_type BOOLEAN DEFAULT FALSE;
UPDATE "lowlevel" SET sumbission_type = FALSE;
ALTER TABLE "lowlevel" ALTER COLUMN sumbission_type SET NOT NULL;

COMMIT;
