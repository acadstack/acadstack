# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AcadStack: a university academics management system (courses, course offerings, instructors,
students, enrollment, attendance, feedback, grades, fees, DC/PhD workflows). Three-tier app:
Postgres → Quart (Python) API → VueJS 3 SPA. See `docs/architecture.md` for the full architecture
write-up (folder layout, business concept map, RBAC, DAL) — read it before making structural
changes; this file only adds what that doc doesn't cover (commands, gotchas).

## Services

- `api_service/` — backend API (Python, [Quart](https://quart.palletsprojects.com/)), served by
  Hypercorn. Entry point is `acadstack_app.py` (`create_app`); `main.py` runs it. Serves the built
  webapp as static files under `/acadstack/`.
- `frec_service/` — standalone face-recognition microservice (Quart + `face_recognition`/OpenCV),
  entry point `run.py` → `app/api.py`. Called by `api_service` for photo-based attendance
  (`api_faces.py`, `face_api_proxy.py`).
- `webapp/` — VueJS 3 + Vite SPA, hash-based routing (`vue-router` with `createWebHashHistory`).
  Built output is copied into `api_service/app` (or into the Docker image directly, see
  `api_service/Dockerfile`).

## Common commands

### Backend (`api_service`)
```bash
source ~/.venv/AcadStack/bin/activate      # or whatever venv you set up per README.md
pip install -r api_service/requirements.txt
cd api_service
python demo_data.py config.json            # (re)create schema + demo data — DESTRUCTIVE, drops the schema
python main.py                             # run the server (reads APP_PORT etc. from env)
pytest                                     # run backend tests (from api_service/)
pytest tests/test_auth.py                  # run a single test file
pytest tests/test_auth.py::test_login      # run a single test
```
The server needs env vars from `app_env_vars.env` (`source app_env_vars.env`) and a valid
`api_service/config.json` (DB connection, ports, email, OAuth). `api_service/tests/config_test.json`
is the config used by the test suite.

`api_service/tests/conftest.py` provides the `client`/`auth`/`db`/`app` pytest fixtures (a real,
throwaway Postgres schema — see its module docstring for setup) that `test_auth.py` and the rest of
the suite depend on.

### Frontend (`webapp`)
```bash
cd webapp
npm install
npm run dev        # Vite dev server with hot reload
npm run build       # vite build && replace-html-vars.js -> outputs to webapp/dist
npm run preview     # serve the production build locally (port 4173)
npm run lint         # eslint --fix over .vue,.js,.jsx,.cjs,.mjs
```
`replace-html-vars.js` runs after `vite build` to inject env-driven values into the built HTML —
don't skip it when testing a production build manually.

### Face recognition service (`frec_service`)
```bash
cd frec_service
pip install -r requirements.txt
python run.py       # reads FREC_PORT from env
```
`frec_service/test/test_face_service.py` is a manual script (not pytest) that POSTs to a running
instance at `API_URL` — start the service first, then run it directly with `python`.

### Docker
- `docker-compose-local.yml` builds images locally from source (uses `app_env_vars_debug.env`).
- `docker-compose.yml` / `docker-dist/` pull prebuilt images (`sodhix/acadstack-backend`,
  `sodhix/acadstack-frec-service`) for demo/deployment (see `DEMO_DEPLOY.md`).
- Cross-arch image builds require `docker buildx` (see README.md for the exact buildx sequence);
  needed e.g. building `linux/amd64` images on Apple Silicon.
- Services/ports: backend `APP_PORT` (default 5300), frec `FREC_PORT` (default 5060), Postgres
  `DB_PORT` (default 5432, `db` hostname inside compose).

## Architecture notes (beyond docs/architecture.md)

- **Routing**: each `api_*.py` module owns one business area and registers its own routes in an
  `init_routes(bp: Blueprint)` function; `acadstack_app.py`'s `create_app` wires all blueprints
  together. When adding a new endpoint, add it in the relevant `api_*.py` module's `init_routes`,
  not in `acadstack_app.py`.
- **RBAC**: authority is granted through named permissions (`permissions.py`, e.g. `course.save`,
  `grades.export`), not raw role lists at each call site. Enforced via the `@rbac(permissions=[...])`
  decorator (`common.py`) on route handlers, `apiVC.has_permission(name)`/`Actor.can(name)` for
  finer-grained checks, and `nav.json` entries naming a permission for frontend nav visibility
  (`webapp/src/main.js`'s `hasPermission()`). The permission→role mapping itself is DB-backed (the
  `"permission"` settings group — see Configuration below), edited through
  `permissions.save_permission_mapping()`, not by editing `permissions.py`'s defaults after initial
  rollout. Role codes (`ACA`, `DEA`, `HOD`, `FAC`, `STU`, `RES`, `SUP`, `GUE`, `PLA`, `ADV`) live in
  `vocab_defaults.ROLES`. Pure role-*identity* checks that aren't authorization decisions (e.g. "this
  actor is a student, scope the query to their own records") still use
  `is_user_in_role()`/`Actor.has_role()`. See docs/architecture.md's RBAC section.
- **Data access**: PeeWee ORM models in `models.py`; some queries run as raw SQL against the PeeWee
  `db` object, defined in `sql_statements.toml` rather than inline in Python.
- **Config-driven UI**: `api_service/nav.json` drives the frontend navigation structure (an entry may
  also gate on `"restrictToDegree"`, e.g. the PhD menu). Dropdown labels/values come from
  `vocab_defaults.py` via `settings_store`/`static_data_dict()` — there is no `static_data.json` file
  to edit any more (see Configuration below). Prefer editing `vocab_defaults.py`/the admin Settings
  screen over hardcoding lists in Vue components.
- **Background tasks**: `bg_tasks.py` / `tasks_helper.py` (APScheduler) handle async/scheduled
  work (e.g. report generation, email); `app.extensions['tasks']` holds their state.
- **Reports & email**: `report_templates/` (HTML, rendered via WeasyPrint/pdfkit) and
  `email_templates/` are used by `api_reports.py` / `create_email.py` / `email_client.py`.
- **Frontend routes**: `webapp/src/router/index.js` maps components to hash routes;
  `webapp/src/App.vue` is the post-login entry point.
- **Configuration**: institution-configurable settings/vocabularies live in the DB
  (`settings_store.py`, the `SystemSetting` table), not `config.json` — only bootstrap items
  (DB connection, secrets, ports) stay in config/env. Rules whose past values must keep applying to
  past academic sessions (the grade point map) are versioned policy instead (`policy_store.py`, the
  `PolicyVersion` table — insert-only, never update/delete). Both have an admin GUI
  (`#/admin.settings`, `#/admin.policy`, gated by `system.manage_settings`/
  `system.manage_academic_policy`) and a full export/import of the whole configuration as one JSON
  document (`config_transfer.py`, `#/admin.config_transfer`, `system.export_config`/
  `system.import_config`). Deleting a vocabulary code still referenced by a business-table row,
  another setting, or a workflow transition is blocked by `config_integrity.py`, not silently
  allowed. See docs/architecture.md's "System settings"/"Versioned academic policy" sections for the
  full design.
