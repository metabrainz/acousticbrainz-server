#!/bin/sh

# Create the database
psql -U postgres < create-db.sql

# Create the stuff
psql -U acousticbrainz acousticbrainz < sql/create_tables.sql
psql -U acousticbrainz acousticbrainz < sql/create_primary_keys.sql
psql -U acousticbrainz acousticbrainz < sql/create_foreign_keys.sql
psql -U acousticbrainz acousticbrainz < sql/create_indexes.sql
