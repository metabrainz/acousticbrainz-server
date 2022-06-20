#!/bin/bash
#
# Build images from the currently checked out version of AcousticBrainz
# and push it to the Docker Hub, with an optional tag (by default "beta").
#
# Usage:
#   $ ./push.sh [tag]
#
# Examples:
#   $ ./push.sh beta             # will push image with tag beta
#   $ ./push.sh v-2018-07-14.0   # will push images with tag v-2018-07-14.0

cd "$(dirname "${BASH_SOURCE[0]}")/../"

GIT_COMMIT_SHA=$(git describe --tags --dirty --always)
echo "$GIT_COMMIT_SHA" > .git-version

function build_and_push_image {
  echo "Building AcousticBrainz web image with tag $2..."
  docker build -f "$1"  -t metabrainz/acousticbrainz:$2 \
        --target acousticbrainz-prod \
        --build-arg GIT_COMMIT_SHA="$GIT_COMMIT_SHA" . && \
  echo "Done!" && \
  echo "Pushing image to dockerhub metabrainz/acousticbrainz-web:$2..." && \
  docker push metabrainz/acousticbrainz:$2 && \
  echo "Done!"
}

TAG=${1:-beta}
build_and_push_image "Dockerfile" "${TAG}"
build_and_push_image "Dockerfile.py2" "${TAG}-py2"
