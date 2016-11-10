BEGIN;

CREATE TABLE bigquery_lowlevel (
  lowlevel        INTEGER -- FK to lowlevel.id
);

CREATE TABLE bigquery_highlevel (
  highlevel_model      INTEGER -- FK to highlevel_model.id
);

ALTER TABLE bigquery_lowlevel
  ADD CONSTRAINT lowlevel_fk_lowlevel
  FOREIGN KEY (lowlevel)
  REFERENCES lowlevel (id);

ALTER TABLE bigquery_highlevel
  ADD CONSTRAINT highlevel_model_fk_highlevel_model
  FOREIGN KEY (highlevel_model)
  REFERENCES highlevel_model (id);

CREATE UNIQUE INDEX lowlevel_ndx_bigquery_lowlevel ON bigquery_lowlevel (lowlevel);
CREATE UNIQUE INDEX highlevel_model_ndx_bigquery_highlevel ON bigquery_highlevel (highlevel_model);

COMMIT;
