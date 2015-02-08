#!/bin/sh

# Create the database
psql -U postgres < sql/create_db.sql

# Create the stuff
psql -U acousticbrainz acousticbrainz < sql/create_tables.sql
psql -U acousticbrainz acousticbrainz < sql/create_extensions.sql
psql -U acousticbrainz acousticbrainz < sql/create_primary_keys.sql
psql -U acousticbrainz acousticbrainz < sql/create_foreign_keys.sql
psql -U acousticbrainz acousticbrainz < sql/create_indexes.sql
