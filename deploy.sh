#!/usr/bin/env bash
# Run on the Linux server from an existing, configured installation.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ "${1:-}" != "--apply" ]]; then
  command -v flock >/dev/null
  exec 9>.deploy.lock
  flock -n 9 || { echo 'Another deployment is running.' >&2; exit 1; }
  [[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo 'Commit or resolve local tracked changes before deploying.' >&2; exit 1; }
  git pull --ff-only
  exec bash ./deploy.sh --apply
fi

[[ -f .env && -f db.sqlite3 ]] || { echo 'Existing .env and db.sqlite3 are required. This command updates an existing installation.' >&2; exit 1; }
docker compose version >/dev/null
integration_version=$(tr -d '\r\n' < integration-version.txt)
[[ "$integration_version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || exit 1
integration_url=https://github.com/bobantonbob/anma-cloud.git
if [[ ! -e ha_integration ]]; then
  git clone --depth 1 --branch "$integration_version" "$integration_url" ha_integration
else
  [[ -d ha_integration/.git ]] || { echo 'ha_integration exists but is not a Git checkout. Move it aside before deploying.' >&2; exit 1; }
  [[ "$(git -C ha_integration remote get-url origin)" == "$integration_url" ]] || { echo 'Unexpected integration remote.' >&2; exit 1; }
  [[ -z "$(git -C ha_integration status --porcelain --untracked-files=no)" ]] || { echo 'Integration has local tracked changes.' >&2; exit 1; }
  git -C ha_integration fetch origin "refs/tags/$integration_version:refs/tags/$integration_version"
  git -C ha_integration checkout --detach "$integration_version"
fi

# Build before stopping the current service. Dockerfile collects static assets.
docker compose build anma-cloud
docker compose run --rm --no-deps anma-cloud python manage.py check
umask 077
mkdir -p .backups
backup=".backups/db-$(date -u +%Y%m%dT%H%M%SZ)-$$.sqlite3"
docker compose stop anma-cloud
trap 'echo "Deployment failed. Database backup: $backup. Service may be stopped; inspect the error before restarting. No automatic database rollback was attempted." >&2' ERR
# SQLite backup API includes committed WAL data; never replace the live database.
docker compose run --rm --no-deps -T anma-cloud python -c 'import sqlite3,sys; source=sqlite3.connect("file:/app/db.sqlite3?mode=ro",uri=True); target=sqlite3.connect(":memory:"); source.backup(target); sys.stdout.buffer.write(target.serialize())' > "$backup"
[[ -s "$backup" ]]
docker compose run --rm --no-deps anma-cloud python manage.py migrate --noinput
docker compose up -d --no-deps --wait --wait-timeout 120 anma-cloud
trap - ERR
printf 'Deployment complete. Integration: %s. Database backup: %s\n' "$integration_version" "$backup"
