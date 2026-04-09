#!/bin/sh
set -eu

sh docker/wait_for_migrations.sh

exec celery -A curamind_ai beat -l info
