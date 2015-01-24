#!/bin/sh

# Installing dependencies
apt-get -y install build-essential libyaml-dev libfftw3-dev libavcodec-dev \
    libavformat-dev python-dev python-numpy-dev python-numpy git \
    libsamplerate0-dev libtag1-dev libqt4-dev swig pkg-config

# Gaia
# See https://github.com/MTG/gaia
git clone https://github.com/MTG/gaia.git /tmp/gaia
cd /tmp/gaia
./waf configure --download
./waf
./waf install

# Essentia
# See http://essentia.upf.edu/documentation/installing.html
git clone https://github.com/MTG/essentia.git /tmp/essentia
cd /tmp/essentia
./waf configure --mode=release --with-gaia --with-example=streaming_extractor_music_svm
./waf
cp /tmp/essentia/build/src/examples/streaming_extractor_music_svm \
    /vagrant/high-level/streaming_extractor_music_svm
