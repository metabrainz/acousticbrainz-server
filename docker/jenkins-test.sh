#!/usr/bin/env bash

# Modify these two as needed:
COMPOSE_FILE_LOC="docker/docker-compose.jenkins.yml"
TEST_SERVICE_NAME="acousticbrainz"

COMPOSE_PROJECT_NAME_ORIGINAL="jenkinsbuild_${BUILD_TAG}"

# Project name is sanitized by Compose, so we need to do the same thing.
# See https://github.com/docker/compose/issues/2119.
COMPOSE_PROJECT_NAME=$(echo $COMPOSE_PROJECT_NAME_ORIGINAL | awk '{print tolower($0)}' | sed 's/[^a-z0-9]*//g')
TEST_CONTAINER_REF="${COMPOSE_PROJECT_NAME}_${TEST_SERVICE_NAME}_run_1"

# Record installed version of Docker and Compose with each build
echo "Docker environment:"
docker --version
docker-compose --version

function cleanup {
    # Shutting down all containers associated with this project
    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                   down --remove-
    docker ps -a --no-trunc  | grep $COMPOSE_PROJECT_NAME \
        | awk '{print $1}' | xargs --no-run-if-empty docker stop
    docker ps -a --no-trunc  | grep $COMPOSE_PROJECT_NAME \
        | awk '{print $1}' | xargs --no-run-if-empty docker rm
}

function run_tests {

    ls -lR

    # Create containers
    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                   build

    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                   up -d db redis

    # List images and containers related to this build
    docker images | grep $COMPOSE_PROJECT_NAME | awk '{print $0}'
    docker ps -a | grep $COMPOSE_PROJECT_NAME | awk '{print $0}'

    # create database and user once
    echo "creating user and database"
    docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME run --rm $TEST_SERVICE_NAME \
        dockerize \
        -wait tcp://db:5432 -timeout 60s bash -c \
        "cd /code && cp config.py.example config.py && ls -lR && python manage.py init_db"

    # run tests
    echo "running tests"
    # NOTE: we specify container name here so that we have a consistent name, allowing
    # us to copy over the test results later in the script. The container name contains
    # a reference to the jenkins tag, so it won't conflict with other test runs.
    docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME run  --name $TEST_CONTAINER_REF $TEST_SERVICE_NAME \
                dockerize \
                -wait tcp://db:5432 -timeout 60s \
                -wait tcp://redis:6379 -timeout 60s \
                bash -c "cp /code/config.py.example /code/config.py && py.test --junitxml=/test_report.xml --cov-report xml:/coverage.xml"
}

function extract_results {
    docker cp ${TEST_CONTAINER_REF}:/test_report.xml .
    docker cp ${TEST_CONTAINER_REF}:/coverage.xml .
}

set -e
cleanup            # Initial cleanup
trap cleanup EXIT  # Cleanup after tests finish running

run_tests
extract_results
