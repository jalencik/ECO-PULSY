"""Generates the demo ("fake") member identities seeded by app.py.

Pure data generation only - no Flask/DB imports here on purpose, so it
stays trivially testable and side-effect free. app.py's
_seed_fake_members() is the only caller and does all the DB work.

The seeder tops the platform up to TARGET_TOTAL_USERS accounts: it
counts the real (is_fake=False) rows first and only generates enough
demo identities to fill the gap, so the combined total the owner and
the Queen see always lands on the same round number while real users
are never duplicated or displaced. Plain admins never see these rows
at all (see admin.py).

Identities are drawn from three name pools reflecting who actually
signs up on an Uzbek site: mostly Uzbek names, a meaningful minority of
Russian names, and a small share of English ones. Every full name is
unique - no repeats across the whole batch. Emails are built from ten
different construction patterns (dotted, concatenated, initials,
birth-year, nickname-style, etc.) picked at random per person across
nine real email providers, so no two accounts look machine-stamped
from the same template.

DATASET_VERSION exists purely so app.py can detect "the generator changed
since these rows were inserted" and resync (delete + recreate) the demo
accounts on next boot, without ever touching real user rows.
"""
import random
from datetime import date, datetime, timedelta, timezone

DATASET_VERSION = 3  # bump whenever the pools / target size change materially

# The combined (real + demo) total the seeder tops the users table up to.
# Only the owner and the Queen ever see this combined figure.
TARGET_TOTAL_USERS = 970

UZBEK_MALE_FIRST_NAMES = [
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

UZBEK_FEMALE_FIRST_NAMES = [
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
UZBEK_MALE_SURNAMES = [
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
UZBEK_FEMALE_SURNAMES = [name + "a" for name in UZBEK_MALE_SURNAMES]

RUSSIAN_MALE_FIRST_NAMES = [
    "Aleksandr", "Dmitriy", "Sergey", "Andrey", "Aleksey", "Maksim", "Ivan", "Mikhail", "Nikolay", "Vladimir",
    "Yevgeniy", "Viktor", "Anton", "Artyom", "Denis", "Igor", "Kirill", "Oleg", "Pavel", "Roman",
    "Stepan", "Vadim", "Valeriy", "Yuriy", "Gennadiy", "Boris", "Konstantin", "Leonid", "Pyotr", "Ruslan",
]
RUSSIAN_FEMALE_FIRST_NAMES = [
    "Anastasiya", "Yelena", "Olga", "Natalya", "Tatyana", "Irina", "Svetlana", "Yekaterina", "Mariya", "Anna",
    "Yuliya", "Viktoriya", "Darya", "Polina", "Alina", "Kseniya", "Valentina", "Galina", "Lyudmila", "Nadezhda",
    "Oksana", "Marina", "Larisa", "Vera", "Sofya", "Alyona", "Kristina", "Margarita", "Veronika", "Tamara",
]
# Only -ov / -ev / -in roots, so the same feminine "-a" rule applies
# cleanly (Ivanov -> Ivanova, Nikitin -> Nikitina).
RUSSIAN_MALE_SURNAMES = [
    "Ivanov", "Petrov", "Sidorov", "Smirnov", "Kuznetsov", "Popov", "Vasilyev", "Sokolov", "Mikhaylov", "Novikov",
    "Fyodorov", "Morozov", "Volkov", "Alekseyev", "Lebedev", "Semyonov", "Yegorov", "Pavlov", "Kozlov", "Stepanov",
    "Nikolayev", "Orlov", "Andreyev", "Makarov", "Nikitin", "Zakharov", "Zaytsev", "Borisov", "Romanov", "Belov",
]
RUSSIAN_FEMALE_SURNAMES = [name + "a" for name in RUSSIAN_MALE_SURNAMES]

ENGLISH_MALE_FIRST_NAMES = [
    "James", "John", "Michael", "David", "Daniel", "Thomas", "Andrew", "Ryan", "Kevin", "Brian",
    "Jason", "Eric", "Mark", "Steven", "Paul", "Adam", "Nathan", "Peter", "George", "Henry",
]
ENGLISH_FEMALE_FIRST_NAMES = [
    "Emily", "Sarah", "Jessica", "Emma", "Olivia", "Sophia", "Hannah", "Grace", "Chloe", "Laura",
    "Rachel", "Megan", "Amy", "Kate", "Lucy", "Julia", "Alice", "Helen", "Victoria", "Charlotte",
]
# English surnames are the same for both genders.
ENGLISH_SURNAMES = [
    "Smith", "Johnson", "Brown", "Taylor", "Wilson", "Davies", "Evans", "Walker", "White", "Green",
    "Hall", "Wood", "Clarke", "Hughes", "Turner", "Carter", "Parker", "Collins", "Bennett", "Murphy",
]

# (male first, female first, male surname, female surname) per origin,
# weighted to look like a real Uzbek user base: mostly Uzbek names, a
# meaningful minority of Russian ones, a small share of English ones.
NAME_POOLS = [
    (UZBEK_MALE_FIRST_NAMES, UZBEK_FEMALE_FIRST_NAMES, UZBEK_MALE_SURNAMES, UZBEK_FEMALE_SURNAMES),
    (RUSSIAN_MALE_FIRST_NAMES, RUSSIAN_FEMALE_FIRST_NAMES, RUSSIAN_MALE_SURNAMES, RUSSIAN_FEMALE_SURNAMES),
    (ENGLISH_MALE_FIRST_NAMES, ENGLISH_FEMALE_FIRST_NAMES, ENGLISH_SURNAMES, ENGLISH_SURNAMES),
]
NAME_POOL_WEIGHTS = [78, 14, 8]

# Nine real providers, weighted so Gmail dominates like it does in reality.
EMAIL_DOMAINS = ["gmail.com", "mail.ru", "yandex.ru", "outlook.com", "icloud.com", "bk.ru", "list.ru", "rambler.ru", "inbox.ru"]
EMAIL_DOMAIN_WEIGHTS = [40, 15, 12, 10, 8, 6, 4, 3, 2]

SEED = 20260709  # fixed seed: same people every run, easy to re-seed by hand


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


def generate_fake_members(n, seed=SEED):
    """Return a list of n dicts: name, email, birthdate (YYYY-MM-DD), created_at (aware datetime).

    Every full name and every email in the batch is unique.
    """
    rng = random.Random(seed)
    used_names = set()
    used_emails = set()
    people = []

    birth_start = date(1965, 1, 1).toordinal()
    birth_end = date(2008, 12, 31).toordinal()
    now = datetime.now(timezone.utc)

    attempts = 0
    max_attempts = max(n, 1) * 80
    while len(people) < n and attempts < max_attempts:
        attempts += 1
        male_first, female_first, male_sur, female_sur = rng.choices(
            NAME_POOLS, weights=NAME_POOL_WEIGHTS, k=1)[0]
        is_male = rng.random() < 0.5
        first = rng.choice(male_first if is_male else female_first)
        surname = rng.choice(male_sur if is_male else female_sur)
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

        joined_days_ago = rng.randint(1, 720)
        created_at = now - timedelta(days=joined_days_ago, seconds=rng.randint(0, 86_400))

        people.append({
            "name": full_name,
            "email": email,
            "birthdate": birthdate_obj.isoformat(),
            "created_at": created_at,
        })

    return people
