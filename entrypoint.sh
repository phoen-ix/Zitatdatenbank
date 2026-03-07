#!/bin/sh
set -e

# Ensure bind-mounted directories are writable by appuser
chown appuser:appuser /backups /data 2>/dev/null || true

# Extract compressed data files if not already present
if [ -f /data/data.tar.gz ] && [ ! -f /data/zitate.sql ]; then
    echo "Extracting data files from data.tar.gz..."
    tar xzf /data/data.tar.gz -C /data/
    echo "Data files extracted."
fi

exec gosu appuser "$@"
