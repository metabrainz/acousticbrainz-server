#!/bin/sh

# Setting up PostgreSQL

echo "deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main" >> /etc/apt/sources.list.d/pgdg.list
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
  sudo apt-key add -
sudo apt-get update

PG_VERSION=9.5

apt-get -y install "postgresql-$PG_VERSION" "postgresql-contrib-$PG_VERSION" "postgresql-server-dev-$PG_VERSION"
PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
PG_IDENT="/etc/postgresql/$PG_VERSION/main/pg_ident.conf"

# Setting up PostgreSQL access
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
sed -i "s/local\s*all\s*all\s*peer/local all all trust/" "$PG_HBA"
# Allow vagrant and postgres to access postgres user
sed -i "s/local\s*all\s*postgres\s*peer/local all postgres peer map=vagrant/" "$PG_HBA"
echo "vagrant vagrant postgres" >> "$PG_IDENT"
echo "vagrant postgres postgres" >> "$PG_IDENT"
# Remote psql from host
echo "host all all all trust" >> "$PG_HBA"

# Explicitly set default client_encoding
echo "client_encoding = utf8" >> "$PG_CONF"

service postgresql restart
