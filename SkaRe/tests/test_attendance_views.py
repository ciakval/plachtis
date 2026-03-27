from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.utils import timezone
from SkaRe.models import (
    Entity, Unit, RegularParticipant, IndividualParticipant,
    Organizer, Person, AttendanceLog,
)


def _make_infodesk():
    user = User.objects.create_user(username='desk', password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


def _make_unit(user, name='Bobři'):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='u@example.com',
        contact_phone='123456789',
        scout_unit_name=name,
    )
    return Unit.objects.create(entity=entity, contact_person_name='Leader')


def _make_participant(unit, first='Jan', last='Novák'):
    return RegularParticipant.objects.create(
        unit=unit,
        first_name=first,
        last_name=last,
        date_of_birth=date(2000, 1, 1),
    )


def _make_individual(user):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='i@example.com',
        contact_phone='123456789',
    )
    return IndividualParticipant.objects.create(
        entity=entity,
        first_name='Marie',
        last_name='Nováková',
        date_of_birth=date(1990, 5, 10),
    )


def _make_organizer(user):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='o@example.com',
        contact_phone='123456789',
    )
    return Organizer.objects.create(
        entity=entity,
        first_name='Petr',
        last_name='Dvořák',
        date_of_birth=date(1985, 3, 20),
    )


class AttendanceUnitsListTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_units_list_shows_unit_names(self):
        _make_unit(self.owner, 'Racci')
        url = reverse('SkaRe:attendance_units_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Racci')

    def test_units_list_shows_arrival_counts(self):
        unit = _make_unit(self.owner, 'Racci')
        p1 = _make_participant(unit, 'Alice', 'Smith')
        p2 = _make_participant(unit, 'Bob', 'Jones')
        p1.attendance_status = Person.AttendanceStatus.ARRIVED
        p1.save()
        url = reverse('SkaRe:attendance_units_list')
        response = self.client.get(url)
        self.assertContains(response, '1')   # 1 arrived
        self.assertContains(response, '2')   # 2 total


class AttendanceUnitDetailTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.unit = _make_unit(self.owner)
        self.p1 = _make_participant(self.unit, 'Alice', 'Smith')

    def test_unit_detail_shows_participant_names(self):
        url = reverse('SkaRe:attendance_unit_detail', kwargs={'unit_id': self.unit.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice')

    def test_unit_detail_404_for_missing_unit(self):
        url = reverse('SkaRe:attendance_unit_detail', kwargs={'unit_id': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class AttendanceSetStatusTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.unit = _make_unit(self.owner)
        self.person = _make_participant(self.unit)

    def _post(self, person, new_status, next_url=None):
        url = reverse('SkaRe:attendance_set_status', kwargs={'person_id': person.pk})
        data = {'new_status': new_status}
        if next_url:
            data['next'] = next_url
        return self.client.post(url, data)

    def test_set_arrived_updates_status(self):
        self._post(self.person, 'arrived')
        self.person.refresh_from_db()
        self.assertEqual(self.person.attendance_status, 'arrived')

    def test_set_arrived_sets_arrived_at(self):
        self._post(self.person, 'arrived')
        self.person.refresh_from_db()
        self.assertIsNotNone(self.person.arrived_at)

    def test_set_departed_sets_departed_at(self):
        self._post(self.person, 'departed')
        self.person.refresh_from_db()
        self.assertIsNotNone(self.person.departed_at)

    def test_set_not_coming_clears_timestamps(self):
        self.person.arrived_at = timezone.now()
        self.person.save()
        self._post(self.person, 'not_coming')
        self.person.refresh_from_db()
        self.assertEqual(self.person.attendance_status, 'not_coming')

    def test_creates_attendance_log_entry(self):
        self._post(self.person, 'arrived')
        self.assertEqual(AttendanceLog.objects.filter(person=self.person).count(), 1)
        log = AttendanceLog.objects.get(person=self.person)
        self.assertEqual(log.status, 'arrived')
        self.assertEqual(log.changed_by, self.desk)

    def test_invalid_status_returns_400(self):
        response = self._post(self.person, 'flying')
        self.assertEqual(response.status_code, 400)

    def test_redirects_to_next_url(self):
        next_url = reverse('SkaRe:attendance_unit_detail', kwargs={'unit_id': self.unit.pk})
        response = self._post(self.person, 'arrived', next_url=next_url)
        self.assertRedirects(response, next_url)

    def test_get_method_not_allowed(self):
        url = reverse('SkaRe:attendance_set_status', kwargs={'person_id': self.person.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class AttendanceMarkAllArrivedTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.unit = _make_unit(self.owner)
        self.p1 = _make_participant(self.unit, 'Alice', 'Smith')
        self.p2 = _make_participant(self.unit, 'Bob', 'Jones')

    def test_marks_all_expected_as_arrived(self):
        url = reverse('SkaRe:attendance_unit_mark_all_arrived', kwargs={'unit_id': self.unit.pk})
        self.client.post(url)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.attendance_status, 'arrived')
        self.assertEqual(self.p2.attendance_status, 'arrived')

    def test_skips_already_departed(self):
        self.p2.attendance_status = Person.AttendanceStatus.DEPARTED
        self.p2.save()
        url = reverse('SkaRe:attendance_unit_mark_all_arrived', kwargs={'unit_id': self.unit.pk})
        self.client.post(url)
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.attendance_status, 'departed')

    def test_creates_log_entries(self):
        url = reverse('SkaRe:attendance_unit_mark_all_arrived', kwargs={'unit_id': self.unit.pk})
        self.client.post(url)
        self.assertEqual(AttendanceLog.objects.count(), 2)


class AttendanceIndividualsListTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_shows_individual_names(self):
        _make_individual(self.owner)
        url = reverse('SkaRe:attendance_individuals_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nováková')


class AttendanceOrganizersListTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_shows_organizer_names(self):
        _make_organizer(self.owner)
        url = reverse('SkaRe:attendance_organizers_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dvořák')
