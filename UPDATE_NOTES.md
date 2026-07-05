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
