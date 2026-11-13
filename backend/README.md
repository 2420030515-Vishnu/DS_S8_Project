# Flask API

## Install and run (PowerShell)

Run these commands from the repository root. They create a local virtual environment, install the backend dependencies, initialize SQLite, run pytest, and start Flask. The generated secret is written only to ignored `.env`.

```powershell
py -3 -m venv backend\.venv
& .\backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt

if (-not (Test-Path .env)) { Copy-Item .env.example .env }
$dashboardEnv = Get-Content .env -Raw
$placeholder = 'replace-with-a-random-secret-generated-for-this-installation'
if ($dashboardEnv.Contains($placeholder)) {
    $dashboardSecret = python -c "import secrets; print(secrets.token_hex(32))"
    $dashboardEnv = $dashboardEnv.Replace($placeholder, $dashboardSecret)
    Set-Content .env -Value $dashboardEnv -Encoding ascii
}

flask --app backend.app init-db
python -m pytest backend\tests data_science\tests -q
python -m backend.app
```

`create_app` also creates the schema if it is missing, so repeated starts are safe. `flask --app backend.app init-db` is an explicit, idempotent initialization step. The service listens on `127.0.0.1:5000` by default. The frontend origin is restricted to `http://localhost:5173`; set `FRONTEND_ORIGINS` to an explicit comma-separated allow-list when needed. In production, use HTTPS and set `APP_ENV=production` so session cookies are marked Secure.

Configuration comes from environment variables or the optional root `.env` file. `.env.example` contains only a placeholder. `FLASK_SECRET_KEY` must be a private random string of at least 32 characters; the server refuses the placeholder or a missing/short key. Set `DATABASE_PATH` and `COVID_DATA_DIR` to override their defaults.

## Data sources and calculations

| API subject | Authoritative file | Measures and handling |
|---|---|---|
| National daily/cumulative | `backend/data/nation_level_daily.csv` | `Daily *` are source daily reports; `Total *` are source cumulative values. Summary uses the latest row's cumulative totals, never a sum of rows. Dates without a year are sequenced from the archive's 2020 start, with year increments on December-to-January rollover. |
| State history | `backend/data/state_level_daily.csv` | `Confirmed`, `Recovered`, and `Deceased` are cumulative by state/date. State names are matched using trimmed, whitespace-collapsed, case-folded keys while original labels are returned. Daily differences are optional derived values; negative revisions are retained and a first observation without a prior record is null. |
| Latest state snapshot | `backend/data/state_level_latest.csv` | `Confirmed`, `Recovered`, `Deaths`, and `Active`. The aggregate `Total` row is excluded from region rankings. |
| District snapshot | `backend/data/district_level_latest.csv` | `Confirmed`, `Active`, `Recovered`, and `Deceased`. This file is a snapshot, so no district history is claimed. |
| National testing | `backend/data/tests_day_wise.csv` | Source testing counts and source-reported positivity. No positivity rate is recomputed using a case series from another date. |
| State testing | `backend/data/tests_state_wise.csv` | State-specific update dates and source-reported values. Latest row per state is selected by that state's update date; updates are not treated as synchronized. |

`complete.csv`, `datasets/states.csv`, `datasets/districts.csv`, and the other root exports overlap these dedicated files and are not added to any API totals. Duplicate observations retain the last row in source order for a given date/geography. Invalid numeric strings and blanks become null; invalid dates are omitted from time-series calculations. Missing required files return a JSON 503 error. Source file reads and normalized frames are cached using file path, modification time, and size as the cache key.

## Endpoints and query parameters

All endpoints are under `/api`. Date filters are inclusive `YYYY-MM-DD`; if both are provided, `start` must be no later than `end`. Unsupported filters/metrics return HTTP 400 with `{ "error", "code": "invalid_query" }`. Missing required data returns HTTP 503. No endpoint describes historical records as live.

### Health and authentication

