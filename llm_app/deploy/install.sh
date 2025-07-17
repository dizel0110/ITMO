#!/bin/bash

# Install NLP module

set -e
set -u

RED="\033[0;31m"
GREEN="\033[0;32m"
DEFAULT="\033[39m"

INVOKE_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# shellcheck disable=SC2046
export $(grep -v '^#' "${INVOKE_DIR}/config.env" | xargs)

ROOT_UID=0
WORKDIR=${WORKDIR_PATH}
COMPOSE_FILE="${WORKDIR}/docker-compose.yml"
LLM_IMAGE="./images/llm.img"
LLM_DIR="${WORKDIR}/llm/"


PATH=${PATH}:/usr/local/bin:/usr/local/sbin

export COMPOSE_HTTP_TIMEOUT=300

if [ "$UID" -ne "$ROOT_UID" ]; then
  echo -e "${RED}Must be root to run script.${DEFAULT}"; exit 1
fi

mkdir -p "${WORKDIR}"
mkdir -p "${WORKDIR}/ssl"
mkdir -p "${WORKDIR}/private/jwt_keys"
mkdir -p "${LLM_DIR}"
cp -p "${INVOKE_DIR}/init_llm.sh" "${LLM_DIR}"

if [ -f /etc/astra_version ]; then
  OS="Astra"
elif [ -f /etc/debian_version ]; then
  # TODO: check if it is Debian or Ubuntu
  OS="Ubuntu"
elif [ -f /etc/redos-release ]; then
  OS="RedOS"
elif [ -f /etc/redhat-release ]; then
  OS="RedHat"
  REDHAT_VER=$(uname -r | sed 's/^.*\(el[0-9]\+\).*$/\1/')
else
  echo -e "${RED}Unknown OS Family.${DEFAULT} Installation cannot proceed."
  exit 1
fi

if [ -f /etc/selinux/config ]; then
  setenforce 0
  sed -i 's/SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config /etc/selinux/config
fi

case "${OS}" in
  "Ubuntu" | "Astra")
    apt-get update -y
    apt-get install ca-certificates curl gnupg2 software-properties-common sudo net-tools -y
    ;;
  "RedOS" | "RedHat")
    ;;
esac

if [ -x "$(command -v docker)" ]; then
  echo -e "${GREEN}Docker already installed...${DEFAULT}"
