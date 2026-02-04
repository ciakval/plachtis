"""
Base seeder functionality for generating test data.
"""
import random
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from SkaRe.models import (
    Entity, Unit, RegularParticipant, IndividualParticipant, Organizer, Person
)

# Czech first names
FIRST_NAMES_MALE = [
    "Jan", "Petr", "Tomáš", "Martin", "Pavel", "Jakub", "Ondřej", "Lukáš",
    "David", "Michal", "Vojtěch", "Adam", "Filip", "Matěj", "Marek", "Daniel",
    "Jiří", "Josef", "Karel", "František", "Václav", "Antonín", "Jaroslav"
]

FIRST_NAMES_FEMALE = [
    "Jana", "Marie", "Eva", "Anna", "Hana", "Lenka", "Kateřina", "Lucie",
    "Petra", "Martina", "Tereza", "Michaela", "Veronika", "Barbora", "Nikola",
    "Monika", "Zuzana", "Kristýna", "Adéla", "Simona", "Markéta", "Klára"
]

LAST_NAMES = [
    "Novák", "Svoboda", "Novotný", "Dvořák", "Černý", "Procházka", "Kučera",
    "Veselý", "Horák", "Němec", "Pokorný", "Marek", "Pospíšil", "Hájek",
    "Jelínek", "Král", "Růžička", "Beneš", "Fiala", "Sedláček", "Doležal",
    "Zeman", "Kolář", "Navrátil", "Čermák", "Vaněk", "Urban", "Blažek"
]

NICKNAMES = [
    "Bobr", "Liška", "Vlk", "Medvěd", "Orel", "Sokol", "Vydra", "Rys",
    "Jezevec", "Sova", "Kuna", "Veverka", "Káně", "Tchoř", "Rosomák",
    "Jelen", "Srna", "Lasice", "Křeček", "Ježek", "Havran", "Datel",
    "", "", "", ""  # Some people don't have nicknames
]

TOWNS = [
    "Praha", "Brno", "Ostrava", "Plzeň", "Liberec", "Olomouc", "České Budějovice",
    "Hradec Králové", "Pardubice", "Zlín", "Havířov", "Kladno", "Most", "Opava",
    "Frýdek-Místek", "Karviná", "Jihlava", "Teplice", "Chomutov", "Přerov"
]

UNIT_NAMES = [
    "1. oddíl Ledňáček", "2. oddíl Orlí Hnízdo", "3. oddíl Polárka", 
    "4. oddíl Kovářov", "5. oddíl Koráb", "6. oddíl Dvojka", 
    "7. oddíl Sedmička", "8. oddíl Osmička", "9. oddíl Devítka",
    "10. oddíl Desítka", "11. oddíl Jedenáctka", "12. oddíl Dvanáctka",
    "13. středisko Delfín", "14. středisko Maják", "15. středisko Kompas",
    "Vodní skauti Modrá Kotva", "Přístav Praha", "Flotila Brno",
    "Námořníci Ostrava", "Říční vlci Plzeň", "Jezero Liberec"
]

DIETARY_RESTRICTIONS = [
    "", "", "", "", "",  # Most people don't have restrictions
    "Vegetarián", "Vegan", "Bezlepková dieta", "Bez laktózy",
    "Alergie na ořechy", "Alergie na vejce", "Bez vepřového",
    "Vegetarián, bez laktózy", "Alergie na mořské plody"
]

HEALTH_RESTRICTIONS = [
    "", "", "", "", "", "", "",  # Most people are healthy
    "Astma", "Alergie na včelí bodnutí", "Epilepsie", "Diabetes",
    "Alergie na penicilin", "Srdeční vada", "Alergie na pyl",
    "Cukrovka - inzulín", "Alergie na prach"
]

ACCOMMODATION_EXPECTATIONS = [
    "Stany pro 2 osoby", "Velký stan pro 8 osob", "Malé stany",
    "Karavan", "Podsadové stany", "Mix stanů různých velikostí",
    "2x stan pro 4 osoby", "Jeden velký a dva malé stany"
]


def random_phone():
    """Generate a random Czech phone number."""
    return f"+420 {random.randint(600, 799)} {random.randint(100, 999)} {random.randint(100, 999)}"


def random_email(first_name, last_name):
    """Generate a random email based on name."""
    domains = ["gmail.com", "seznam.cz", "email.cz", "centrum.cz", "volny.cz"]
    # Remove diacritics for email
    first = first_name.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ý", "y").replace("ě", "e").replace("š", "s").replace("č", "c").replace("ř", "r").replace("ž", "z").replace("ň", "n").replace("ť", "t").replace("ď", "d")
    last = last_name.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ý", "y").replace("ě", "e").replace("š", "s").replace("č", "c").replace("ř", "r").replace("ž", "z").replace("ň", "n").replace("ť", "t").replace("ď", "d")
    return f"{first}.{last}{random.randint(1, 99)}@{random.choice(domains)}"


def random_date_of_birth(category):
    """Generate a random date of birth based on category."""
    today = date.today()
    if category == Person.ScoutCategory.ADULT:
        age = random.randint(18, 50)
    elif category == Person.ScoutCategory.ROVER:
        age = random.randint(15, 20)
    elif category == Person.ScoutCategory.SCOUT:
        age = random.randint(11, 15)
    else:  # CUB
        age = random.randint(6, 11)
    
    birth_year = today.year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    return date(birth_year, birth_month, birth_day)


