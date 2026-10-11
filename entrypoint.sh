#!/bin/sh
set -e

# Ensure bind-mounted directories are writable by appuser
chown appuser:appuser /backups /data 2>/dev/null || true

# Extract compressed data files if not already present
if [ -f /data/data.tar.gz ] && [ ! -f /data/zitate.sql ]; then
    # data.tar.gz lives in Git LFS. A clone made without git-lfs only has the
    # ~130-byte pointer file, which tar would reject with a cryptic error.
    if head -c 64 /data/data.tar.gz | grep -q '^version https://git-lfs\.github\.com/spec/'; then
        echo "============================================================" >&2
        echo "  ERROR: data/data.tar.gz is a Git LFS pointer, not the data archive." >&2
        echo "  Install git-lfs and fetch the real file in the repository:" >&2
        echo "      git lfs install && git lfs pull" >&2
        echo "  then start again: docker compose up -d" >&2
        echo "============================================================" >&2
        exit 1
    fi
    echo "============================================================"
    echo "  Extracting data files from data.tar.gz (~53 MB)..."
    echo "============================================================"
    tar xzf /data/data.tar.gz -C /data/
    echo "  Data files extracted: $(ls -lh /data/*.sql /data/*.csv 2>/dev/null | awk '{print $9, $5}' | tr '\n' ', ')"
fi

exec gosu appuser "$@"
