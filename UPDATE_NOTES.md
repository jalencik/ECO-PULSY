# Update v3 — Caching, Background Prefetch & Security Hardening

## Files changed (sync exactly these 6 to GitHub)

| File | What changed |
|---|---|
| `requirements.txt` | added Flask-Caching, Flask-APScheduler |
| `extensions.py` | new shared `cache` and `scheduler` instances |
| `config.py` | cache/prefetch settings + secure session cookies |
| `app.py` | scheduler start-up, security headers, ProxyFix |
| `auth.py` | login brute-force lock (5 tries -> 10 min) |
| `services/openmeteo.py` | Flask-Caching backend + `warm_cache()` job |

No other files changed. No database schema changed.

## What the upgrade does

1. **Zero-lag pages.** A background job runs at boot and every 30 minutes,
   fetching the national overview and all 14 region datasets into an
   in-memory cache. Users are always served from memory — they never
   wait for an Open-Meteo round-trip.
2. **Smart error handling.** Successful data is cached for 40 minutes;
   error responses for only 60 seconds, so a temporary API hiccup heals
   fast instead of showing a stale error for half an hour.
3. **Security (from your uploaded guides).** OWASP security headers on
   every response; login locks an email for 10 minutes after 5 wrong
   passwords (brute-force protection); session cookies are HttpOnly,
   SameSite=Lax and HTTPS-only on Render; ProxyFix makes Flask
   proxy-aware behind Render's load balancer.

## How to ship it WITHOUT touching your 30 users' data

Your data lives in Supabase; Render only runs code. A deploy cannot
delete Supabase rows. Additionally: `db.create_all()` only creates
tables that don't exist (it never drops or empties existing ones), and
the district seeder checks `locations` is empty before inserting —
with 173 rows already there, it does nothing.

Exact clicks:

1. Open the ECO PULSE folder in VS Code.
2. Source Control icon (left bar) — you'll see the 6 changed files.
3. Type a message: `Feat: caching layer, background prefetch, security hardening`
4. Click **Commit**, then **Sync Changes** (or **Push**).
5. Render auto-deploys the push (or: Render dashboard -> Manual Deploy
   -> **Deploy latest commit**; "Clear cache & deploy" is also safe —
   that cache is the BUILD cache, not your database).
6. Watch the logs for `Booting worker` — then open the site. First page
   loads instantly warm.

## How to verify afterwards

- Render Logs: every 30 minutes you'll see two bursts of outbound
  fetches finish silently; every 12 minutes a `GET / ... 200` line with
  User-Agent `UptimeRobot` (proof your ping bot works).
- Supabase -> Table Editor -> `users`: still 30 rows. `locations`: still 173.
- Try 5 wrong passwords on your own account: attempt 6 says
  "Too many failed attempts" — that's the new brute-force lock
  (it clears itself after 10 minutes).
