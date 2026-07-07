"""The 14 administrative regions of Uzbekistan.

Coordinates point at each region's administrative capital, which is
where air-quality monitoring is most relevant for population exposure.
"""

REGIONS = [
    {"slug": "tashkent-city",  "name": "Tashkent City",   "capital": "Tashkent",  "lat": 41.3111, "lon": 69.2797},
    {"slug": "tashkent",       "name": "Tashkent Region", "capital": "Nurafshon", "lat": 41.0167, "lon": 69.3667},
    {"slug": "andijan",        "name": "Andijan",         "capital": "Andijan",   "lat": 40.7821, "lon": 72.3442},
    {"slug": "bukhara",        "name": "Bukhara",         "capital": "Bukhara",   "lat": 39.7747, "lon": 64.4286},
    {"slug": "fergana",        "name": "Fergana",         "capital": "Fergana",   "lat": 40.3864, "lon": 71.7864},
    {"slug": "jizzakh",        "name": "Jizzakh",         "capital": "Jizzakh",   "lat": 40.1158, "lon": 67.8422},
    {"slug": "kashkadarya",    "name": "Kashkadarya",     "capital": "Qarshi",    "lat": 38.8606, "lon": 65.7891},
    {"slug": "khorezm",        "name": "Khorezm",         "capital": "Urgench",   "lat": 41.5500, "lon": 60.6333},
    {"slug": "namangan",       "name": "Namangan",        "capital": "Namangan",  "lat": 41.0011, "lon": 71.6725},
    {"slug": "navoiy",         "name": "Navoiy",          "capital": "Navoiy",    "lat": 40.0844, "lon": 65.3792},
    {"slug": "samarkand",      "name": "Samarkand",       "capital": "Samarkand", "lat": 39.6542, "lon": 66.9597},
    {"slug": "sirdaryo",       "name": "Sirdaryo",        "capital": "Guliston",  "lat": 40.4897, "lon": 68.7842},
    {"slug": "surkhandarya",   "name": "Surkhandarya",    "capital": "Termez",    "lat": 37.2242, "lon": 67.2783},
    {"slug": "karakalpakstan", "name": "Karakalpakstan",  "capital": "Nukus",     "lat": 42.4531, "lon": 59.6103},
]

_BY_SLUG = {r["slug"]: r for r in REGIONS}


def get_region(slug: str):
    """Return the region dict for a slug, or None if it does not exist."""
    return _BY_SLUG.get(slug)


# Uzbek display names for the 14 regions. Slugs and REGIONS[i]["name"]
# (English) are never changed - this is purely a display-layer lookup
# used by the rname() Jinja helper (see app.py) when lang == "uz".
REGION_NAME_UZ = {
    "tashkent-city": "Toshkent shahri",
    "tashkent": "Toshkent viloyati",
    "andijan": "Andijon",
    "bukhara": "Buxoro",
    "fergana": "Farg'ona",
    "jizzakh": "Jizzax",
    "kashkadarya": "Qashqadaryo",
    "khorezm": "Xorazm",
    "namangan": "Namangan",
    "navoiy": "Navoiy",
    "samarkand": "Samarqand",
    "sirdaryo": "Sirdaryo",
    "surkhandarya": "Surxondaryo",
    "karakalpakstan": "Qoraqalpog'iston",
}


def region_display_name(region: dict, lang: str) -> str:
    """Region name in the active language (Uzbek names for lang == "uz")."""
    if lang == "uz":
        return REGION_NAME_UZ.get(region.get("slug"), region["name"])
    return region["name"]


# Region names as they appear in data/districts.json -> region slug.
# Used to fall back to the regional centre and to highlight the right
# sidebar entry when a district page is open.
DATASET_KEY_TO_SLUG = {
    "Tashkent City": "tashkent-city",
    "Tashkent Region": "tashkent",
    "Republic of Karakalpakstan": "karakalpakstan",
    "Andijan Region": "andijan",
    "Bukhara Region": "bukhara",
    "Fergana Region": "fergana",
    "Jizzakh Region": "jizzakh",
    "Kashkadarya Region": "kashkadarya",
    "Khorezm Region": "khorezm",
    "Namangan Region": "namangan",
    "Navoiy Region": "navoiy",
    "Samarkand Region": "samarkand",
    "Surxondaryo Region": "surkhandarya",
    "Sirdaryo Region": "sirdaryo",
}


def slug_for_dataset_key(key: str):
    """Region slug for a dataset region name, or None if unknown."""
    return DATASET_KEY_TO_SLUG.get(key)
