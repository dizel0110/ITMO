#!/bin/bash

# Define the directory containing the script
INVOKE_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

CONFIG_ENV="${INVOKE_DIR}/config.env"

# Check if config.env exists
if [ ! -f "${CONFIG_ENV}" ]; then
    echo "Config file not found!"
    exit 1
fi

# Extract specific variables from the config file
WORKDIR_PATH=$(grep "^WORKDIR_PATH=" "${CONFIG_ENV}" | cut -d '=' -f2)
WITH_SENTRY=$(grep "^WITH_SENTRY=" "${CONFIG_ENV}" | cut -d '=' -f2)

# Check if WORKDIR_PATH is set
if [ -z "${WORKDIR_PATH}" ]; then
    echo "WORKDIR_PATH is not defined in config.env."
    exit 1
else
    echo "WORKDIR_PATH is defined in config.env."
fi

ENV_FILE="${WORKDIR_PATH}/.env"

# Check if .env file exists
if [ ! -f "${ENV_FILE}" ]; then
    echo ".env file not found!"
    exit 1
fi

# Check if WITH_SENTRY is set in config.env and update if necessary
if [ -n "${WITH_SENTRY}" ]; then
    echo "WITH_SENTRY is defined in ${CONFIG_ENV}."
    if [ "${WITH_SENTRY}" = "True" ]; then
        echo "WITH_SENTRY is already set to True."
    else
        echo "Updating WITH_SENTRY to True."
        sed -i.old "s|^WITH_SENTRY=.*|WITH_SENTRY=True|g" "${CONFIG_ENV}"
        sed -i.old "s|^WITH_SENTRY=.*|WITH_SENTRY=True|g" "${ENV_FILE}"
    fi
else
    echo "WITH_SENTRY is not defined in ${CONFIG_ENV}."
    exit 1
fi

# Ask the user if they wish to set the Sentry DSN key
while true; do
    read -r -p "Do you wish to set DSN Sentry key? [yes/no] " yn
    case $yn in
        [Yy]* )
            read -r -p 'Please, insert Sentry DSN key: ' sentry_dsn

            if grep -q "^SENTRY_DSN=" "${ENV_FILE}"; then
                while true; do
                    read -r -p "Sentry DSN key already set, do you want to overwrite it? [yes/no] " yn
                    case $yn in
                        [Yy]* )
                            sed -i.old "s|^SENTRY_DSN=.*|SENTRY_DSN=${sentry_dsn}|g" "${ENV_FILE}"
                            sed -i.old "s|^WITH_SENTRY=.*|WITH_SENTRY=True|g" "${ENV_FILE}"
                            break
                            ;;
                        [Nn]* )
                            exit
                            ;;
                        * )
                            echo "Please answer yes or no."
                            ;;
                    esac
                done
            else
                echo "SENTRY_DSN=${sentry_dsn}" >> "${ENV_FILE}"
            fi

            exit
            ;;
        [Nn]* )
            exit
            ;;
        * )
            echo "Please answer yes or no."
            ;;
    esac
done