else
  echo -e "${GREEN}Install docker...${DEFAULT}"
  case "${OS}" in
    "Ubuntu" | "Astra")
      apt-get update -y
      apt-get install docker.io -y
      ;;
    "RedOS")
      dnf install -y docker-ce
      ;;
    "RedHat")
      dnf remove -y runc
      dnf install -y vendor/pkgs/rh"${REDHAT_VER}"/*
      ;;
  esac
  systemctl enable docker
  systemctl start docker
fi

if [ -x "$(command -v docker-compose)" ]; then
  echo -e "${GREEN}docker-compose already installed${DEFAULT}"
else
  echo -e "${GREEN}Install docker-compose...${DEFAULT}"
  case "${OS}" in
    "Ubuntu" | "Astra")
      apt-get update -y
      apt-get install docker-compose -y
      ;;
    "RedHat")
      cp vendor/docker-compose /usr/local/sbin/docker-compose
      chmod +x /usr/local/sbin/docker-compose
      ;;
    "RedOS")
      dnf install -y docker-compose
      ;;
  esac
fi

NLP_IS_RUNNING=""
if [ -f "${COMPOSE_FILE}" ]; then
  NLP_IS_RUNNING=$(docker compose -f "${COMPOSE_FILE}" ps -q django)
fi

if [[ "${NLP_IS_RUNNING}" != "" ]]; then
  echo -e "${GREEN}Stopping services...${DEFAULT}"
  docker compose -f "${COMPOSE_FILE}" down
fi

echo -e "${GREEN}Updating configuration...${DEFAULT}"
if [ ! -f "${WORKDIR}"/.env ]; then
  cp "${INVOKE_DIR}/config.env" "${WORKDIR}"/.env
  sed -i "s|PRODUCT_VERSION=|PRODUCT_VERSION=$(cat "$INVOKE_DIR"/.version)|g" "${WORKDIR}"/.env
else
  OLD_CONFIG_FILE="${WORKDIR}/.env"
  NEW_CONFIG_FILE="${INVOKE_DIR}/config.env"
  TEMP_FILE=$(mktemp)

  while IFS= read -r line; do
    if [[ ${line:0:1} = "#" ]]; then
    	echo "$line" >> "$TEMP_FILE"
    	continue;
    fi
    if (( $(awk -v line="$line" 'BEGIN {print index(line, "=")}') > 1 )); then
        key="${line%%=*}"; key="${key//#}"
        if [[ ${key} = "PRODUCT_VERSION" ]] || [[ ${key} = "SECRET_KEY" ]]; then
          continue;
        fi

        old_value=$(grep "^$key=" "$OLD_CONFIG_FILE" | cut -d '=' -f2-)
        if [[ -n "$old_value" ]]; then
            echo -e "$key=$old_value" >> "$TEMP_FILE"
            continue;
        fi
    fi
      echo "$line" >> "$TEMP_FILE"
  done < "$NEW_CONFIG_FILE"

  # Critical values to be copied from old file:
  for key in "APPLICATION_UID" "POSTGRES_PASSWORD" "REDIS_PASSWORD"; do
    value=$(grep "^$key=" "$OLD_CONFIG_FILE" | cut -d '=' -f2-)
    if [[ -n "$value" ]]; then
       echo -e "$key=$value" >> "$TEMP_FILE"
    fi
  done

  # Values to be filled afresh:
  echo -e "PRODUCT_VERSION=$(cat "$INVOKE_DIR"/.version)" >> "$TEMP_FILE"
  echo -e "SECRET_KEY=$(uuidgen)" >> "$TEMP_FILE"

  cp "${OLD_CONFIG_FILE}" "${OLD_CONFIG_FILE}".old
  mv "$TEMP_FILE" "$OLD_CONFIG_FILE"
  chmod 644 "${WORKDIR}"/.env
  echo -e "${GREEN}Config successfully updated${DEFAULT}"
fi

if [ ! "$(grep '^NLP_HOSTNAME=' "${WORKDIR}"/.env | cut -d '=' -f2-)" ]; then
  if [[ -n ${NLP_DOMAIN+x} ]]; then
    sed -i "s|NLP_HOSTNAME=|NLP_HOSTNAME=https://${NLP_DOMAIN}|g" "${WORKDIR}"/.env
  fi
fi

if [ ! "$(grep '^HOST_IP_ADDRESS=' "${WORKDIR}"/.env | cut -d '=' -f2-)" ]; then
  set +e
  HOST_IP=$(curl -f -s http://whatismyip.akamai.com/)
  set -e
  if [ "${HOST_IP}" ]; then
    sed -i "s|HOST_IP_ADDRESS=|HOST_IP_ADDRESS=https://${HOST_IP}|g" "${WORKDIR}"/.env
  else
    echo -e "${RED}Failed to obtain host IP address. Please edit HOST_IP_ADDRESS parameter in ${WORKDIR}/.env manually."
    exit 1
  fi
fi

# shellcheck disable=SC2046
export $(grep -v '^#' "${WORKDIR}/.env" | xargs)

if [ -x "$(command -v s3cmd)" ]; then
  echo -e "${GREEN}Downloading LLM files...${DEFAULT}"
  mkdir -p "${LLM_DIR}/Vikhr"
  mkdir -p "${LLM_DIR}/ai-forever"

  s3cmd sync --skip-existing --check-md5  --recursive "${S3_LLM_URL}Vikhr/" "${LLM_DIR}/Vikhr/"
  s3cmd sync --skip-existing --check-md5 --recursive "${S3_LLM_URL}ai-forever/" "${LLM_DIR}/ai-forever/"

  if [ ! -f "${LLM_IMAGE}" ]; then
    echo -e "${GREEN}Downloading LLM Docker image...${DEFAULT}"
    s3cmd get "${S3_LLM_URL}Docker/Vikhr/llm.img" "${LLM_IMAGE}"
  fi

else
  echo -e "${RED}Failed to download LLM files. Please install and configure s3cmd${DEFAULT}"
fi

if [ "${NLP_HOSTNAME}" ]; then
  export NGINX_HOSTNAME="${NLP_HOSTNAME##*/}"  # This variable is used in nginx.conf
else
  export NGINX_HOSTNAME="${HOST_IP_ADDRESS##*/}"
fi

echo -e "${GREEN}Checking for existing SSL certificate...${DEFAULT}"
if [ -f "${WORKDIR}"/ssl/cert.crt ] && [ -f "${WORKDIR}"/ssl/cert.key ]; then
  echo -e "${GREEN}SSL certificate found.${DEFAULT}"
else
  echo -e "${RED}SSL certificate not found. ${DEFAULT}"
  while true; do
    echo -e "1) Use your existing certificate"
    echo -e "2) Skip and add SSL certificate later"
    read -r -p "Please choose an option: " cert_option
    if [ "$cert_option" -eq 1 ]; then
      read -r -p "Please enter full path to certificate file: " cert_path
      if [ -f "${cert_path}" ]; then
        cp "${cert_path}" "${WORKDIR}"/ssl/cert.crt
      else
        echo -e "${RED}File not found. ${DEFAULT}"
        continue
      fi
      read -r -p "Please enter full path to private key file: " cert_path
      if [ -f "${cert_path}" ]; then
        cp "${cert_path}" "${WORKDIR}"/ssl/cert.key
      else
        echo -e "${RED}File not found. ${DEFAULT}"
        continue
      fi
      break
    elif [ "$cert_option" -ne 2 ]; then
      echo -e "${RED}Please enter 1 or 2!${DEFAULT}"
      continue
    else
      echo -e "${GREEN}Add SSL certificate manually to ${WORKDIR}/ssl/. File names must be cert.crt and cert.key${DEFAULT}"
      break
    fi
  done
