#!/bin/sh

# Create the database
psql -U postgres < sql/create_test_db.sql

# Create the stuff
psql -U ab_test ab_test < sql/create_tables.sql
psql -U ab_test ab_test < sql/create_primary_keys.sql
psql -U ab_test ab_test < sql/create_foreign_keys.sql
psql -U ab_test ab_test < sql/create_indexes.sql
psql -U postgres ab_test < sql/create_extensions.sql
