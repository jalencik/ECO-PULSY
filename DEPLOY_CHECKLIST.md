# ECO PULSY — Final Deployment Checklist

Everything in code is done and tested. These are the only steps left,
in order. Total time: about 10 minutes.

## 0. Security first (2 min) — IMPORTANT

Your Supabase database password was shared in a chat. Rotate it before
going live:

1. Supabase dashboard -> Project Settings -> Database -> **Reset database
   password**. Save the new password somewhere safe (not in code).
2. Your connection string (used in step 2 below) becomes:
   `postgresql://postgres.uaimqpqzenwyedrezlsv:NEW_PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres?sslmode=require`

Never paste this string into any file in this folder — only into
Render's environment settings. The `.gitignore` protects `.env`, but the
safest secret is one that never touches disk.

## 1. Push to GitHub (3 clicks)

1. Right-click an empty spot inside the `ECO PULSE` folder in File
   Explorer -> **Open with Code** (or open VS Code -> File -> Open Folder).
2. Click the **Source Control** icon in the left bar (branch symbol).
3. Click **Publish to GitHub** -> choose
   **Publish to GitHub public repository** -> name it `eco-pulsy` -> Enter.
   Sign in with GitHub if asked. VS Code commits and pushes everything
   (venv, database and caches are excluded by `.gitignore`).

## 2. Deploy on Render (5 min)

1. https://dashboard.render.com -> **New** -> **Blueprint**.
2. Connect your GitHub account if needed -> pick the `eco-pulsy` repo.
   Render reads `render.yaml` automatically (service name: eco-pulsy,
   free plan, Gunicorn, Python 3.12).
3. Before the first deploy finishes, open the service -> **Environment**
   -> **Add Environment Variable**:
   - Key: `DATABASE_URL`
   - Value: your Supabase **Session pooler** URI from step 0
     (port 5432, with `?sslmode=require` at the end).
4. **Manual Deploy** -> **Clear cache & deploy**.
5. Watch the logs. Success looks like:
   - `Installing collected packages: ... psycopg2-binary ...`
   - `Booting worker with pid ...`
   On that first boot the app creates the `users` and `locations` tables
   in Supabase and seeds all 173 districts automatically. Verify in
   Supabase -> Table Editor -> `locations` (should show 173 rows).
6. Open your live URL (https://eco-pulsy.onrender.com or similar),
   register the first account — it becomes the administrator.

## 3. 24/7 uptime ping (3 min)

1. https://uptimerobot.com -> create a free account.
2. **Add New Monitor** -> type: HTTP(s).
3. URL: your live Render URL. Friendly name: ECO PULSY.
4. Monitoring interval: **12 minutes** -> Create.

This keeps Render's free instance awake (it sleeps after 15 idle
minutes) and generates daily database traffic so Supabase's free
project never hits the 7-day inactivity pause.

## 4. Ten-second smoke test

On the live site: log in -> dashboard -> top-right picker -> choose
"Tashkent Region" -> the district box activates -> type "Bo" -> pick
"Bostanliq" -> the district page opens with live data. Done.