fi
if [ ! -f "${WORKDIR}/ssl/dhparam.pem" ]; then
  echo -e "${GREEN}Generating dhparam... Please wait, this can take long time...${DEFAULT}"
  openssl dhparam -out "${WORKDIR}"/ssl/dhparam.pem 4096
fi

echo -e "${GREEN}Checking for JWT RSA encryption key...${DEFAULT}"
if [ -f "${WORKDIR}"/private/jwt_keys/jwt_key.pub ]; then
  echo -e "${GREEN}RSA encryption key found.${DEFAULT}"
else
  echo -e "${RED}RSA encryption key not found. ${DEFAULT}"
  read -r -p "Please enter path to public RSA key file (ENTER to skip): " jwt_key_path
  if [ "$jwt_key_path" ] ; then
    if [ -f "${jwt_key_path}" ]; then
        cp "${jwt_key_path}" "${WORKDIR}"/private/jwt_keys/jwt_key.pub
        echo -e "${GREEN}RSA encryption key copied. ${DEFAULT}"
    else
      echo -e "${RED}File not found. ${DEFAULT}"
      echo -e "${RED}Add RSA encryption public key to ${WORKDIR}/private/jwt_keys/. File name must be jwt_key.pub${DEFAULT}"
    fi
  else
    echo -e "${GREEN}Add RSA encryption public key to ${WORKDIR}/private/jwt_keys/. File name must be jwt_key.pub${DEFAULT}"
  fi
fi

# shellcheck disable=SC2143
if [ ! "$(grep '^APPLICATION_UID=' "${WORKDIR}"/.env)" ]; then
  echo -e "${GREEN}Generating application UID...${DEFAULT}"
  echo "APPLICATION_UID=$(uuidgen)" >> "${WORKDIR}"/.env
fi

# shellcheck disable=SC2143
if [ ! "$(grep '^POSTGRES_PASSWORD=' "${WORKDIR}"/.env)" ]; then
  echo -e "${GREEN}Generating postgres credentials...${DEFAULT}"
  POSTGRES_PASSWORD=$(uuidgen)
  echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" >> "${WORKDIR}"/.env
fi
echo "DATABASE_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db/${POSTGRES_DB}" >> "${WORKDIR}"/.env

# shellcheck disable=SC2143
if [ ! "$(grep '^REDIS_PASSWORD=' "${WORKDIR}"/.env)" ]; then
  echo -e "${GREEN}Generating redis credentials...${DEFAULT}"
  REDIS_PASSWORD=$(uuidgen)
  echo "REDIS_PASSWORD=${REDIS_PASSWORD}" >> "${WORKDIR}"/.env
fi
echo "REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0" >> "${WORKDIR}"/.env
echo "CACHEOPS_REDIS=redis://:${REDIS_PASSWORD}@redis:6379/1" >> "${WORKDIR}"/.env

if [ -f "${WORKDIR}"/docker-compose.yml ]; then
  cp -f "${WORKDIR}"/docker-compose.yml "${WORKDIR}"/docker-compose.yml.old
fi
cp -f "${INVOKE_DIR}"/{docker-compose.yml,.version,connect_to_sentry.sh} "${WORKDIR}"

echo -e "${GREEN}Load docker images...${DEFAULT}"
for imagefile in ./images/*; do
  docker load --input "${imagefile}"
done

echo -e "${GREEN}Starting services...${DEFAULT}"
for image in "django" "scheduler" "worker-high" "worker-default" "worker-low" "llm_service"; do
  docker compose -f "$COMPOSE_FILE" run -u root --rm --no-deps "${image}" \
    bash -c "chown -R 1001:1001 /tmp && install -d /tmp -o root -g root -m 1777"
done
docker compose -f "$COMPOSE_FILE" up -d

echo -e "${DEFAULT}Waiting for the server to start${DEFAULT}"
attempts_counter=0
max_attempts=150
until curl --output /dev/null --silent --head --fail "http://127.0.0.1:8000/admin"; do
  if [ ${attempts_counter} -eq ${max_attempts} ]; then
    echo -e "\n${RED}Timeout error. Check docker logs. Then restart the installation.${DEFAULT}"
    exit 1
  fi
  printf '.'
  attempts_counter=$((attempts_counter+1))
  sleep 5
done
printf '\n'

echo -e "${GREEN}Clear old docker containers, images and networks...${DEFAULT}"
docker container prune -f
docker image prune -f
docker network prune -f

echo -e "${GREEN}Nlp ${PRODUCT_VERSION} successfully installed.${DEFAULT}"
