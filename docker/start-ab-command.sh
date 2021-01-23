#!/bin/bash

cd /code
exec chpst -uacousticbrainz:acousticbrainz python "$@"
