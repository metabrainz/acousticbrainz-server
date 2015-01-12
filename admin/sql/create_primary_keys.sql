BEGIN;

ALTER TABLE lowlevel ADD CONSTRAINT lowlevel_pkey PRIMARY KEY (id);
ALTER TABLE highlevel ADD CONSTRAINT highlevel_pkey PRIMARY KEY (id);
ALTER TABLE highlevel_json ADD CONSTRAINT highlevel_json_pkey PRIMARY KEY (id);
ALTER TABLE statistics ADD CONSTRAINT statistics_pkey PRIMARY KEY (name, collected);
ALTER TABLE incremental_dumps ADD CONSTRAINT incremental_dumps_pkey PRIMARY KEY (id);

COMMIT;
