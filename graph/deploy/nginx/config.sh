#!/bin/sh

# shellcheck disable=SC2016
envsubst '\$NGINX_HOSTNAME' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
