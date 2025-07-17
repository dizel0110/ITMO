#!/bin/bash

set -e

python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput
python3 manage.py compilemessages --locale ru
gunicorn -c ai_photoenhancer/gunicorn.conf.py ai_photoenhancer.asgi:application
