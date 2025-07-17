#!/bin/bash

set -e
set -u

export "$(grep -v '^#' deploy/config.env | xargs)"

# Gitlab CI will set AKCENT_GRAPH_VERSION
if [ -z "${AKCENT_GRAPH_VERSION:-}" ]; then
  if [ "$#" -gt 0 ]; then
    AKCENT_GRAPH_VERSION=$1
  fi
fi
if [ -z "${AKCENT_GRAPH_VERSION}" ]; then
  echo Error: empty version; exit 1
fi

DIST_DIR=dist
PACKAGE_NAME="akcent_graph-${AKCENT_GRAPH_VERSION}"
PACKAGE="${PACKAGE_NAME}.tar.gz"

mkdir -p deploy/box
IMAGES="deploy/images/"

GREEN="\033[0;32m"
DEFAULT="\033[39m"

print_green() {
  echo -e "${GREEN}${1}${DEFAULT}"
}

print_green "Packaging of version \"${AKCENT_GRAPH_VERSION}\" started"
cd "$(dirname "$0")/.."

cp deploy/config.env deploy/box/config.env

print_green "Creating package"
echo "${AKCENT_GRAPH_VERSION}" > deploy/box/.version
mkdir -p ${DIST_DIR}
cp deploy/install.sh deploy/box
cp deploy/connect_to_sentry.sh deploy/box
cp deploy/docker-compose.prod.yml deploy/box/docker-compose.yml
tar --totals -czf "${DIST_DIR}/${PACKAGE}" -C deploy images box --transform=s,box,"${PACKAGE_NAME}",

print_green "Removing intermediate files"
rm -r ${IMAGES}
rm deploy/box/{.version,config.env,install.sh,docker-compose.yml,connect_to_sentry.sh}

print_green "Success. Distribution kit was stored to \"${DIST_DIR}\" directory."
