#!/bin/sh -e

apt-get update
apt-get -y upgrade

cd /vagrant/admin
./install_server.sh
./install_hl_extractor.sh
