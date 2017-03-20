#!/bin/sh

curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
apt-get -y install memcached python-virtualenv python-dev ipython pxz nodejs libffi-dev libssl-dev
