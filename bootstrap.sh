#!/bin/sh

apt-get update
apt-get -y upgrade

cd /vagrant
./admin/install_web_server.sh /vagrant
./admin/install_hl_extractor.sh /vagrant
