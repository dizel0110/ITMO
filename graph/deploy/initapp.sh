#!/bin/bash

set -e

python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput
python3 manage.py compilemessages --locale ru
python3 manage.py load_init_data
python3 manage.py get_annoy_indexes
python3 manage.py install_labels
gunicorn -c akcent_graph/gunicorn.conf.py akcent_graph.asgi:application
