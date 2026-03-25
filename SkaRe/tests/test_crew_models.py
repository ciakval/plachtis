from datetime import date, timedelta

from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from SkaRe.models import Person, EventSettings, Unit, Entity, RegularParticipant, Crew, CrewMember, Boat, BoatClass


def _make_user(username):
    return User.objects.create_user(username=username, password='pw')


def _make_entity(user):
    return Entity.objects.create(
        created_by=user,
        contact_email='test@test.com',
        contact_phone='123456789',
    )


def _make_unit(user):
    entity = _make_entity(user)
    return Unit.objects.create(entity=entity, contact_person_name='Test')


def _make_person(unit, first_name='Jan', last_name='Novák'):
    return RegularParticipant.objects.create(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date(2000, 1, 1),
        unit=unit,
    )


class PersonVisibleToTest(TestCase):
    def setUp(self):
        self.owner = _make_user('owner')
        self.borrower = _make_user('borrower')
        self.unit = _make_unit(self.owner)
        self.person = _make_person(self.unit)

    def test_visible_to_field_exists(self):
        self.person.visible_to.add(self.borrower)
        self.assertIn(self.borrower, self.person.visible_to.all())

    def test_visible_to_empty_by_default(self):
        self.assertEqual(self.person.visible_to.count(), 0)

    def test_borrowed_persons_reverse_relation(self):
        self.person.visible_to.add(self.borrower)
        self.assertIn(
            self.person.pk,
            self.borrower.borrowed_persons.values_list('pk', flat=True),
        )


class CrewRegistrationDeadlineTest(TestCase):
    def test_is_crew_registration_open_when_deadline_null(self):
        settings = EventSettings.get_solo()
        settings.crew_registration_deadline = None
        settings.save()
        self.assertTrue(EventSettings.is_crew_registration_open())

    def test_get_crew_registration_deadline_returns_none_when_null(self):
        settings = EventSettings.get_solo()
        settings.crew_registration_deadline = None
        settings.save()
        self.assertIsNone(EventSettings.get_crew_registration_deadline())

    def test_is_crew_registration_open_before_deadline(self):
        settings = EventSettings.get_solo()
        settings.crew_registration_deadline = timezone.now() + timedelta(days=1)
        settings.save()
        self.assertTrue(EventSettings.is_crew_registration_open())

    def test_is_crew_registration_closed_after_deadline(self):
        settings = EventSettings.get_solo()
        settings.crew_registration_deadline = timezone.now() - timedelta(days=1)
        settings.save()
        self.assertFalse(EventSettings.is_crew_registration_open())


class CrewModelTest(TestCase):
    def setUp(self):
        self.user = _make_user('crew_owner')
        self.unit = _make_unit(self.user)
        self.person = _make_person(self.unit)
        self.person2 = _make_person(self.unit, first_name='Petr', last_name='Dvořák')
        bc = BoatClass.objects.create(name='P550', category=BoatClass.Category.SAIL, order=1)
        self.boat = Boat.objects.create(
            created_by=self.user, boat_class=bc,
            name='ALBATROS', contact_person='J', contact_phone='123456789',
        )

    def test_create_crew(self):
        crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        self.assertEqual(crew.category, 'S')
        self.assertEqual(crew.boat, self.boat)

    def test_unique_boat_category(self):
        Crew.objects.create(boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user)
        with self.assertRaises(IntegrityError):
            Crew.objects.create(boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user)

    def test_crew_str(self):
        crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        self.assertIn('ALBATROS', str(crew))
        self.assertIn('S', str(crew))

    def test_crew_member_helmsman(self):
        crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        member = CrewMember.objects.create(
            crew=crew,
            role=CrewMember.ROLE_HELMSMAN,
            participant=self.person.person_ptr,
        )
        self.assertEqual(member.role, CrewMember.ROLE_HELMSMAN)

    def test_crew_member_crew_role(self):
        crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        CrewMember.objects.create(
            crew=crew, role=CrewMember.ROLE_HELMSMAN, participant=self.person.person_ptr
        )
        member2 = CrewMember.objects.create(
            crew=crew, role=CrewMember.ROLE_CREW, participant=self.person2.person_ptr
        )
        self.assertEqual(crew.members.count(), 2)
        self.assertEqual(member2.role, CrewMember.ROLE_CREW)

    def test_crew_members_deleted_with_crew(self):
        crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        CrewMember.objects.create(
            crew=crew, role=CrewMember.ROLE_HELMSMAN, participant=self.person.person_ptr
        )
        crew_id = crew.id
        crew.delete()
        self.assertFalse(CrewMember.objects.filter(crew_id=crew_id).exists())
