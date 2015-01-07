#!/bin/sh

# Create the database
psql -U postgres < create-test-db.sql

# Create the tables
psql -U ab_test ab_test < create-tables.sql
