"""Generates the 300 demo ("fake") member identities seeded by app.py.

Pure data generation only - no Flask/DB imports here on purpose, so it
stays trivially testable and side-effect free. app.py's
_seed_fake_members() is the only caller and does all the DB work.

Names are drawn from a large pool of common Uzbek given names and
surnames (140+ first names per gender, 120+ surnames) and combined with
a seeded RNG, so re-running generate_fake_members() always produces the
same 300 people - useful if the seeding step ever needs to be re-run by
hand. Emails are built from ten different construction patterns (dotted,
concatenated, initials, birth-year, nickname-style, etc.) picked at
random per person, across nine real email providers, so no two accounts
look machine-stamped from the same template.

DATASET_VERSION exists purely so app.py can detect "the generator changed
since these rows were inserted" and resync (delete + recreate) the demo
accounts on next boot, without ever touching real user rows.
"""
import random
from datetime import date, datetime, timedelta, timezone

DATASET_VERSION = 2  # bump whenever the name/email pools change materially

MALE_FIRST_NAMES = [
    "Aziz", "Bekzod", "Davron", "Elyor", "Farrukh", "Gayrat", "Hasan", "Ilhom", "Jasur", "Kamron",
    "Laziz", "Muhammad", "Nodir", "Otabek", "Qodir", "Rustam", "Sardor", "Sherzod", "Shavkat", "Akmal",
    "Bobur", "Diyor", "Eldor", "Farhod", "Golib", "Husan", "Ikrom", "Javlon", "Komil", "Lochin",
    "Mirzo", "Nurbek", "Odil", "Parviz", "Rasul", "Sanjar", "Tohir", "Umid", "Xurshid", "Yorqin",
    "Ziyodulla", "Alisher", "Bahodir", "Doston", "Zafar", "Ulugbek", "Sirojiddin", "Anvar", "Baxtiyor", "Dilshod",
    "Abbos", "Abdulla", "Abror", "Adham", "Ahror", "Akbar", "Alijon", "Ammar", "Anvarjon", "Asadbek",
    "Asror", "Avaz", "Aybek", "Azamat", "Bahrom", "Bekjon", "Bexruz", "Behzod", "Bilol", "Boburbek",
    "Botir", "Dadaxon", "Davlat", "Diyorbek", "Elbek", "Elmurod", "Erkin", "Ermek", "Fayzulla", "Firdavs",
    "Gulom", "Habibullo", "Hamza", "Hikmat", "Ibrohim", "Ilyos", "Imron", "Islom", "Ismoil", "Izzat",
    "Jahongir", "Jamshid", "Jaxongir", "Jonibek", "Jorabek", "Jumaboy", "Kamoliddin", "Karim", "Kobiljon", "Kudrat",
    "Lazizbek", "Mahmud", "Malik", "Mansur", "Maruf", "Mashrab", "Mavlon", "Miraziz", "Mirjalol", "Mirsaid",
    "Muzaffar", "Nasriddin", "Navruz", "Nizom", "Normurod", "Nuriddin", "Obid", "Ortiq", "Oybek", "Rahim",
    "Rahmatullo", "Ravshan", "Rustambek", "Saidakbar", "Sarvar", "Shahzod", "Shukrullo", "Sobir", "Suxrob", "Temur",
    "Tolib", "Turgun", "Ubaydulla", "Uktam", "Valijon", "Xasan", "Xayrulla", "Xolmurod", "Xoshimjon", "Yahyo",
    "Yodgor", "Yusuf", "Zayniddin", "Zohid",
]

FEMALE_FIRST_NAMES = [
    "Zarina", "Malika", "Dilnoza", "Nigora", "Sevara", "Gulnora", "Madina", "Feruza", "Shahnoza", "Nodira",
    "Kamola", "Yulduz", "Dilorom", "Zamira", "Sabina", "Mohira", "Nilufar", "Gulbahor", "Sitora", "Umida",
    "Aziza", "Barno", "Charos", "Dildora", "Elnora", "Farida", "Gulnoza", "Hilola", "Iroda", "Komila",
    "Laylo", "Munisa", "Nargiza", "Oydin", "Parvina", "Rayhona", "Shirin", "Vazira", "Zebo", "Gozal",
    "Halima", "Muborak", "Nasiba", "Sadoqat", "Tumaris", "Ozoda", "Mehriniso", "Gulchehra", "Shoira", "Robiya",
    "Anora", "Asal", "Bahora", "Chinora", "Dilbar", "Dilfuza", "Dilrabo", "Durdona", "Farangiz", "Farzona",
    "Gavhar", "Gulasal", "Gulchiroy", "Gulzoda", "Gulruh", "Gulsara", "Guzal", "Hurshida", "Iqbol", "Jamila",
    "Kamila", "Kumush", "Latofat", "Lobar", "Lola", "Mahbuba", "Malohat", "Manzura", "Marjona", "Maftuna",
    "Mehri", "Mohigul", "Mohinur", "Mukarrama", "Muslima", "Nafisa", "Naima", "Navbahor", "Nazira", "Nigina",
    "Nozima", "Oydinoy", "Oysha", "Sarvinoz", "Sevinch", "Shahida", "Shahlo", "Shokhida", "Shoxsanam", "Suvara",
    "Tahmina", "Umidahon", "Vasila", "Xadicha", "Xosiyat", "Yulduzxon", "Zarnigor", "Zebiniso", "Ziyoda", "Zulfiya",
    "Gulmira", "Shahzoda", "Feruzabonu", "Madinabonu", "Sevinchoy", "Mubina", "Sofiya", "Asila", "Marhabo", "Nodirabegim",
    "Latifa", "Muhlisa", "Gulhayo", "Dilnavoz", "Rano", "Gulzira", "Sabohat", "Shakhnoza", "Zeboxon", "Dilshoda",
]

