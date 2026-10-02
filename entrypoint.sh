#!/bin/bash
# Boots MariaDB (unix socket only, no network), seeds it, then starts the web app.
set -euo pipefail

DB_NAME="${DB_NAME:-vault}"
DB_USER="${DB_USER:-ctf}"
DB_PASS="${DB_PASS:-ctfpass}"
PORT="${PORT:-5000}"
STOP=0

if [ -z "${FLAG:-}" ]; then
  echo "[entrypoint] WARNING: FLAG is not set, the app will use a placeholder flag" >&2
fi

mkdir -p /run/mysqld
chown mysql:mysql /run/mysqld

if [ ! -d /var/lib/mysql/mysql ]; then
  echo "[entrypoint] initializing MariaDB data directory"
  mariadb-install-db --user=mysql --datadir=/var/lib/mysql >/dev/null
fi

echo "[entrypoint] starting MariaDB"
mariadbd \
  --user=mysql \
  --datadir=/var/lib/mysql \
  --socket=/run/mysqld/mysqld.sock \
  --pid-file=/run/mysqld/mysqld.pid \
  --skip-networking \
  --skip-name-resolve \
  --performance-schema=OFF \
  --innodb-buffer-pool-size=32M \
  --key-buffer-size=8M \
  --max-connections=30 &
DB_PID=$!

ready=0
for _ in $(seq 1 60); do
  if mariadb-admin --silent ping >/dev/null 2>&1; then
    ready=1
    break
  fi
  if ! kill -0 "$DB_PID" 2>/dev/null; then
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "[entrypoint] MariaDB failed to start" >&2
  exit 1
fi

echo "[entrypoint] seeding database"
mariadb <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`;
SQL
mariadb "${DB_NAME}" < /app/init.sql
# The web app's DB user can only SELECT, so players can't modify anything.
mariadb <<SQL
CREATE OR REPLACE USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT SELECT ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "[entrypoint] starting web app on port ${PORT}"
gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers 2 \
  --user ctf --group ctf \
  --access-logfile - \
  --error-logfile - \
  app:app &
WEB_PID=$!

cleanup() {
  kill "$WEB_PID" "$DB_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap 'STOP=1; cleanup' TERM INT

# Exit as soon as either process dies so the platform restarts the container.
wait -n || true
if [ "$STOP" -eq 1 ]; then
  exit 0
fi
echo "[entrypoint] a process exited unexpectedly, shutting down" >&2
cleanup
exit 1
