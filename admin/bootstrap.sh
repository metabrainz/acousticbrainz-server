#!/bin/sh
# Application setup script for Vagrant

apt-get update
apt-get -y upgrade

apt-get -y install python-virtualenv python-dev pxz

cd /vagrant
./admin/install_database.sh /vagrant
./admin/install_web_server.sh /vagrant
./admin/install_hl_extractor.sh /vagrant
