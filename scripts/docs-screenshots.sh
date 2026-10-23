#!/usr/bin/env bash
# Regenerate the docs screenshots: build the prod image, start a throwaway
# stack under its own compose project, seed the demo quotes, run the docs tour
# (e2e/docs/) against it, tear everything down again.
#
#   scripts/docs-screenshots.sh [outdir]      # default: docs/screenshots
#
# PORT_BASE (default 25600): the app on 127.0.0.1:PORT_BASE.
# COMPOSE_PROJECT_NAME (default zitatdatenbank_docs): never `zitatdatenbank`,
# the project name of a checkout's own stack. ARTIFACTS: where Playwright's
# test results go (default: a temp dir).
#
# The stack has no bind mounts (docker-compose.e2e.yml), so it never reads
# data/data.tar.gz or a local mariadb-data/, and ignores a local .env.
# Node + `npm ci` in e2e/ are the caller's.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="$(mkdir -p "${1:-docs/screenshots}" && cd "${1:-docs/screenshots}" && pwd)"
ARTIFACTS="${ARTIFACTS:-$(mktemp -d)}"
export PORT_BASE="${PORT_BASE:-25600}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-zitatdatenbank_docs}"

case "$COMPOSE_PROJECT_NAME" in
  zitatdatenbank | phytotron | phytotron-dev | vib | fileheron | keyb-dev)
    echo "docs-screenshots: refusing the live project name '$COMPOSE_PROJECT_NAME'" >&2
    exit 1 ;;
esac

# Test-only values; the stack reads nothing from a .env (--env-file /dev/null).
export SECRET_KEY=docs-secret-key-not-a-secret DB_ROOT_PASSWORD=docs-root-not-a-secret
export DB_PASSWORD=docs-db-not-a-secret ADMIN_USERNAME=admin ADMIN_PASSWORD=docs-admin-not-a-secret

compose() {
  docker compose --env-file /dev/null \
    -f docker-compose.yml -f docker-compose.e2e.yml -f docker-compose.docs.yml "$@"
}
teardown() {
  rc=$?
  [ "$rc" = 0 ] || compose logs --tail=200 >"$ARTIFACTS/stack.log" 2>&1 || true
  compose down -v --remove-orphans --rmi local || true
  exit "$rc"
}
trap teardown EXIT

compose up -d --build --wait

cd e2e
E2E_BASE_URL="http://localhost:$PORT_BASE" \
  DOCS_SCREENSHOT_DIR="$OUT" \
  DOCS_ADMIN_USERNAME="$ADMIN_USERNAME" \
  DOCS_ADMIN_PASSWORD="$ADMIN_PASSWORD" \
  DOCS_WEB_CONTAINER="$COMPOSE_PROJECT_NAME-web" \
  DOCS_DB_CONTAINER="$COMPOSE_PROJECT_NAME-db" \
  npx playwright test -c playwright.docs.config.ts --output "$ARTIFACTS/test-results"
echo "docs-screenshots: $(find "$OUT" -name '*.png' | wc -l) PNGs in $OUT"
