"""Site translations (English / Uzbek).

Usage in templates (registered as Jinja globals in app.py):
    {{ t("key.name") }}
    {{ t("key.name", name=user.name) }}          # simple {placeholder} interpolation
    {{ rname(region) }}                          # Uzbek/English region display name

The active language is read from the "lang" cookie (see app.py /
views.set_language) and defaults to English. Any key missing from the
active language falls back to English, then to the raw key itself, so a
missing translation can never crash a page - it just shows in English
(or, worst case, shows the key name) until someone fills it in.
"""

DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "uz")
LANG_LABELS = {"en": "English", "uz": "O'zbekcha"}


TRANSLATIONS = {
    "en": {
        # --- <head> -----------------------------------------------------
        "meta.description": "EcoPulse - real-time air quality and weather intelligence for all 14 regions of Uzbekistan.",

        # --- Landing page nav --------------------------------------------
        "nav.features": "Features",
        "nav.how": "How it works",
        "nav.data": "Data",
        "nav.signin": "Sign in",
        "nav.signup": "Create free account",

        # --- Hero ----------------------------------------------------------
        "hero.eyebrow": "Air quality intelligence for Uzbekistan",
        "hero.title": "Know what you breathe, in every region of the country.",
        "hero.lede": "Live air quality and weather for all 14 regions of Uzbekistan - EPA health categories, six tracked pollutants and a multi-day outlook, in one clear dashboard.",
        "hero.get_started": "Get started",
        "hero.have_account": "I already have an account",
        "hero.fine_print": "Free · No credit card required",
        "hero.trust_badge": "Trusted by {count}+ users across Uzbekistan",
        "hero.preview_head": "National overview",
        "hero.preview_foot": "Sample preview",

        # --- Stats band ------------------------------------------------------
        "stats.regions": "regions covered",
        "stats.districts": "districts, coordinate-precise",
        "stats.pollutants": "pollutants tracked",
        "stats.aqi": "AQI standard",

        # --- Features section --------------------------------------------------
        "features.title": "Everything on one screen",
        "features.sub": "Built for daily decisions: should the kids play outside, is it a good day to run, do you need a mask.",
        "features.card1.title": "Full regional coverage",
        "features.card1.body": "Every viloyat plus Tashkent City and Karakalpakstan - down to all 173 districts, each fetched by its exact coordinates.",
        "features.card2.title": "Health-first air quality",
        "features.card2.body": "PM2.5, PM10, NO₂, O₃, SO₂ and CO converted into official EPA categories with plain-language advice.",
        "features.card3.title": "Weather that matters",
        "features.card3.body": "Current conditions, 48-hour trends and a 3-day forecast, because weather is what moves pollution.",

        # --- How it works ------------------------------------------------------
        "how.title": "Three steps",
        "how.step1.title": "Create your account",
        "how.step1.body": "Takes under a minute. Free forever for personal use.",
        "how.step2.title": "Pick your region",
        "how.step2.body": "All 14 regions live in the sidebar - one click away at any time.",
        "how.step3.title": "Check before you go out",
        "how.step3.body": "The AQI card tells you exactly what today's air means for your health.",

        # --- Data honesty section --------------------------------------------------
        "data.title": "Honest about the data",
        "data.p1": "Measurements and forecasts come from",
        "data.p2": ", which blends multiple national weather models and monitoring networks. No forecast on Earth is 100% accurate - so instead of pretending, we show you the official EPA uncertainty-aware categories that health agencies use.",

        # --- CTA / footer ------------------------------------------------------
        "cta.title": "Start monitoring the air you breathe",
        "cta.button": "Create free account",
        "footer.data": "Data: WeatherAPI.com · AQI: US EPA standard",
        "footer.copyright": "© {year} EcoPulse",

        # --- Auth: shared ------------------------------------------------------
        "auth.email": "Email",
        "auth.password": "Password",

        # --- Auth: login ------------------------------------------------------
        "auth.welcome_back": "Welcome back",
        "auth.signin_sub": "Sign in to your dashboard.",
        "auth.remember": "Keep me signed in",
        "auth.signin_button": "Sign in",
        "auth.new_here": "New to EcoPulse?",
        "auth.create_account_link": "Create an account",

        # --- Auth: register ------------------------------------------------------
        "auth.create_title": "Create your account",
        "auth.create_sub": "Free access to air quality across Uzbekistan.",
        "auth.full_name": "Full name",
        "auth.password_hint": "(at least 8 characters)",
        "auth.birthdate": "Date of birth",
        "auth.recommended": "(recommended)",
        "auth.photo": "Profile photo",
        "auth.optional": "(optional)",
        "auth.create_button": "Create account",
        "auth.already_registered": "Already registered?",
        "auth.signin_link": "Sign in",

        # --- App sidebar / topbar ------------------------------------------------------
        "sidebar.dashboard": "Dashboard",
        "sidebar.map": "Map",
        "sidebar.rankings": "Rankings",
        "sidebar.news": "News",
        "sidebar.regions": "Regions",
        "sidebar.administration": "Administration",
        "sidebar.admin_panel": "Admin panel",
        "sidebar.signout": "Sign out",

        # --- Dashboard ------------------------------------------------------
        "dashboard.title": "National overview",
        "dashboard.sub": "Current air quality and weather across all 14 regions of Uzbekistan",
        "dashboard.avg_pm25": "National average PM2.5",
        "dashboard.cleanest": "Cleanest air right now",
        "dashboard.worst": "Most polluted right now",
        "dashboard.health_tip_title": "Today's health tip",
        "dashboard.health_tip_context": "Based on current conditions in {region}",

        # --- Rankings ------------------------------------------------------
        "rankings.title": "Rankings",
        "rankings.sub": "All 14 regions compared live - tap a region to rank its districts too",
        "rankings.tab_hottest": "Hottest",
        "rankings.tab_polluted": "Most polluted",
        "rankings.tab_humid": "Most humid",
        "rankings.tab_windy": "Windiest",
        "rankings.expand_hint": "Tap a region to rank its districts",
        "rankings.loading": "Loading districts...",
        "rankings.load_error": "Couldn't load districts right now. Try again shortly.",
        "rankings.no_data": "No data available yet.",
        "rankings.stale_district": "Preview - live data temporarily unavailable for this district",

        # --- News ------------------------------------------------------
        "news.title": "News",
        "news.sub": "Air quality and environment headlines, refreshed hourly",
        "news.unavailable": "News is temporarily unavailable. Please check back shortly.",
        "news.stale": "Showing the last successfully loaded headlines while live news refreshes.",
        "news.no_articles": "No matching articles right now. Check back soon.",
        "news.not_configured": "The news feed isn't connected yet.",
        "news.attribution": "News via Currents API - each headline links to its original source.",

        # --- Map ------------------------------------------------------
        "map.title": "Map",
        "map.sub": "Live air quality across Uzbekistan - hover or tap a marker for details",
        "map.view_details": "View full details",
        "map.legend_title": "AQI legend",
        "map.attribution_note": "Markers mark each region's administrative centre, not a boundary estimate.",

        # --- Banners ------------------------------------------------------
        "banner.demo": "Demo data mode is on (DEMO_DATA=1). Values shown are synthetic samples, not live measurements.",
        "banner.stale_dashboard": "Live refresh is temporarily delayed - showing the most recent readings.",
        "banner.error_dashboard": "Live data is temporarily unavailable. Please refresh in a moment.",
        "banner.stale_region": "Live refresh is temporarily delayed by the data provider - showing the most recent successful measurements. Updates resume automatically.",
        "banner.error_region": "Live data is temporarily unavailable for this region. Please refresh in a moment.",
        "banner.error_location": "Live data is temporarily unavailable for this district. Please refresh in a moment.",
        "banner.fallback": "Point data for this district is temporarily unavailable - showing the regional centre ({capital}) instead.",
        "banner.last_updated": "(last good reading: {mins} min ago)",

        # --- Region / location detail ------------------------------------------------------
        "region.measured_at": "Measured at",
        "detail.current_weather": "Current weather",
        "detail.feels_like": "Feels like",
        "detail.wind": "Wind",
        "detail.humidity": "Humidity",
        "detail.pressure": "Pressure",
        "detail.aqi_title": "Air quality index",
        "detail.aqi_unavailable": "AQI unavailable.",
        "detail.aqi_note": "US EPA index, computed from PM2.5",
        "aqi.hint": "AQI (Air Quality Index)",
        "detail.chart_title": "Next 48 hours - temperature and PM2.5",
        "detail.forecast_title": "{days}-day forecast",
        "detail.forecast_hint": "Tap a day for its hour-by-hour temperature and AQI",
        "detail.pollutant_title": "Pollutant breakdown",
        "detail.pollutant_col": "Pollutant",
        "detail.concentration_col": "Concentration",
        "detail.unit_col": "Unit",

        # --- Weather condition labels (keyed by the exact English label the
        # backend produces, so no new backend code is needed) ---------------
        "weather.Clear": "Clear",
        "weather.Partly cloudy": "Partly cloudy",
        "weather.Cloudy": "Cloudy",
        "weather.Fog": "Fog",
        "weather.Thunderstorm": "Thunderstorm",
        "weather.Snow": "Snow",
        "weather.Rain": "Rain",
        "weather.Unknown": "Unknown",

        # --- Weekday abbreviations (Python strftime %a output) ---------------
        "weekday.Mon": "Mon", "weekday.Tue": "Tue", "weekday.Wed": "Wed",
        "weekday.Thu": "Thu", "weekday.Fri": "Fri", "weekday.Sat": "Sat", "weekday.Sun": "Sun",

        # --- AQI categories + advice (keyed by the exact English label) ---------------
        "aqi.label.Good": "Good",
        "aqi.label.Moderate": "Moderate",
        "aqi.label.Unhealthy for Sensitive Groups": "Unhealthy for Sensitive Groups",
        "aqi.label.Unhealthy": "Unhealthy",
        "aqi.label.Very Unhealthy": "Very Unhealthy",
        "aqi.label.Hazardous": "Hazardous",
        "aqi.advice.Good": "Air quality is satisfactory. Enjoy outdoor activities.",
        "aqi.advice.Moderate": "Acceptable air quality. Unusually sensitive people should consider limiting prolonged outdoor exertion.",
        "aqi.advice.Unhealthy for Sensitive Groups": "Children, older adults and people with heart or lung disease should reduce prolonged outdoor exertion.",
        "aqi.advice.Unhealthy": "Everyone may begin to experience health effects. Sensitive groups should avoid outdoor exertion.",
        "aqi.advice.Very Unhealthy": "Health alert: everyone should avoid prolonged outdoor exertion.",
        "aqi.advice.Hazardous": "Emergency conditions: everyone should stay indoors and keep activity levels low.",

        # --- Admin / Owner / Queen panel ------------------------------------------------------
        "admin.owner_panel": "Owner panel",
        "admin.queen_panel": "Queen panel",
        "admin.admin_panel": "Admin panel",
        "admin.platform_accounts": "Platform accounts",
        "admin.and_roles": "and roles",
        "admin.run_diagnostics": "Run live diagnostics",
        "admin.total_users": "Total users",
        "admin.administrators": "Administrators",
        "admin.all_users_owner": "All users - owner controls",
        "admin.all_users_queen": "All users - queen controls",
        "admin.all_users": "All users",
        "admin.col_num": "#",
        "admin.col_name": "Name",
        "admin.col_email": "Email",
        "admin.col_role": "Role",
        "admin.col_joined": "Joined",
        "admin.col_manage": "Manage",
        "admin.edit_tooltip": "Edit user",
        "admin.delete_tooltip": "Delete user",
        "admin.confirm_delete": "Delete {name} permanently?",
        "admin.edit_user_title": "Edit user",
        "admin.owner_controls": "Owner controls",
        "edit.name_label": "Name",
        "edit.email_label": "Email",
        "edit.role_label": "Role",
        "edit.save": "Save changes",
        "edit.cancel": "Cancel",

        # --- Roles (keyed by the exact string User.role_label / admin.py produce) -----
        "role.Owner": "Owner",
        "role.Queen": "Queen",
        "role.Administrator": "Administrator",
        "role.Member": "Member",

        # --- Location picker ------------------------------------------------------
        "picker.region": "Region…",
        "picker.district": "District…",
        "picker.search_region": "Search region",
        "picker.search_district": "Search district",
        "picker.use_location": "Use my current location",
        "picker.location_error": "Could not get your location. Please allow location access.",

        # --- Error pages ------------------------------------------------------
        "error.back_home": "Back to home",
        "error.403": "You do not have permission to view this page.",
        "error.404": "The page you are looking for does not exist.",

        # --- Flash messages ------------------------------------------------------
        "flash.signup_paused": "Sign-ups from this network are temporarily paused for security. Please try again a little later.",
        "flash.name_required": "Please enter your full name.",
        "flash.email_invalid": "Please enter a valid email address.",
        "flash.password_length": "Password must be at least 8 characters.",
        "flash.email_taken": "An account with this email already exists.",
        "flash.photo_too_large": "Profile photo must be under 800 KB.",
        "flash.photo_bad_type": "Photo must be a PNG, JPG, WEBP or GIF image.",
        "flash.login_locked": "Too many failed attempts. Please try again in 10 minutes.",
        "flash.bad_credentials": "Incorrect email or password.",
        "flash.email_in_use": "That email is already used by another account.",
        "flash.user_updated": "User updated.",
        "flash.cannot_delete_self": "You cannot delete your own account.",
        "flash.cannot_delete_owner": "The owner account can't be deleted.",
        "flash.user_deleted": "User deleted.",
    },

    "uz": {
        # --- <head> -----------------------------------------------------
        "meta.description": "EcoPulse - O'zbekistonning barcha 14 viloyati uchun real vaqtda havo sifati va ob-havo ma'lumotlari.",

        # --- Landing page nav --------------------------------------------
        "nav.features": "Imkoniyatlar",
        "nav.how": "Qanday ishlaydi",
        "nav.data": "Ma'lumotlar",
        "nav.signin": "Kirish",
        "nav.signup": "Bepul ro'yxatdan o'tish",

        # --- Hero ----------------------------------------------------------
        "hero.eyebrow": "O'zbekiston uchun havo sifati tizimi",
        "hero.title": "Mamlakatning har bir mintaqasida nima bilan nafas olayotganingizni bilib oling.",
        "hero.lede": "O'zbekistonning barcha 14 viloyati uchun jonli havo sifati va ob-havo - EPA sog'liq toifalari, kuzatiluvchi oltita ifloslantiruvchi modda va bir necha kunlik prognoz, bitta aniq boshqaruv panelida.",
        "hero.get_started": "Boshlash",
        "hero.have_account": "Mening hisobim bor",
        "hero.fine_print": "Bepul · Bank kartasi talab qilinmaydi",
        "hero.trust_badge": "O'zbekiston bo'ylab {count}+ foydalanuvchi bizga ishonadi",
        "hero.preview_head": "Umumiy ko'rinish",
        "hero.preview_foot": "Namunaviy ko'rinish",

        # --- Stats band ------------------------------------------------------
        "stats.regions": "viloyat qamrovda",
        "stats.districts": "tuman, aniq koordinatali",
        "stats.pollutants": "ifloslantiruvchi modda kuzatiladi",
        "stats.aqi": "AQI standarti",

        # --- Features section --------------------------------------------------
        "features.title": "Barchasi bitta ekranda",
        "features.sub": "Kundalik qarorlar uchun: bolalar tashqarida o'ynasa bo'ladimi, yugurish uchun yaxshi kunmi, niqob kerakmi.",
        "features.card1.title": "To'liq mintaqaviy qamrov",
        "features.card1.body": "Har bir viloyat, shuningdek Toshkent shahri va Qoraqalpog'iston - barcha 173 tumangacha, har biri aniq koordinatalari bo'yicha olinadi.",
        "features.card2.title": "Sog'liqni birinchi o'ringa qo'yuvchi havo sifati",
        "features.card2.body": "PM2.5, PM10, NO₂, O₃, SO₂ va CO rasmiy EPA toifalariga va tushunarli tavsiyalarga aylantiriladi.",
        "features.card3.title": "Muhim ob-havo ma'lumotlari",
        "features.card3.body": "Joriy holat, 48 soatlik tendensiyalar va 3 kunlik prognoz - chunki ob-havo ifloslanishni harakatga keltiradi.",

        # --- How it works ------------------------------------------------------
        "how.title": "Uch qadam",
        "how.step1.title": "Hisobingizni yarating",
        "how.step1.body": "Bir daqiqadan kam vaqt oladi. Shaxsiy foydalanish uchun har doim bepul.",
        "how.step2.title": "Mintaqangizni tanlang",
        "how.step2.body": "Barcha 14 viloyat yon panelda joylashgan - istalgan vaqtda bir bosishda.",
        "how.step3.title": "Tashqariga chiqishdan oldin tekshiring",
        "how.step3.body": "AQI kartasi bugungi havo salomatligingiz uchun nimani anglatishini aniq ko'rsatadi.",

        # --- Data honesty section --------------------------------------------------
        "data.title": "Ma'lumotlar haqida ochiq va halol",
        "data.p1": "O'lchovlar va prognozlar",
        "data.p2": " manbasidan olinadi, u bir nechta milliy ob-havo modellari va kuzatuv tarmoqlarini birlashtiradi. Yer yuzida 100% aniq prognoz yo'q - shuning uchun soxta aniqlik ko'rsatish o'rniga sog'liqni saqlash idoralari foydalanadigan rasmiy EPA noaniqlikni hisobga oluvchi toifalarni ko'rsatamiz.",

        # --- CTA / footer ------------------------------------------------------
        "cta.title": "Nafas olayotgan havoingizni kuzatishni boshlang",
        "cta.button": "Bepul ro'yxatdan o'tish",
        "footer.data": "Ma'lumot: WeatherAPI.com · AQI: AQSh EPA standarti",
        "footer.copyright": "© {year} EcoPulse",

        # --- Auth: shared ------------------------------------------------------
        "auth.email": "Elektron pochta",
        "auth.password": "Parol",

        # --- Auth: login ------------------------------------------------------
        "auth.welcome_back": "Xush kelibsiz",
        "auth.signin_sub": "Boshqaruv panelingizga kirish uchun tizimga kiring.",
        "auth.remember": "Meni tizimda saqlash",
        "auth.signin_button": "Kirish",
        "auth.new_here": "EcoPulse'da yangimisiz?",
        "auth.create_account_link": "Hisob yaratish",

        # --- Auth: register ------------------------------------------------------
        "auth.create_title": "Hisobingizni yarating",
        "auth.create_sub": "O'zbekiston bo'ylab havo sifatiga bepul kirish.",
        "auth.full_name": "To'liq ism",
        "auth.password_hint": "(kamida 8 ta belgi)",
        "auth.birthdate": "Tug'ilgan sana",
        "auth.recommended": "(tavsiya etiladi)",
        "auth.photo": "Profil rasmi",
        "auth.optional": "(ixtiyoriy)",
        "auth.create_button": "Hisob yaratish",
        "auth.already_registered": "Ro'yxatdan o'tganmisiz?",
        "auth.signin_link": "Kirish",

        # --- App sidebar / topbar ------------------------------------------------------
        "sidebar.dashboard": "Boshqaruv paneli",
        "sidebar.map": "Xarita",
        "sidebar.rankings": "Reyting",
        "sidebar.news": "Yangiliklar",
        "sidebar.regions": "Viloyatlar",
        "sidebar.administration": "Boshqaruv",
        "sidebar.admin_panel": "Admin panel",
        "sidebar.signout": "Chiqish",

        # --- Dashboard ------------------------------------------------------
        "dashboard.title": "Umumiy milliy ko'rinish",
        "dashboard.sub": "O'zbekistonning barcha 14 viloyati bo'yicha joriy havo sifati va ob-havo",
        "dashboard.avg_pm25": "O'rtacha milliy PM2.5",
        "dashboard.cleanest": "Hozirda eng toza havo",
        "dashboard.worst": "Hozirda eng ifloslangan havo",
        "dashboard.health_tip_title": "Bugungi salomatlik maslahati",
        "dashboard.health_tip_context": "{region} dagi joriy sharoitlarga asoslanib",

        # --- Rankings ------------------------------------------------------
        "rankings.title": "Reyting",
        "rankings.sub": "Barcha 14 viloyat jonli taqqoslanadi - tumanlar reytingini ko'rish uchun viloyatni bosing",
        "rankings.tab_hottest": "Eng issiq",
        "rankings.tab_polluted": "Eng ifloslangan",
        "rankings.tab_humid": "Eng nam",
        "rankings.tab_windy": "Eng shamolli",
        "rankings.expand_hint": "Tumanlar reytingini ko'rish uchun viloyatni bosing",
        "rankings.loading": "Tumanlar yuklanmoqda...",
        "rankings.load_error": "Tumanlarni hozircha yuklab bo'lmadi. Birozdan so'ng qayta urinib ko'ring.",
        "rankings.no_data": "Hozircha ma'lumot mavjud emas.",
        "rankings.stale_district": "Ko'rib chiqish - bu tuman uchun jonli ma'lumot vaqtincha mavjud emas",

        # --- News ------------------------------------------------------
        "news.title": "Yangiliklar",
        "news.sub": "Havo sifati va atrof-muhitga oid yangiliklar, har soatda yangilanadi",
        "news.unavailable": "Yangiliklar vaqtincha mavjud emas. Birozdan so'ng qayta tekshiring.",
        "news.stale": "Jonli yangiliklar yangilanayotgan vaqtda so'nggi muvaffaqiyatli yuklangan sarlavhalar ko'rsatilmoqda.",
        "news.no_articles": "Hozircha mos maqolalar yo'q. Tez orada qayta tekshiring.",
        "news.not_configured": "Yangiliklar manbai hali ulanmagan.",
        "news.attribution": "Yangiliklar Currents API orqali - har bir sarlavha asl manbaga havola qiladi.",

        # --- Map ------------------------------------------------------
        "map.title": "Xarita",
        "map.sub": "O'zbekiston bo'ylab jonli havo sifati - tafsilotlar uchun belgini bosing yoki uning ustiga kursorni olib boring",
        "map.view_details": "To'liq ma'lumotlarni ko'rish",
        "map.legend_title": "AQI belgilari",
        "map.attribution_note": "Belgilar har bir viloyatning ma'muriy markazini bildiradi, chegara taxminini emas.",

        # --- Banners ------------------------------------------------------
        "banner.demo": "Demo ma'lumot rejimi yoqilgan (DEMO_DATA=1). Ko'rsatilgan qiymatlar sun'iy namunalar, jonli o'lchovlar emas.",
        "banner.stale_dashboard": "Jonli yangilanish vaqtincha kechikmoqda - so'nggi mavjud ma'lumotlar ko'rsatilmoqda.",
        "banner.error_dashboard": "Jonli ma'lumot vaqtincha mavjud emas. Iltimos, birozdan so'ng qayta yuklang.",
        "banner.stale_region": "Ma'lumot provayderi tomonidan jonli yangilanish vaqtincha kechikmoqda - so'nggi muvaffaqiyatli o'lchovlar ko'rsatilmoqda. Yangilanish avtomatik davom etadi.",
        "banner.error_region": "Ushbu mintaqa uchun jonli ma'lumot vaqtincha mavjud emas. Iltimos, birozdan so'ng qayta yuklang.",
        "banner.error_location": "Ushbu tuman uchun jonli ma'lumot vaqtincha mavjud emas. Iltimos, birozdan so'ng qayta yuklang.",
        "banner.fallback": "Ushbu tuman uchun aniq nuqta ma'lumoti vaqtincha mavjud emas - uning o'rniga mintaqa markazi ({capital}) ko'rsatilmoqda.",
        "banner.last_updated": "(so'nggi yaxshi o'lchov: {mins} daqiqa oldin)",

        # --- Region / location detail ------------------------------------------------------
        "region.measured_at": "O'lchov nuqtasi",
        "detail.current_weather": "Joriy ob-havo",
        "detail.feels_like": "His qilinadigan harorat",
        "detail.wind": "Shamol",
        "detail.humidity": "Namlik",
        "detail.pressure": "Bosim",
        "detail.aqi_title": "Havo sifati indeksi",
        "detail.aqi_unavailable": "AQI mavjud emas.",
        "detail.aqi_note": "AQSh EPA indeksi, PM2.5 asosida hisoblangan",
        "aqi.hint": "AQI (Havo sifati indeksi)",
        "detail.chart_title": "Keyingi 48 soat - harorat va PM2.5",
        "detail.forecast_title": "{days} kunlik prognoz",
        "detail.forecast_hint": "Soatlik harorat va AQI uchun kunni bosing",
        "detail.pollutant_title": "Ifloslantiruvchi moddalar taqsimoti",
        "detail.pollutant_col": "Ifloslantiruvchi modda",
        "detail.concentration_col": "Konsentratsiya",
        "detail.unit_col": "O'lchov birligi",

        # --- Weather condition labels ---------------------------------------------
        "weather.Clear": "Ochiq",
        "weather.Partly cloudy": "Ozgina bulutli",
        "weather.Cloudy": "Bulutli",
        "weather.Fog": "Tumanli",
        "weather.Thunderstorm": "Momaqaldiroq",
        "weather.Snow": "Qor",
        "weather.Rain": "Yomg'ir",
        "weather.Unknown": "Noma'lum",

        # --- Weekday abbreviations ---------------------------------------------
        "weekday.Mon": "Dush", "weekday.Tue": "Sesh", "weekday.Wed": "Chor",
        "weekday.Thu": "Pay", "weekday.Fri": "Jum", "weekday.Sat": "Shan", "weekday.Sun": "Yak",

        # --- AQI categories + advice ---------------------------------------------
        "aqi.label.Good": "Yaxshi",
        "aqi.label.Moderate": "O'rtacha",
        "aqi.label.Unhealthy for Sensitive Groups": "Sezgir guruhlar uchun zararli",
        "aqi.label.Unhealthy": "Zararli",
        "aqi.label.Very Unhealthy": "Juda zararli",
        "aqi.label.Hazardous": "Xavfli",
        "aqi.advice.Good": "Havo sifati qoniqarli. Tashqi faoliyatdan bahramand bo'ling.",
        "aqi.advice.Moderate": "Havo sifati qabul qilinishi mumkin. Alohida sezgir odamlar uzoq muddatli tashqi jismoniy faoliyatni cheklashni o'ylab ko'rishlari kerak.",
        "aqi.advice.Unhealthy for Sensitive Groups": "Bolalar, keksalar hamda yurak yoki o'pka kasalligi bo'lgan odamlar uzoq muddatli tashqi jismoniy faoliyatni kamaytirishi kerak.",
        "aqi.advice.Unhealthy": "Barcha odamlarda sog'liq bilan bog'liq ta'sirlar boshlanishi mumkin. Sezgir guruhlar tashqi jismoniy faoliyatdan saqlanishi kerak.",
        "aqi.advice.Very Unhealthy": "Sog'liq bo'yicha ogohlantirish: barcha odamlar uzoq muddatli tashqi jismoniy faoliyatdan saqlanishi kerak.",
        "aqi.advice.Hazardous": "Favqulodda holat: barcha odamlar uy ichida qolishi va faollikni pasaytirishi kerak.",

        # --- Admin / Owner / Queen panel ------------------------------------------------------
        "admin.owner_panel": "Egasi paneli",
        "admin.queen_panel": "Qirolicha paneli",
        "admin.admin_panel": "Admin panel",
        "admin.platform_accounts": "Platforma hisoblari",
        "admin.and_roles": "va rollari",
        "admin.run_diagnostics": "Jonli diagnostikani ishga tushirish",
        "admin.total_users": "Jami foydalanuvchilar",
        "admin.administrators": "Administratorlar",
        "admin.all_users_owner": "Barcha foydalanuvchilar - egasi nazorati",
        "admin.all_users_queen": "Barcha foydalanuvchilar - qirolicha nazorati",
        "admin.all_users": "Barcha foydalanuvchilar",
        "admin.col_num": "#",
        "admin.col_name": "Ism",
        "admin.col_email": "Elektron pochta",
        "admin.col_role": "Rol",
        "admin.col_joined": "Qo'shilgan sana",
        "admin.col_manage": "Boshqarish",
        "admin.edit_tooltip": "Foydalanuvchini tahrirlash",
        "admin.delete_tooltip": "Foydalanuvchini o'chirish",
        "admin.confirm_delete": "{name} butunlay o'chirib tashlansinmi?",
        "admin.edit_user_title": "Foydalanuvchini tahrirlash",
        "admin.owner_controls": "Egasi nazorati",
        "edit.name_label": "Ism",
        "edit.email_label": "Elektron pochta",
        "edit.role_label": "Rol",
        "edit.save": "O'zgarishlarni saqlash",
        "edit.cancel": "Bekor qilish",

        # --- Roles ------------------------------------------------------
        "role.Owner": "Egasi",
        "role.Queen": "Qirolicha",
        "role.Administrator": "Administrator",
        "role.Member": "A'zo",

        # --- Location picker ------------------------------------------------------
        "picker.region": "Viloyat…",
        "picker.district": "Tuman…",
        "picker.search_region": "Viloyatni qidirish",
        "picker.search_district": "Tumanni qidirish",
        "picker.use_location": "Joriy joylashuvimdan foydalanish",
        "picker.location_error": "Joylashuvingizni aniqlab bo'lmadi. Iltimos, joylashuvga ruxsat bering.",

        # --- Error pages ------------------------------------------------------
        "error.back_home": "Bosh sahifaga qaytish",
        "error.403": "Ushbu sahifani ko'rishga ruxsatingiz yo'q.",
        "error.404": "Siz izlayotgan sahifa mavjud emas.",

        # --- Flash messages ------------------------------------------------------
        "flash.signup_paused": "Xavfsizlik uchun ushbu tarmoqdan ro'yxatdan o'tish vaqtincha to'xtatilgan. Birozdan so'ng qayta urinib ko'ring.",
        "flash.name_required": "Iltimos, to'liq ismingizni kiriting.",
        "flash.email_invalid": "Iltimos, haqiqiy elektron pochta manzilini kiriting.",
        "flash.password_length": "Parol kamida 8 ta belgidan iborat bo'lishi kerak.",
        "flash.email_taken": "Ushbu elektron pochta bilan hisob allaqachon mavjud.",
        "flash.photo_too_large": "Profil rasmi 800 KB dan kichik bo'lishi kerak.",
        "flash.photo_bad_type": "Rasm PNG, JPG, WEBP yoki GIF formatida bo'lishi kerak.",
        "flash.login_locked": "Juda ko'p noto'g'ri urinish. Iltimos, 10 daqiqadan so'ng qayta urinib ko'ring.",
        "flash.bad_credentials": "Elektron pochta yoki parol noto'g'ri.",
        "flash.email_in_use": "Ushbu elektron pochtadan boshqa hisobda foydalanilmoqda.",
        "flash.user_updated": "Foydalanuvchi yangilandi.",
        "flash.cannot_delete_self": "O'zingizning hisobingizni o'chira olmaysiz.",
        "flash.cannot_delete_owner": "Egasi hisobini o'chirib bo'lmaydi.",
        "flash.user_deleted": "Foydalanuvchi o'chirildi.",
    },
}


def t(lang, key, **kwargs):
    """Translate *key* into *lang*, falling back to English then the key."""
    text = TRANSLATIONS.get(lang, {}).get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
