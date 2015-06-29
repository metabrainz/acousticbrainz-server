#!/bin/sh
# Application setup script for Vagrant

# If -h is set, install the highlevel extractor
AB_DO_HL=0
while getopts ":h" opt; do
case $opt in
    h)
      shift
      AB_DO_HL=1
      ;;
esac
done

# If an argument is given, it's an apt archive
if [ $# -eq 1 ]; then
  echo "Setting apt mirror to $1"
  sed -i "s/archive.ubuntu.com/$1/" /etc/apt/sources.list
fi

apt-get update
apt-get -y upgrade

cd /vagrant
./admin/install_database.sh /vagrant
./admin/install_web_server.sh /vagrant
if [ $AB_DO_HL -eq 1 ]; then
    ./admin/install_hl_extractor.sh /vagrant
fi
