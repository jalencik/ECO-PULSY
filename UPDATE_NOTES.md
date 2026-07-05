# Update v4 — Rate-limit resilience, stale-serving & snapshot persistence

This update eliminates the **"Live data is temporarily unavailable"** banner
as a normal occurrence. It attacks the real root causes of that message on
Render's free tier, not just the symptom.

## Why the banner appeared

1. **No retry.** A single Open-Meteo `429` (rate limit) became an error
   instantly. Render's free tier shares outbound IPs across many apps, and
   Open-Meteo throttles per IP, so 429s happen even when your app is polite.
2. **Last good data was thrown away.** Any failed refresh returned an error
   payload — even though perfectly good data had loaded minutes earlier.
3. **The cache is wiped on every restart.** `SimpleCache` lives only in one
   worker's memory. Render cold-starts constantly, so after each restart the
   app had nothing to show until the next successful refresh.
4. **The warm-up burst was ~16 rapid calls** (14 regions fetched one by one),
   the exact pattern that trips a shared-IP rate limit.

## What changed

| File | Change |
|---|---|
| `services/openmeteo.py` | Retry with backoff honoring `Retry-After`; serve last-good (`stale`) data on failure; batched 14-region warm-up (2 calls, not 28) |
| `services/snapshots.py` | **New.** Saves/loads the last good payload to the database |
| `models.py` | **New** `Snapshot` table (auto-created on boot; no manual migration) |
| `templates/dashboard.html`, `region.html`, `location.html` | Gentle "refresh delayed" notice when showing cached data |
| `test_resilience.py` | **New.** 14 simulated-failure tests, all passing |

No existing table changed. No data is touched.

## The four defensive layers

1. **Retry on 429/5xx/timeout** — up to 3 attempts, honoring the API's
   `Retry-After` header (capped so a user never waits long).
2. **Serve last-known-good data** — if a refresh still fails, the previous
   good payload is shown with a small "refresh delayed" note instead of the
   red error. The red banner can now appear **only** on a page that has
   *never once* loaded successfully.
3. **Snapshot persistence to Postgres/Supabase** — every good payload is
   saved to a `snapshots` table, so a cold start or restart restores real
   data instantly, and all workers share it.
4. **Batched warm-up** — all 14 regions are refreshed in 2 requests, keeping
   you far under the rate limit.

## Honest limitation

No free-tier stack can promise literally zero errors. What this guarantees is
that users never see a **blank or broken** page: worst case they see slightly
older readings with a polite notice, and the app self-heals on the next
successful refresh.

## Deploy

Your data lives in Supabase; Render only runs code. `db.create_all()` only
*adds* the new `snapshots` table — it never drops or empties anything.

1. Merge/push this branch to `main` on GitHub.
2. Render auto-deploys (or Manual Deploy → Deploy latest commit).
3. Watch the logs for `Booting worker`, then open the site.

## Verify

- `venv/Scripts/python.exe test_resilience.py` → `14 passed, 0 failed`.
- In Supabase → Table Editor you'll see a new `snapshots` table filling with
  one row per region shortly after boot.
- `users` (30) and `locations` (173) are untouched.
