#!/bin/sh -e

apt-get update
apt-get -y upgrade

./admin/install_server.sh
./admin/install_hl_extractor.sh
