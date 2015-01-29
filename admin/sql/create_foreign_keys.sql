BEGIN;

ALTER TABLE highlevel
  ADD CONSTRAINT highlevel_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);

ALTER TABLE highlevel
  ADD CONSTRAINT highlevel_fk_highlevel_json
  FOREIGN KEY (data)
  REFERENCES highlevel_json (id);

COMMIT;
