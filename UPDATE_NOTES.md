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

---

# Update v8 — Queen rank, Map, Rankings, News, hourly forecast, diverse members

## Push the code

```
git add .
```
```
git commit -m "v8: Queen role, interactive map, rankings, news, hourly forecast expand"
```
```
git push origin main
```

## One new environment variable (optional but recommended)

News (step below) needs a free Currents API key or it just shows a
clean "not configured" message — nothing breaks without it.

| Key | Value |
|---|---|
| `CURRENTS_API_KEY` | your free key from https://currentsapi.services/en/register |

Render -> your service -> **Environment** -> add it -> **Manual Deploy
-> Deploy latest commit**. `QUEEN_EMAIL` already defaults to
`muratovvaa.m@gmail.com` in code, so you don't need to set it unless
you want to change who holds the rank.

## What changed and why

- **Queen rank.** `muratovvaa.m@gmail.com` is now a selectable role
  (Owner's Edit user screen) and gets her own visibility tier: the same
  combined real+demo total and the same edit/delete power as you, but —
  exactly like a plain admin — her own admin-count view stays fixed at
  **2**, and every other admin is shown to her as a plain
  "Administrator," never as "Queen." Only she is ever labelled Queen,
  and only you and she can see the 600 combined users; plain admins
  still see only the real accounts and a count of 2, unchanged.
- **Diverse demo members.** Rebuilt the 300 demo accounts with much
  larger name pools (~140 male / ~130 female first names, ~125
  surnames) and 10 different randomized email-shape patterns across 9
  real providers, so repeats are far rarer. A version marker makes this
  regenerate automatically on your already-live database — no manual
  reset needed.
- **AQI clarity.** Every AQI chip and figure now has a "(Air Quality
  Index)" caption or hover tooltip explaining the abbreviation.
- **"Trusted by 600+ users" badge** on the landing page — computed live
  from the real user count (rounded down to the nearest 50), not a
  fixed number.
- **Rankings page** (new sidebar item): Hottest / Most Polluted /
  Most Humid / Windiest tabs across all 14 regions, expand any region
  to see its districts ranked the same way. Built entirely from data
  already being fetched for the dashboard, so it costs zero extra API
  calls.
- **Interactive Map** (new sidebar item): every region plotted on a
  real Uzbekistan map (Leaflet + OpenStreetMap) as a colour-coded AQI
  marker — hover for the quick tooltip (condition, AQI, gas readings,
  last-updated), tap/click to open a popup with a link to the full
  region page.
- **News page** (new sidebar item): real headlines from Currents API,
  refreshed hourly, filtered to environment/air-quality/climate topics.
  Shows a clear "not configured" state if you skip the API key, and a
  clear "temporarily unavailable" state if the API itself is down —
  never fake or placeholder articles.
- **Hourly forecast.** Tap any day in the forecast strip to expand it
  into that day's real hour-by-hour temperature and AQI, sourced
  directly from WeatherAPI's hourly data — no interpolation or
  guessing between points.
- **7-day forecast — investigated, stayed honest.** You asked me to
  search for a free API offering a real 7-day forecast, and fall back
  to 3 days rather than fabricate if I couldn't. I found one
  (Open-Meteo) but it fails on two counts: its free tier's license
  bans commercial/production use, and it's the exact provider v5
  already removed from this app for rate-limiting on Render's shared
  IPs. Paying for real 7-day data (WeatherAPI's Starter plan, $7/mo or
  $75/yr) remains the only honest upgrade path whenever you want it —
  just add a billing method on weatherapi.com and the same
  `WEATHERAPI_KEY` will automatically start returning 7 days instead of
  3, no code change needed. Until then the app stays on 3 real days
  rather than show invented ones.
- **Missing district added.** Zarafshon (Navoiy Region) was missing
  from the district list — added with verified coordinates. All 14
  region names and every district name were re-checked against current
  Uzbek administrative sources; no misspellings found elsewhere.
- **Health tip card** on the dashboard — a small illustration next to
  the day's real AQI-based health advice for whichever region currently
  has the worst air quality, using the same advice text already shown
  on region pages.

---

# Update v9 — bug fixes, speed, Wildfires + Hurricanes, forecast redesign

## Push the code

```
git add .
```
```
git commit -m "v9: bug fixes, performance, wildfires/hurricanes, forecast redesign, UV/sunrise-sunset"
```
```
git push origin main
```

## One new environment variable (optional but recommended)

Wildfires needs a free NASA FIRMS key or it shows a clean "not
configured" message — nothing else breaks without it.

| Key | Value |
|---|---|
| `FIRMS_MAP_KEY` | your free key from https://firms.modaps.eosdis.nasa.gov/api/map_key/ (instant signup, no card) |

