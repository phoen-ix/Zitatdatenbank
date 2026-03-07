#!/bin/sh
set -e

# Ensure bind-mounted directories are writable by appuser
chown appuser:appuser /backups /data 2>/dev/null || true

# Extract compressed data files if not already present
if [ -f /data/data.tar.gz ] && [ ! -f /data/zitate.sql ]; then
    echo "============================================================"
    echo "  Extracting data files from data.tar.gz (~53 MB)..."
    echo "============================================================"
    tar xzf /data/data.tar.gz -C /data/
    echo "  Data files extracted: $(ls -lh /data/*.sql /data/*.csv 2>/dev/null | awk '{print $9, $5}' | tr '\n' ', ')"
fi

exec gosu appuser "$@"
