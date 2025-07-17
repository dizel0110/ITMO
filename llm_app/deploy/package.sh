#!/bin/bash

# The script to create NLP package, which should be the same as built on CI. You may upload it to file storage manually.

set -e
set -u

# Gitlab CI will set NLP_VERSION
if [ -z "${NLP_VERSION:-}" ]; then
  if [ "$#" -gt 0 ]; then
    NLP_VERSION=$1
  else
    read -rp 'Which version to build?: ' NLP_VERSION
  fi
fi
if [ -z "${NLP_VERSION}" ]; then
  echo Error: empty version; exit 1
fi

CURRENT_DIR=$(pwd)
EXTRA_WORD="_copy"
LAST_DIR_NAME=$(basename "$CURRENT_DIR")
COPY_FOLDER_PATH="$CURRENT_DIR/$LAST_DIR_NAME$EXTRA_WORD"

mkdir "$COPY_FOLDER_PATH"

cp -r "$CURRENT_DIR/fixtures" "$COPY_FOLDER_PATH/"
cp -r "$CURRENT_DIR/nlp" "$COPY_FOLDER_PATH/"
cp -r "$CURRENT_DIR/deploy" "$COPY_FOLDER_PATH/"
cp -r "$CURRENT_DIR/FulltextSearchAndSimilar" "$COPY_FOLDER_PATH/"
cp "docker-compose.yml" "$COPY_FOLDER_PATH/"
cp "manage.py" "$COPY_FOLDER_PATH/"
mv "pyarmor-regfile"* "$COPY_FOLDER_PATH/"


cd "$COPY_FOLDER_PATH"

cp deploy/config.env deploy/.env

export "$(grep -v '^#' deploy/config.env | xargs)"
poetry export --without-hashes > requirements.prod.txt


DIST_DIR=dist
PACKAGE_NAME="nlp-${NLP_VERSION}"
PACKAGE="${PACKAGE_NAME}.tar.gz"
mkdir -p deploy/box
mkdir -p deploy/images
IMAGES="deploy/images/services.img"

GREEN="\033[0;32m"
DEFAULT="\033[39m"

print_green() {
  echo -e "${GREEN}${1}${DEFAULT}"
}

./deploy/obfuscation.sh

print_green "Packaging of version \"${NLP_VERSION}\" started"
cd "$(dirname "$0")/.."

print_green "Building backend"
docker build -t nlp/django:latest . -f ./deploy/django/Dockerfile
docker build -t nlp/nginx:latest . -f ./deploy/nginx/Dockerfile

print_green "Pull docker images from Internet"
docker-compose -f docker-compose.yml pull

cp deploy/config.env deploy/box/config.env

print_green "Saving docker images"
images=""
for img in $(docker-compose -f deploy/docker-compose.prod.yml config | awk '{if ($1 == "image:") print $2;}'); do
  images="$images $img"
done
# shellcheck disable=SC2086
docker save -o ${IMAGES} ${images}

print_green "Creating package"
echo "${NLP_VERSION}" > deploy/box/.version
mkdir -p ${DIST_DIR}
cp deploy/install.sh deploy/box
cp deploy/init_llm.sh deploy/box
cp deploy/connect_to_sentry.sh deploy/box
cp deploy/docker-compose.prod.yml deploy/box/docker-compose.yml
echo -e "${DIST_DIR}/${PACKAGE}"
tar --totals -czf "${DIST_DIR}/${PACKAGE}" -C deploy images box --transform=s,box,"${PACKAGE_NAME}",

print_green "Removing intermediate files"
rm ${IMAGES}
rm deploy/box/{.version,config.env,install.sh,init_llm.sh,connect_to_sentry.sh,docker-compose.yml}
rm deploy/.env
rm requirements.prod.txt

cd "$CURRENT_DIR"


mv "$COPY_FOLDER_PATH/dist/nlp"* "$CURRENT_DIR"/dist
rm -r "$COPY_FOLDER_PATH"

print_green "Success. Distribution kit was stored to \"${DIST_DIR}\" directory."
