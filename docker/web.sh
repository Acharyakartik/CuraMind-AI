#!/bin/sh
set -eu

python manage.py migrate --noinput

if [ "${RUN_COLLECTSTATIC:-0}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

exec python manage.py runserver 0.0.0.0:8000

