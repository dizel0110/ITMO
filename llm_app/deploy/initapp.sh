#!/bin/bash

set -e

python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput
python3 manage.py compilemessages --locale ru
python3 manage.py load_init_data
python3 manage.py createadmin
gunicorn -c nlp/gunicorn.conf.py nlp.asgi:application