def random_person_data(category=None):
    """Generate random person data."""
    is_male = random.choice([True, False])
    first_name = random.choice(FIRST_NAMES_MALE if is_male else FIRST_NAMES_FEMALE)
    last_name = random.choice(LAST_NAMES)
    if not is_male and last_name.endswith("ý"):
        last_name = last_name[:-1] + "á"
    elif not is_male and not last_name.endswith("á"):
        last_name = last_name + "ová"
    
    if category is None:
        category = random.choice(list(Person.ScoutCategory))
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'nickname': random.choice(NICKNAMES),
        'date_of_birth': random_date_of_birth(category),
        'category': category,
        'health_restrictions': random.choice(HEALTH_RESTRICTIONS),
        'dietary_restrictions': random.choice(DIETARY_RESTRICTIONS),
        'relevant_information': "",
    }


def random_arrival_departure():
    """Generate random arrival and departure times."""
    # Event around July 2026
    base_date = timezone.make_aware(timezone.datetime(2026, 7, 10, 12, 0))
    arrival_offset = random.randint(-2, 1)  # Days before/after base
    arrival_hour = random.randint(8, 20)
    arrival = base_date + timedelta(days=arrival_offset, hours=arrival_hour - 12)
    
    departure = base_date + timedelta(days=random.randint(5, 8), hours=random.randint(8, 16) - 12)
    
    return arrival, departure


def get_or_create_test_user(username="testuser"):
    """Get or create a test user."""
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': f'{username}@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'is_staff': False,
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    return user


def create_unit(user, unit_name=None, num_participants=None):
    """Create a unit with participants."""
    if unit_name is None:
        unit_name = random.choice(UNIT_NAMES)
    
    if num_participants is None:
        num_participants = random.randint(3, 15)
    
    contact_person = random_person_data(Person.ScoutCategory.ADULT)
    arrival, departure = random_arrival_departure()
    
    entity = Entity.objects.create(
        created_by=user,
        scout_unit_name=unit_name,
        scout_unit_evidence_id=f"{random.randint(100, 999)}.{random.randint(10, 99)}",
        contact_email=random_email(contact_person['first_name'], contact_person['last_name']),
        contact_phone=random_phone(),
        expected_arrival=arrival,
        expected_departure=departure,
        home_town=random.choice(TOWNS),
    )
    
    unit = Unit.objects.create(
        entity=entity,
        contact_person_name=f"{contact_person['first_name']} {contact_person['last_name']}",
        backup_contact_phone=random_phone() if random.random() > 0.5 else "",
        boats_p550=random.randint(0, 3),
        boats_sail=random.randint(0, 2),
        boats_paddle=random.randint(0, 5),
        boats_motor=random.randint(0, 1),
        scarf_count=random.randint(0, num_participants + 5),
        accommodation_expectations=random.choice(ACCOMMODATION_EXPECTATIONS),
        estimated_accommodation_area=f"{random.randint(20, 100)} m²",
    )
    
    # Create participants
    for _ in range(num_participants):
        person_data = random_person_data()
        RegularParticipant.objects.create(unit=unit, **person_data)
    
    return unit


def create_individual_participant(user):
    """Create an individual participant."""
    person_data = random_person_data()
    arrival, departure = random_arrival_departure()
    
    entity = Entity.objects.create(
        created_by=user,
        contact_email=random_email(person_data['first_name'], person_data['last_name']),
        contact_phone=random_phone(),
        expected_arrival=arrival,
        expected_departure=departure,
        home_town=random.choice(TOWNS),
    )
    
    participant = IndividualParticipant.objects.create(
        entity=entity,
        boats_p550=random.randint(0, 1),
        boats_sail=random.randint(0, 1),
        boats_paddle=random.randint(0, 2),
        boats_motor=0,
        scarf_count=random.randint(0, 3),
        accommodation_expectations=random.choice(ACCOMMODATION_EXPECTATIONS) if random.random() > 0.5 else "",
        estimated_accommodation_area=f"{random.randint(5, 20)} m²" if random.random() > 0.5 else "",
        **person_data
    )
    
    return participant


def create_organizer(user):
    """Create an organizer."""
    person_data = random_person_data(Person.ScoutCategory.ADULT)
    arrival, departure = random_arrival_departure()
    
    entity = Entity.objects.create(
        created_by=user,
        contact_email=random_email(person_data['first_name'], person_data['last_name']),
        contact_phone=random_phone(),
        expected_arrival=arrival,
        expected_departure=departure,
        home_town=random.choice(TOWNS),
    )
    
    organizer = Organizer.objects.create(
        entity=entity,
        division=random.choice(list(Organizer.Division)),
        transport=random.choice(list(Organizer.TransportOptions)),
        need_lift=random.choice([True, False]),
        want_travel_order=random.choice([True, False]),
        accommodation=random.choice(list(Organizer.AccomodationOptions)),
        codex_agreement=True,
        **person_data
    )
    
    return organizer

