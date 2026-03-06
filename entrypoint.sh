#!/bin/sh
set -e

# Ensure bind-mounted directories are writable by appuser
chown appuser:appuser /backups /data 2>/dev/null || true

exec gosu appuser "$@"