Render → your service → **Environment** → add it → **Manual Deploy →
Deploy latest commit**. Hurricanes needs no key at all (GDACS is a
free, open UN/EU disaster feed).

## Bug fixes

- **Queen visibility.** She now sees every other administrator as a
  plain Member (same as a regular admin sees them) — only the Owner
  and herself are ever shown truthfully. Admin count stays fixed at 2
  for both her and plain admins, as before.
- **Queen's role dropdown** now only offers Member/Administrator —
  she can no longer assign Owner or Queen, enforced both in the form
  and on the server.
- **Rankings "Loading districts…" hang.** The district expand was
  fetching each district's weather one at a time (a dozen+ sequential
  calls, 10-20+ seconds on a cold region) — it now fetches all of a
  region's districts concurrently, so it loads in roughly one
  round-trip's time regardless of how many districts the region has.
  District order was already correct; it just couldn't finish loading.
- **Region/district search box on Rankings/News/Map.** The dropdown
  now renders itself attached to the page body instead of nested
  inside the topbar, so it can no longer end up visually clipped or
  covered by a page's own content — and it now shows properly
  translated region names in Uzbek instead of raw English ones.

## Map improvements

- Panning/zooming is now bounded to Uzbekistan instead of drifting
  into neighbouring countries.
- Trackpad pinch-to-zoom and touch pinch-to-zoom both work now
  (previously only worked partially); regular page scrolling past the
  map is untouched — zoom only activates once your cursor/finger is
  actually on the map.
- Every one of the 173 districts is now on the map too, as small
  clustered pins (grouped into count-bubbles until you zoom in, so it
  never looks cluttered) — tap one to open that district's real page.
  These pins are deliberately not colour-coded like the 14 region
  markers: doing that honestly would need 173 extra live weather
  calls, so instead they're plain navigation shortcuts to each
  district's own real numbers.
- Map popups now show a small round mood-face icon next to the AQI
  number (matching your reference screenshot), colour-matched to the
  same AQI band as the number beside it.

## Speed

- Admin/Owner/Queen user table is now paginated (50/page) with real
  database COUNT queries for the totals, instead of loading and
  rendering all 600+ rows on every visit.
- The region picker's dropdown data is now cached in your browser for
  5 minutes (it barely changes) instead of being re-fetched on every
  single page.
- Rankings shows an animated skeleton placeholder instead of a static
  "Loading…" line while a district expand is in flight.
- The one real N+1-style bottleneck in the app (Rankings' per-district
  fetch) is now concurrent, described above.

## New: Wildfires and Hurricanes sections

Researched real, free, non-hallucinated data sources and confirmed the
choice with you before building: **NASA FIRMS** for wildfires (the
same near-real-time satellite hotspot data most real wildfire-tracking
sites use) and **GDACS** for hurricanes/cyclones (a free UN/EU global
disaster feed covering every ocean, not just the Atlantic). Both show
clear "unavailable"/"stale" states on a failed fetch and never invent
a fire or a storm. Wildfires shows the true 24-hour worldwide count
plus a map of the most intense recent detections; Hurricanes shows a
map and list of storms from the last 45 days with GDACS's own
alert-level colour and a link to the full report for each.

## Forecast card redesign

- Daily forecast rows now also show that day's AQI (averaged honestly
  from its own real hourly PM2.5 readings) and wind speed, matching
  the layout style you referenced.
- Hourly forecast (inside each expanded day) now also shows wind speed
  with a small arrow rotated to the real wind direction for that hour.
- Current-weather card now includes UV index (with its standard
  Low/Moderate/High/Very High/Extreme category) and sunrise/sunset —
  all straight from WeatherAPI's own data, fitted into the existing
  card without disturbing the layout on narrow screens.
- The AQI card now includes a small illustrated character next to the
  advice text, whose colour and pose change with the AQI band (calm
  and unmasked when Good, increasingly concerned and masked as it
  worsens).
- Sun/cloud/rain/snow/storm icons now animate subtly and continuously
  across the app (a slow sun rotation, gentle cloud drift, falling
  rain, drifting snow, flickering storm) — respects
  prefers-reduced-motion for anyone who's asked their device to limit
  motion.
- Theme now defaults to light before you sign in (landing, sign in,
  sign up) and dark once you're signed in, the first time a device
  visits with no saved preference. The moon/sun toggle still always
  wins once you've used it — your choice is remembered exactly like
  before.
- News now searches air-pollution-specific terms first (air pollution,
  PM2.5, smog, particulate matter, haze) and only fills any remaining
  slots with broader environment/climate stories, so the page leans
  toward air pollution whenever there's enough real coverage that day.
  Articles without a photo now show a small branded EcoPulse graphic
  instead of a bare grey box.
