# Update v5 — WeatherAPI fix + Owner rank + profiles

## Step 1 — get your free WeatherAPI key (2 min, no card)

1. Go to https://www.weatherapi.com/signup.aspx and sign up (free).
2. On your dashboard, copy the **API Key**.
3. You'll paste it into Render in step 3. That's the only manual value.

## Step 2 — push the code (VS Code -> Terminal -> New Terminal)

```
git add .
```
```
git commit -m "v5: WeatherAPI provider, owner rank, profile fields, geolocation"
```
```
git push origin main
```
(If push is rejected: `git pull --no-edit -X ours` then `git push origin main`.)

## Step 3 — set two environment variables on Render

Render -> your service -> **Environment** -> add:

| Key | Value |
|---|---|
| `WEATHERAPI_KEY` | the key from step 1 |
| `OWNER_EMAIL` | jaloliddin2009applicant@gmail.com |

Then **Manual Deploy -> Deploy latest commit**. After it boots, open
`/admin/diagnostics` — the WeatherAPI row should read **OK 200**, and the
dashboard fills with live data within a minute.

## What changed and why

**The actual bug (proven by your diagnostics page):** only Open-Meteo's
*weather* endpoint was returning 429 "Daily API request limit exceeded"
— its air-quality endpoint was fine. The cause is Render's free tier
sharing outbound IPs with thousands of apps that collectively exhaust
Open-Meteo's per-IP free quota.

**The fix:** weather now comes from **WeatherAPI.com** using YOUR personal
key (1,000,000 calls/month free). A personal key is tied to your account,
not the shared IP, so this rate-limit can't happen again. One WeatherAPI
call returns weather + air quality + forecast together, so the app is
simpler and no longer depends on Open-Meteo at all. Forecast shows 3 days
(WeatherAPI free tier); the heading adjusts automatically.

**New: Owner vs Admin ranks.**
- The `OWNER_EMAIL` account is automatically promoted to **Owner**.
- The Owner sees the *real* number of admins and the full user table,
  and can **edit** any user's name/email/role or **delete** a user (pencil
  and trash icons in the table).
- Plain Admins see the admin count as **2** and no management table, exactly
  as you asked.

**New: richer sign-up.**
- Optional **Date of birth** field, labelled "(recommended)".
- Optional **profile photo** upload — stored in the database and shown as
  the sidebar avatar.
- **"Use my current location"** button (pin icon by the search boxes): asks
  the browser for GPS, saves the coordinates to the user's record, and jumps
  to their nearest region.

**Passwords:** stored ONLY as irreversible salted hashes, as before. This
is deliberate and protects your users — see the chat for the full reason.

---

# Update v6 — Mobile menu, dark mode, Book-security hardening

Push: `git add .` -> `git commit -m "v6: mobile burger menu, dark mode, CSP/HSTS, signup rate limit"` -> `git push origin main`

- **Phones:** burger icon opens the sidebar as a slide-in panel (regions,
  admin link, your profile chip and Sign out all reachable). Tapping the
  dark overlay or any link closes it. The district picker moves to its
  own full-width row on small screens.
- **Dark mode:** moon/sun button in the top-right (also on the landing
  page). Choice is remembered on the device; first visit follows the
  phone's system theme. Full dark palette across dashboard, region pages,
  admin, auth screens, dropdowns and banners.
- **Security (from your Book, chapter 12 + appendix checklist):**
  Content-Security-Policy header (only our own code + our two CDNs can
  run), HSTS on Render, all inline JS removed (CSP-safe confirms),
  signup rate limit (5 accounts/hour per IP), real client IPs behind
  Render's proxy, dependency versions capped. Passwords were already
  stored as salted hashes — that IS the "password turned into code
  hackers can't reach" from the book.

---

# Update v7 — Uzbek/English, demo members, phone polish, speed + hardening

Push: `git add .` -> `git commit -m "v7: EN/UZ language, 300 demo members, mobile polish, gzip + gunicorn threads, retry tuning"` -> `git push origin main`

- **English / Uzbek language switcher** — "EN / UZ" pill in the top-right
  of every page (landing included). Choice is remembered in a cookie, no
  account change needed. Translations live in one place: `translations.py`.
  The admin diagnostics page stays English-only (it's an internal ops
  tool); everything a regular visitor sees is bilingual.
- **300 demo member accounts** (`services/fake_members.py`) — clearly
  fake Uzbek names/emails, seeded once automatically on the next deploy.
  Role is always "Member," and they can never log in (random, discarded
  password). Only **your** owner panel folds them into the combined
  "Total users" count, each tagged with a small "Demo" pill only you can
  see. Plain admins query real accounts only — same count and table as
  before, demo rows never appear to them at all.
- **Phone layout fixes** (no design/colour/content changes, layout only):
  fixed a real bug where the topbar's language/theme controls and the
  region search box could squeeze together instead of stacking on narrow
  screens; landing page nav wraps to its own row instead of overflowing;
  hero buttons stack full-width on small phones; the admin/diagnostics
  tables scroll horizontally inside their card instead of breaking the
  page; the day-forecast strip now sizes itself to however many days
  WeatherAPI actually returns (was hardcoded for 7, you get 3).
  Additional fix: rebuilt the "Honest about the data" and footer credit
  on the landing page, which still said "Open-Meteo" from before the v5
  provider switch — they now correctly say WeatherAPI.com.
- **Speed:** gzip compression on every HTML/CSS/JS/JSON response
  (stdlib only, no new dependency), a week of browser caching for
  `/static/*`, and gunicorn now runs with 4 threads (`--worker-class
  gthread --threads 4`, still **one process** so the background
  prefetch scheduler can't accidentally double up) plus a 90s timeout
  so a slow upstream retry gets a real answer instead of a killed
  worker. WeatherAPI calls now time out and fall back to the last-good
  preview faster (10s/2 tries instead of 15s/3) — real-time data is
  still always tried first, you just don't wait as long for the
  preview when it's struggling. The stale/preview banners now say how
  many minutes old that last good reading is.
- **View-source, honestly:** no website — this one included — can stop
  a visitor's browser from showing them the HTML/CSS/JS it already sent,
  that's how the web works for every site, not an EcoPulse gap. What
  actually matters is already true here: your WeatherAPI key, database
  URL and secret key only ever live in Render's environment variables
  and are never sent to the browser. Added a right-click/devtools-shortcut
  block as light friction (labelled clearly in `static/js/ui.js` as
  friction, not protection — delete it anytime it's annoying).
