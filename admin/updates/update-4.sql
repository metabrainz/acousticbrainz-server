BEGIN;

CREATE TABLE dataset (
  id          SERIAL,
  name        VARCHAR NOT NULL,
  description TEXT,
  owner       INT, -- FK to user
  created     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE dataset ADD CONSTRAINT dataset_pkey PRIMARY KEY (id);


CREATE TABLE class (
  id          SERIAL,
  name        VARCHAR NOT NULL,
  description TEXT,
  dataset     INT     NOT NULL -- FK to dataset
);
ALTER TABLE class ADD CONSTRAINT class_pkey PRIMARY KEY (id);


CREATE TABLE class_member (
  class    INT, -- FK to class
  lowlevel INT -- FK to lowlevel
);
ALTER TABLE class ADD CONSTRAINT class_pkey PRIMARY KEY (class, lowlevel);


-- FKs

ALTER TABLE dataset
  ADD CONSTRAINT dataset_fk_user
  FOREIGN KEY (owner)
  REFERENCES "user" (id);

ALTER TABLE class
  ADD CONSTRAINT class_fk_dataset
  FOREIGN KEY (dataset)
  REFERENCES dataset (id);

ALTER TABLE class_member
  ADD CONSTRAINT class_member_fk_class
  FOREIGN KEY (class)
  REFERENCES class (id);

ALTER TABLE class_member
  ADD CONSTRAINT class_member_member_fk_lowlevel
  FOREIGN KEY (lowlevel)
  REFERENCES lowlevel (id);


COMMIT;
