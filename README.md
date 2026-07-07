# EcoPulse — Air Quality & Weather Intelligence for Uzbekistan

A Flask web application that shows live air quality (US EPA AQI) and
weather for all 14 regions of Uzbekistan, with user accounts and an
administrator panel.

## Features

- Landing page, registration and sign-in (passwords stored as salted hashes)
- English / Uzbek language switcher, remembered per device (`translations.py`)
- Dashboard with a national overview card for every region
- **173 districts** across all 14 regions, each fetched by its exact
  coordinates via a cascading searchable picker (region -> district)
- Region pages: current weather, EPA AQI with health advice, a 48-hour
  temperature/PM2.5 chart, multi-day forecast and a six-pollutant breakdown
- Admin panel: total users, total administrators and a full user table.
  The owner's view also folds in the seeded demo accounts (see
  `services/fake_members.py`) with a "Demo" badge only the owner sees;
  plain admins see real accounts and real counts only.
- CSRF-protected forms, role-based access control, gzip response
  compression, cached static assets
- Data from WeatherAPI.com (weather + air quality + forecast in one call),
  cached and prefetched in the background so pages load from memory

## Run locally

```bash
python -m venv venv
venv\Scripts\activate        # Windows  (use `source venv/bin/activate` on macOS/Linux)
pip install -r requirements.txt
flask --app app run --debug
```

Open http://127.0.0.1:5000 — the SQLite database is created automatically.

**The first account you register automatically becomes the administrator.**
Promote more admins later with:

```bash
flask --app app create-admin someone@example.com
```

No internet connection? Run with demo data (clearly labelled in the UI):

```bash
# Windows PowerShell
$env:DEMO_DATA="1"; flask --app app run --debug
```

## Deploy for free (Render)

1. Push this folder to a GitHub repository.
2. Go to https://render.com → New → Blueprint → pick your repo.
   Render reads `render.yaml` and configures everything.
3. Click **Deploy**. Your app gets a public `https://….onrender.com` URL.

## Permanent database (Supabase PostgreSQL)

1. In Supabase: **Project Settings -> Database -> Connection string**.
   Copy the **Session pooler** URI (it works on IPv4 networks like Render).
2. In Render: your service -> **Environment** -> add
   `DATABASE_URL` = that URI (include your password).
3. Redeploy. On boot the app automatically:
   - normalises `postgres://` to `postgresql://` (SQLAlchemy 2 requires it),
   - runs `db.create_all()` inside an app context (Gunicorn-safe), building
     the `users` and `locations` tables if they don't exist,
   - seeds the 173-district dataset into `locations` exactly once.

The PostgreSQL driver (`psycopg2-binary`) is already in `requirements.txt`.
If you ever need to re-run seeding manually: `flask --app app seed-locations`.

## Accuracy, honestly

Forecasts come from WeatherAPI.com, which blends multiple national
weather models and monitoring networks — the same class of sources
commercial weather apps use. No provider on Earth offers 100% accurate
forecasts; that is a physical limit of the atmosphere, not a software
bug. This app therefore reports the official EPA AQI categories that
health agencies designed to be robust to normal forecast error. If a
live reading can't be fetched in time, the app always prefers to show
the most recent successful reading (clearly labelled, with how old it
is) over an empty page.

## Project layout

```
app.py                 Flask app factory, CSRF/CSP, i18n, gzip, error pages, CLI
config.py              Environment-driven configuration
extensions.py          Shared SQLAlchemy / LoginManager instances
translations.py        English/Uzbek text + the t() template helper
models.py              User model (incl. is_fake for seeded demo accounts)
auth.py                Register / login / logout routes
views.py               Landing, dashboard, region pages, language switch route
admin.py               Admin-only panel (owner vs plain-admin visibility)
services/              WeatherAPI client, EPA AQI maths, region catalogue,
                       fake_members.py (demo account generator)
data/                  districts.json — 173 districts with coordinates
templates/             Jinja2 templates
static/                Stylesheet, chart/picker/theme scripts
```
