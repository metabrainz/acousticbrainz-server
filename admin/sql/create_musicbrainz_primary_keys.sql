BEGIN;

ALTER TABLE musicbrainz.artist ADD CONSTRAINT artist_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.artist_credit ADD CONSTRAINT artist_credit_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.artist_credit_name ADD CONSTRAINT artist_credit_name_pkey PRIMARY KEY (artist_credit, position);
ALTER TABLE musicbrainz.artist_gid_redirect ADD CONSTRAINT artist_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.area ADD CONSTRAINT area_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.area_type ADD CONSTRAINT area_type_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.recording ADD CONSTRAINT recording_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.recording_gid_redirect ADD CONSTRAINT recording_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.release ADD CONSTRAINT release_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_gid_redirect ADD CONSTRAINT release_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.track ADD CONSTRAINT track_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.track_gid_redirect ADD CONSTRAINT track_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.release_group ADD CONSTRAINT release_group_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_group_gid_redirect ADD CONSTRAINT release_group_gid_redirect_pkey PRIMARY KEY (gid);
ALTER TABLE musicbrainz.medium ADD CONSTRAINT medium_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.medium_format ADD CONSTRAINT medium_format_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_status ADD CONSTRAINT release_status_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_group_primary_type ADD CONSTRAINT release_group_primary_type_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.language ADD CONSTRAINT language_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.release_packaging ADD CONSTRAINT release_packaging_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.script ADD CONSTRAINT script_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.gender ADD CONSTRAINT gender_pkey PRIMARY KEY (id);
ALTER TABLE musicbrainz.artist_type ADD CONSTRAINT artist_type_pkey PRIMARY KEY (id);

COMMIT;
