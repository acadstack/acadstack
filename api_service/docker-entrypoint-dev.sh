#!/bin/sh
# Dev-only entrypoint for docker-compose-local.yml. When AUTO_DEMO_DATA=true
# (set in app_env_vars_debug.env) and the schema hasn't been created yet, it
# runs the same `python demo_data.py config.json` documented in README.md
# once, so a fresh `docker compose up` on an empty ./pgdata volume comes up
# with demo data instead of an empty DB. It never re-runs against a schema
# that already exists, so restarting the containers doesn't wipe local data.
#
# Gated behind AUTO_DEMO_DATA (default off) and only wired up in
# docker-compose-local.yml -- docker-compose.yml's prebuilt demo/deployment
# images keep using the Dockerfile's default `python main.py` CMD directly,
# so this never runs against a real deployment (demo_data.py drops the
# schema first).
set -e

if [ "${AUTO_DEMO_DATA:-false}" = "true" ]; then
  echo "AUTO_DEMO_DATA=true: checking whether the schema is already initialized..."
  if python - <<'PYEOF'
import sys, time
import common as C
import models as M

db_name, db_args = C.db_config_from_env()
M.db.init(db_name, **db_args)

last_err = None
for _ in range(30):
    try:
        M.db.connect()
        break
    except Exception as e:
        last_err = e
        time.sleep(2)
else:
    print(f"Could not reach the database: {last_err}", file=sys.stderr)
    sys.exit(2)

try:
    initialized = M.db.table_exists("schema_migrations")
finally:
    M.db.close()
sys.exit(0 if initialized else 1)
PYEOF
  then
    echo "Schema already initialized; skipping demo data."
  else
    status=$?
    if [ "$status" = "2" ]; then
      echo "Database never became reachable; starting server anyway." >&2
    else
      echo "First run detected; populating demo data..."
      python demo_data.py config.json
    fi
  fi
fi

exec python main.py
