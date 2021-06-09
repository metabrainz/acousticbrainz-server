#!/usr/bin/env bash

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the acousticbrainz-server source."
    exit -1
fi

docker_compose() {
    exec docker-compose -f docker/docker-compose.dev.yml -p acousticbrainz-server "$@"
}

run() {
    docker_compose run --rm --user `id -u`:`id -g` "$@"
}

if [[ "$1" == "manage" ]]; then shift
    run webserver python manage.py "$@"
elif [[ "$1" == "psql" ]]; then shift
    run db psql -h db -U acousticbrainz acousticbrainz
elif [[ "$1" == "bash" ]]; then shift
    docker_compose run --rm webserver bash
elif [[ "$1" == "shell" ]]; then shift
    docker_compose run --rm webserver flask shell
elif [[ "$1" == "npm" ]]; then shift
    run -e HOME=/tmp webserver npm "$@"
else
    docker_compose "$@"
fi
