#!/bin/sh
set -eu

# With SQLite (single file DB) concurrent `migrate` calls can race and crash.
# This script waits until migrations are fully applied by the `web` service.

max_seconds="${MIGRATION_WAIT_SECONDS:-120}"
sleep_seconds="${MIGRATION_WAIT_SLEEP_SECONDS:-2}"

start="$(date +%s)"
while true; do
  if output="$(python manage.py showmigrations 2>/dev/null)"; then
    if printf "%s" "$output" | grep -qE "^[[:space:]]*\\[[[:space:]]\\]"; then
      : # pending migrations
    else
      exit 0
    fi
  fi

  now="$(date +%s)"
  if [ $((now - start)) -ge "$max_seconds" ]; then
    echo "Timed out waiting for Django migrations (${max_seconds}s)." >&2
    python manage.py showmigrations || true
    exit 1
  fi

  sleep "$sleep_seconds"
done