- `GET /api/health` — service health and `historical_data: true`.
- `GET /auth/csrf` — creates/returns the session's CSRF token. Send it in `X-CSRF-Token` for every POST/PUT/PATCH/DELETE API request.
- `POST /auth/register` — JSON `{ "name", "email", "password" }`; name 2–100 chars, valid email, password 8–128 chars. Returns 201; duplicate email returns 409.
- `POST /auth/login` — JSON `{ "email", "password" }`; generic 401 for invalid credential pairs.
- `GET /auth/me` — actual authenticated profile or `{ "user": null }`.
- `POST /auth/logout` — clears the session.
- `GET /auth/preferences`, `PUT /auth/preferences` — requires a session. PUT body is a JSON object up to 8 KB.

Passwords are Werkzeug hashes. SQLite stores a unique normalized email and a password hash, never the plaintext password. Session cookies are HttpOnly, SameSite=Lax, eight-hour permanent sessions; production defaults to Secure. The signed cookie contains a random session token, while SQLite stores only its SHA-256 digest, user id, and expiration in `auth_sessions`. Logout revokes that row, so replaying a copied but correctly signed cookie does not restore access. CSRF tokens are checked for unsafe methods. Account preferences are user-scoped.

### Analytics and data

- `GET /dashboard/summary` — latest national cumulative and daily source fields, plus national coverage.
- `GET /dashboard/trends?start=&end=&metric=&state=&district=` — national series by default. National `metric` is one of `Daily Confirmed`, `Total Confirmed`, `Daily Recovered`, `Total Recovered`, `Daily Deceased`, `Total Deceased`; returns at most 500 rows. A state filter uses the state history source and supports `Confirmed`, `Recovered`, `Deceased` plus `daily_confirmed`, `daily_recovered`, or `daily_deceased` derived differences. A district trend request returns 400 because the available district file is snapshot-only.
- `GET /analytics/states?start=&end=&state=&metric=&sort_by=&sort_order=` — without dates, uses the latest state snapshot (`Confirmed`, `Recovered`, `Deaths`, `Active`). With a date filter, uses state daily history and only supports `Confirmed`, `Recovered`, `Deceased`. `sort_order` is `asc` or `desc`.
- `GET /analytics/state-comparison?state=Karnataka&state=Maharashtra&start=&end=&metric=` — `state` may be repeated or use comma-separated `states=`; maximum 10. Metric is `Confirmed`, `Recovered`, or `Deceased`; output includes each state's own observation date within the common selected period.
- `GET /analytics/districts?state=&district=&start=&end=&metric=&sort_by=&sort_order=` — case-insensitive state/district filters over the latest snapshot. Metric is `Confirmed`, `Active`, `Recovered`, or `Deceased`.
- `GET /analytics/testing?level=national|state&start=&end=&state=&metric=` — national testing time series by default; `level=state` returns latest per-state updates in the selected date window. Positivity is returned as the source reports it.
- `GET /data/explorer?dataset=&q=&state=&district=&start=&end=&metric=&min_value=&max_value=&sort_by=&sort_order=&limit=&offset=` — datasets: `national`, `states`, `districts`, `testing`, `testing_states`. `limit` is 1–500; `offset` is 0–1,000,000. Metric thresholds require a supported numeric measure. Search is literal substring matching across source fields.
- `GET /metadata` — archive source, actual date coverage, columns, row counts, source availability, and limitations.
- `GET /insights?start=&end=` — peak daily national value and first-to-last difference over returned records, plus the largest latest-state snapshot total when available. Each result gives its calculation and period/source context.

Compatibility aliases used by the existing frontend are retained: `/meta`, `/national`, `/states`, `/districts`, `/testing`, `/testing/states`, and `/explore`.

## Tests

The pytest suite uses temporary CSV fixtures and a temporary SQLite database. It covers registration/hash/uniqueness, CSRF and protected preferences, invalid credentials, source errors, cumulative aggregation correctness, date/state filters, district snapshot behavior, testing source rates, insights, sorting, and pagination.
