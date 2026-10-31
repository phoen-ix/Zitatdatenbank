#!/usr/bin/env bash
# The e2e suite (e2e/tests, inventory in e2e/COVERAGE.md): build the prod image,
# start a throwaway stack under its own compose project, run the suite against
# it (the setup project imports the demo quotes), tear everything down again.
#
#   scripts/e2e.sh [playwright args]          e.g. --grep backup, --repeat-each=3
#
# PORT_BASE (default 25600): the app on 127.0.0.1:PORT_BASE.
# COMPOSE_PROJECT_NAME (default zitatdatenbank_e2e): never `zitatdatenbank`,
# the project name of a checkout's own stack. ARTIFACTS: Playwright's test
# results and HTML report, plus the stack log on failure (default: a temp dir).
#
# The stack has no bind mounts (docker-compose.e2e.yml): it never reads
# data/data.tar.gz or a local mariadb-data/, and ignores a local .env.
# Node + `npm ci` in e2e/ are the caller's.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ARTIFACTS="${ARTIFACTS:-$(mktemp -d)}"
mkdir -p "$ARTIFACTS"
export PORT_BASE="${PORT_BASE:-25600}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-zitatdatenbank_e2e}"

case "$COMPOSE_PROJECT_NAME" in
  zitatdatenbank | phytotron | phytotron-dev | vib | fileheron | keyb-dev)
    echo "e2e: refusing the live project name '$COMPOSE_PROJECT_NAME'" >&2
    exit 1 ;;
esac

# Test-only values; the stack reads nothing from a .env (--env-file /dev/null).
export SECRET_KEY=e2e-secret-key-not-a-secret DB_ROOT_PASSWORD=e2e-root-not-a-secret
export DB_PASSWORD=e2e-db-not-a-secret ADMIN_USERNAME=admin ADMIN_PASSWORD=e2e-admin-not-a-secret

compose() {
  docker compose --env-file /dev/null -f docker-compose.yml -f docker-compose.e2e.yml "$@"
}
teardown() {
  rc=$?
  [ "$rc" = 0 ] || compose logs --tail=300 >"$ARTIFACTS/stack.log" 2>&1 || true
  compose down -v --remove-orphans --rmi local || true
  exit "$rc"
}
trap teardown EXIT

compose up -d --build --wait

cd e2e
E2E_BASE_URL="http://localhost:$PORT_BASE" \
  DOCS_ADMIN_USERNAME="$ADMIN_USERNAME" \
  DOCS_ADMIN_PASSWORD="$ADMIN_PASSWORD" \
  DOCS_WEB_CONTAINER="$COMPOSE_PROJECT_NAME-web" \
  DOCS_DB_CONTAINER="$COMPOSE_PROJECT_NAME-db" \
  PLAYWRIGHT_HTML_OUTPUT_DIR="$ARTIFACTS/playwright-report" PLAYWRIGHT_HTML_OPEN=never \
  npx playwright test --output "$ARTIFACTS/test-results" "$@"
