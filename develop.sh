#!/usr/bin/env bash

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the acousticbrainz-server source."
    exit -1
fi

docker-compose -f docker/docker-compose.dev.yml -p acousticbrainz-server "$@"
