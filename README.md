# India COVID-19 Data Analytics Dashboard

A full-stack application for exploring and analyzing the historical COVID-19 data archived in this repository. It is an academic analytics project, **not a live surveillance service**; the dashboard reports source coverage dates and does not imply current case conditions.

## Features

- Account registration and login with Werkzeug password hashes, CSRF-protected HttpOnly sessions, SQLite session revocation, and account-scoped saved preferences.
- National daily and cumulative trends; state rankings and comparisons; district snapshot analysis; and testing trends where the source supports them.
- Searchable, sortable and paginated data explorer with filtered CSV export.
- API-derived insights, source and methodology notes, actual data date coverage, loading/error/empty states, and responsive navigation.
- Reproducible Pandas/NumPy data profiling, EDA and chart generation that writes derived artifacts separately from the source CSVs.

## Architecture and technologies

| Layer | Implementation |
|---|---|
| Frontend | React, Vite, JavaScript, CSS, Recharts, lucide-react |
| API | Python Flask, Flask-CORS, Pandas, NumPy |
| Authentication and persistence | SQLite, Werkzeug password hashing, signed HttpOnly cookie sessions and CSRF tokens |
| Data science | Pandas, NumPy, Matplotlib and Seaborn |
| Automated checks | pytest, oxlint and Vite production build |

The React single-page application calls the Flask JSON API. The backend services load and normalize the designated CSV sources and provide metadata and aggregates. SQLite stores user accounts, revocable session records and preferences. The data-science pipeline profiles the repository sources independently and saves reports/plots under `data_science/outputs/`. Detailed API and processing behavior is documented in [backend/README.md](backend/README.md) and [data_science/README.md](data_science/README.md).

## Repository layout

```text
backend/                 Flask app, routes, services, SQLite layer, API tests and analytic CSVs
data_science/            Profiling, preprocessing, EDA, visualizations, tests and generated outputs
datasets/                Original source CSV datasets (preserved)
frontend/                React/Vite app, reusable components, API client and frontend documentation
api.ipynb                Historical research notebook; not required to run the app
web_scraping.ipynb       Historical notebook; not required to run the app
```

## Data sources and interpretation

API analytics use the dedicated files in `backend/data/` for their documented metric and aggregation levels. In particular, `nation_level_daily.csv` distinguishes daily reported values from cumulative totals; cumulative values are taken from observations and never summed across dates. The district API source is a snapshot, so it does not support historical district trends. Testing data can be irregular and asynchronous across states; source-reported positivity is retained, and a new positivity rate is not calculated by joining incompatible case and test observations. Overlapping exports are not added together.

The independent data-science source register, exact parsed date ranges, row counts, data-quality findings, missingness, duplicate keys, and calculation limitations are recorded in [data_science/README.md](data_science/README.md) and its reproducible `data_science/outputs/profile_and_eda.json` report. Original CSVs and project documents are inputs and are not overwritten by the pipeline.

## Requirements

- Python 3.10 or later and `pip`
- Node.js and npm (use the versions supported by the installed Vite release)
- PowerShell for the commands below

## Clean setup and run (PowerShell)

Run from the repository root. In the first terminal, create the Python environment, install dependencies, create a private local secret, initialize SQLite, and start Flask:

```powershell
py -3 -m venv backend\.venv
& .\backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
$envText = Get-Content .env -Raw
$placeholder = 'replace-with-a-random-secret-generated-for-this-installation'
if ($envText.Contains($placeholder)) {
    $secret = python -c "import secrets; print(secrets.token_hex(32))"
    $envText = $envText.Replace($placeholder, $secret)
    Set-Content .env -Value $envText -Encoding ascii
}
flask --app backend.app init-db
python -m backend.app
```

In a second terminal, install the locked frontend dependencies and start Vite:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open **http://localhost:5173**. The API listens at **http://127.0.0.1:5000** by default, and its health check is `/api/health`. The default API base URL is `http://localhost:5000/api`; set `VITE_API_URL` in `frontend/.env.local` if it differs. Root `.env.example` contains placeholders only; do not commit a real `.env` or production secret. Configure `FRONTEND_ORIGINS` as an explicit comma-separated CORS allow-list. Use HTTPS and production configuration when deploying.

## Database and environment

The backend creates the SQLite schema on startup; `flask --app backend.app init-db` is the explicit, repeatable initialization command. Defaults and all supported variables are listed in `.env.example` and described in [backend/README.md](backend/README.md). `FLASK_SECRET_KEY` must be replaced with a private random value of at least 32 characters. `DATABASE_PATH` and `COVID_DATA_DIR` can override the local defaults. Do not reuse the development secret in a deployed environment.

## Tests and build checks

From the repository root with the backend virtual environment activated:

```powershell
python -m pytest backend\tests data_science\tests -q
```

From `frontend/`:

```powershell
npm run lint
npm run build
```

The API tests use temporary databases and CSV fixtures plus the real source-data contract where applicable. Browser-level navigation, visual appearance at physical device sizes, and console behavior require manual browser review; see the checklist in [frontend/README.md](frontend/README.md).

To regenerate the data profile and analysis outputs from the repository root:

```powershell
python -m data_science.eda --output data_science/outputs
```

This process reads the registered datasets and writes report/chart artifacts only into the specified output directory.

## API documentation

All routes are prefixed with `/api`. See [backend/README.md](backend/README.md) for request bodies, parameters, validation, authentication and response details. Main endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Service and historical-data health |
| `POST /auth/register`, `POST /auth/login` | Create an account or authenticate |
| `GET /auth/me`, `POST /auth/logout` | Check current session or revoke it |
| `GET /dashboard/summary`, `GET /dashboard/trends` | National summary and filtered series |
| `GET /analytics/states`, `/analytics/state-comparison`, `/analytics/districts`, `/analytics/testing` | Geographic and testing analytics |
| `GET /data/explorer` | Filtered and paginated source records |
| `GET /metadata`, `GET /insights` | Source coverage and data-derived insights |

Authentication uses a CSRF token for unsafe requests. User profile/preferences operations require a valid session. Read-only historical analytics are available as documented in the backend API guide; the frontend itself protects dashboard pages behind login.

## Known limitations

- All dashboard values are historical archive observations. They are not current public-health statistics.
- Dataset coverage differs by source and ends at the dates listed in the source register; there is no live data feed.
- District observations are snapshots, not a complete daily district time series.
- State testing updates may not be synchronized. Positivity rates are not recalculated from mismatched sources or dates.
- Missing values, invalid dates, negative revisions and duplicate keys are reported or handled according to the field/source policy; they are not generically filled with zero.
- The two notebooks are preserved as historical artifacts and are not part of application startup. They may reference retired sources or contain cells that write files.
- Responsive design and browser workflows have a manual checklist; automated build/tests do not substitute for a real browser/device review.

## Project documents

The original notebooks, presentations and project documents remain in the repository. Review [frontend/README.md](frontend/README.md), [backend/README.md](backend/README.md), and [data_science/README.md](data_science/README.md) for layer-specific details.