# Male surname roots. Feminine forms follow the standard -a suffix rule
# (Karimov -> Karimova), applied automatically below.
MALE_SURNAMES = [
    "Karimov", "Yusupov", "Rashidov", "Islomov", "Abdullayev", "Rakhimov", "Nazarov", "Yuldashev", "Ergashev", "Saidov",
    "Tursunov", "Aliyev", "Xolmatov", "Mirzayev", "Umarov", "Sultonov", "Ganiyev", "Toshmatov", "Qodirov", "Ahmedov",
    "Juraev", "Nematov", "Xasanov", "Sharipov", "Mahmudov", "Rustamov", "Nurmatov", "Bekmuradov", "Xudoyberdiev", "Otajonov",
    "Abdurahmonov", "Abdusattorov", "Adilov", "Ahmadjonov", "Akbarov", "Alimov", "Anvarov", "Artikov", "Askarov", "Atabekov",
    "Aminov", "Azimov", "Bobojonov", "Boltayev", "Boymatov", "Choriyev", "Dadajonov", "Davlatov", "Egamberdiyev", "Elmuratov",
    "Eshonqulov", "Fayzullayev", "Gafurov", "Hakimov", "Hamidov", "Hasanov", "Ibragimov", "Ibrohimov", "Iminov", "Isakov",
    "Ismoilov", "Jalilov", "Jamolov", "Jorayev", "Kadirov", "Kamalov", "Kambarov", "Kenjayev", "Kholiqov", "Komilov",
    "Kurbanov", "Latipov", "Madaminov", "Mamatov", "Mansurov", "Maqsudov", "Marufov", "Mavlonov", "Mirsoatov", "Muhamedov",
    "Mukimov", "Muminov", "Nabiyev", "Nasriddinov", "Niyazov", "Normatov", "Nosirov", "Nurmuhamedov", "Obidov", "Odilov",
    "Ortiqov", "Otabekov", "Qahhorov", "Qambarov", "Qaharov", "Qosimov", "Qurbonov", "Rajabov", "Ravshanov", "Rizayev",
    "Sadullayev", "Safarov", "Sagdullayev", "Saidkhonov", "Salimov", "Samadov", "Sattorov", "Shamsiyev", "Shermatov", "Shodmonov",
    "Siddiqov", "Sobirov", "Solijonov", "Temirov", "Toirov", "Toshpulatov", "Turaqulov", "Ubaydullayev", "Xaydarov", "Xolikov",
    "Yodgorov", "Yoqubov", "Yusufov", "Zaripov", "Zokirov",
]
FEMALE_SURNAMES = [name + "a" for name in MALE_SURNAMES]

# Nine real providers, weighted so Gmail dominates like it does in reality.
EMAIL_DOMAINS = ["gmail.com", "mail.ru", "yandex.ru", "outlook.com", "icloud.com", "bk.ru", "list.ru", "rambler.ru", "inbox.ru"]
EMAIL_DOMAIN_WEIGHTS = [40, 15, 12, 10, 8, 6, 4, 3, 2]

SEED = 20260708  # fixed seed: same 300 people every run, easy to re-seed by hand


def _local_part(rng, first, surname, birth_year):
    """One of ten realistic email shapes, chosen at random per person."""
    f = first.lower()
    s = surname.lower()
    templates = [
        f"{f}.{s}{rng.randint(1, 999)}",
        f"{f}{s}{rng.randint(1, 99)}",
        f"{f}_{s}",
        f"{f[0]}.{s}{rng.randint(1, 999)}",
        f"{f}.{s[0]}{rng.randint(1, 99)}",
        f"{s}.{f}{rng.randint(1, 99)}",
        f"{f}{birth_year}",
        f"{f[:4]}{rng.randint(10, 999)}",
        f"{f}.{s}",
        f"{f}{rng.randint(1, 9999)}",
    ]
    return rng.choice(templates)


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
    max_attempts = n * 80
    while len(people) < n and attempts < max_attempts:
        attempts += 1
        is_male = rng.random() < 0.5
        first = rng.choice(MALE_FIRST_NAMES if is_male else FEMALE_FIRST_NAMES)
        surname = rng.choice(MALE_SURNAMES if is_male else FEMALE_SURNAMES)
        full_name = f"{first} {surname}"
        if full_name in used_names:
            continue
        used_names.add(full_name)

        birth_ordinal = rng.randint(birth_start, birth_end)
        birthdate_obj = date.fromordinal(birth_ordinal)

        email = None
        for _ in range(6):  # a few tries with fresh random shapes before giving up on this name
            candidate = f"{_local_part(rng, first, surname, birthdate_obj.year)}@" \
                        f"{rng.choices(EMAIL_DOMAINS, weights=EMAIL_DOMAIN_WEIGHTS, k=1)[0]}"
            if candidate not in used_emails:
                email = candidate
                break
        if email is None:
            continue
        used_emails.add(email)

        joined_days_ago = rng.randint(1, 600)
        created_at = now - timedelta(days=joined_days_ago, seconds=rng.randint(0, 86_400))

        people.append({
            "name": full_name,
            "email": email,
            "birthdate": birthdate_obj.isoformat(),
            "created_at": created_at,
        })

    return people
