"""Generates the 300 demo ("fake") member identities seeded by app.py.

Pure data generation only - no Flask/DB imports here on purpose, so it
stays trivially testable and side-effect free. app.py's
_seed_fake_members() is the only caller and does all the DB work.

Names are drawn from common Uzbek given names and surnames and combined
deterministically (seeded RNG) so re-running generate_fake_members()
always produces the same 300 people - useful if the seeding step ever
needs to be re-run by hand.
"""
import random
from datetime import date, datetime, timedelta, timezone

MALE_FIRST_NAMES = [
    "Aziz", "Bekzod", "Davron", "Elyor", "Farrukh", "Gayrat", "Hasan", "Ilhom", "Jasur", "Kamron",
    "Laziz", "Muhammad", "Nodir", "Otabek", "Qodir", "Rustam", "Sardor", "Sherzod", "Shavkat", "Akmal",
    "Bobur", "Diyor", "Eldor", "Farhod", "Golib", "Husan", "Ikrom", "Javlon", "Komil", "Lochin",
    "Mirzo", "Nurbek", "Odil", "Parviz", "Rasul", "Sanjar", "Tohir", "Umid", "Xurshid", "Yorqin",
    "Ziyodulla", "Alisher", "Bahodir", "Doston", "Zafar", "Ulugbek", "Sirojiddin", "Anvar", "Baxtiyor", "Dilshod",
]

FEMALE_FIRST_NAMES = [
    "Zarina", "Malika", "Dilnoza", "Nigora", "Sevara", "Gulnora", "Madina", "Feruza", "Shahnoza", "Nodira",
    "Kamola", "Yulduz", "Dilorom", "Zamira", "Sabina", "Mohira", "Nilufar", "Gulbahor", "Sitora", "Umida",
    "Aziza", "Barno", "Charos", "Dildora", "Elnora", "Farida", "Gulnoza", "Hilola", "Iroda", "Komila",
    "Laylo", "Munisa", "Nargiza", "Oydin", "Parvina", "Rayhona", "Shirin", "Vazira", "Zebo", "Gozal",
    "Halima", "Muborak", "Nasiba", "Sadoqat", "Tumaris", "Ozoda", "Mehriniso", "Gulchehra", "Shoira", "Robiya",
]

# Feminine surnames follow the standard -a suffix rule (Karimov -> Karimova).
MALE_SURNAMES = [
    "Karimov", "Yusupov", "Rashidov", "Islomov", "Abdullayev", "Rakhimov", "Nazarov", "Yuldashev", "Ergashev", "Saidov",
    "Tursunov", "Aliyev", "Xolmatov", "Mirzayev", "Umarov", "Sultonov", "Ganiyev", "Toshmatov", "Qodirov", "Ahmedov",
    "Juraev", "Nematov", "Xasanov", "Sharipov", "Mahmudov", "Rustamov", "Nurmatov", "Bekmuradov", "Xudoyberdiev", "Otajonov",
]
FEMALE_SURNAMES = [name + "a" for name in MALE_SURNAMES]

EMAIL_DOMAINS = ["gmail.com", "mail.ru", "yandex.com", "inbox.uz", "bk.ru", "list.ru"]

SEED = 20260707  # fixed date-derived seed: same 300 people every run


def generate_fake_members(n=300, seed=SEED):
    """Return a list of n dicts: name, email, birthdate (YYYY-MM-DD), created_at (aware datetime)."""
    rng = random.Random(seed)
    used_names = set()
    used_emails = set()
    people = []

    birth_start = date(1965, 1, 1).toordinal()
    birth_end = date(2007, 12, 31).toordinal()
    now = datetime.now(timezone.utc)

    attempts = 0
    max_attempts = n * 60
    while len(people) < n and attempts < max_attempts:
        attempts += 1
        is_male = rng.random() < 0.5
        first = rng.choice(MALE_FIRST_NAMES if is_male else FEMALE_FIRST_NAMES)
        surname = rng.choice(MALE_SURNAMES if is_male else FEMALE_SURNAMES)
        full_name = f"{first} {surname}"
        if full_name in used_names:
            continue
        used_names.add(full_name)

        local_part = f"{first.lower()}.{surname.lower()}{rng.randint(1, 999)}"
        email = f"{local_part}@{rng.choice(EMAIL_DOMAINS)}"
        if email in used_emails:
            continue
        used_emails.add(email)

        birthdate = date.fromordinal(rng.randint(birth_start, birth_end)).isoformat()
        joined_days_ago = rng.randint(1, 600)
        created_at = now - timedelta(days=joined_days_ago, seconds=rng.randint(0, 86_400))

        people.append({
            "name": full_name,
            "email": email,
            "birthdate": birthdate,
            "created_at": created_at,
        })

    return people
