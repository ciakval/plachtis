import csv
import io
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from SkaRe.models import (
    Entity, Unit, RegularParticipant, IndividualParticipant, Organizer, Person,
)


def _make_infodesk():
    user = User.objects.create_user(username='desk', password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


def _make_unit(user, name='Bobři'):
    entity = Entity.objects.create(
        created_by=user, contact_email='u@example.com',
        contact_phone='+420777111222', scout_unit_name=name,
    )
    return Unit.objects.create(entity=entity, contact_person_name='Leader')


def _make_participant(unit, arrived=False, diet_vegan=False, health=''):
    p = RegularParticipant.objects.create(
        unit=unit, first_name='Jan', last_name='Novák',
        date_of_birth=date(2000, 1, 1),
        diet_vegan=diet_vegan,
        health_restrictions=health,
    )
    if arrived:
        p.attendance_status = Person.AttendanceStatus.ARRIVED
        p.save()
    return p


def _make_individual(user, arrived=False, health=''):
    entity = Entity.objects.create(
        created_by=user, contact_email='i@example.com',
        contact_phone='+420777333444',
    )
    p = IndividualParticipant.objects.create(
        entity=entity, first_name='Marie', last_name='Nováková',
        date_of_birth=date(1990, 5, 10), health_restrictions=health,
    )
    if arrived:
        p.attendance_status = Person.AttendanceStatus.ARRIVED
        p.save()
    return p


class ExportsIndexTest(TestCase):
    def setUp(self):
        self.client = Client()
        _make_infodesk()
        self.client.login(username='desk', password='pw')

    def test_index_returns_200(self):
        url = reverse('SkaRe:exports_index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_index_has_kitchen_link(self):
        response = self.client.get(reverse('SkaRe:exports_index'))
        self.assertContains(response, reverse('SkaRe:exports_kitchen_csv'))

    def test_index_has_medical_link(self):
        response = self.client.get(reverse('SkaRe:exports_index'))
        self.assertContains(response, reverse('SkaRe:exports_medical_csv'))


class KitchenCsvTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_csv_only_includes_arrived_people(self):
        unit = _make_unit(self.owner)
        arrived = _make_participant(unit, arrived=True)
        not_arrived = _make_participant(unit, arrived=False)
        response = self.client.get(reverse('SkaRe:exports_kitchen_csv'))
        content = response.content.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        self.assertEqual(len(rows), 2)  # header + 1 arrived person

    def test_csv_content_type_is_csv(self):
        response = self.client.get(reverse('SkaRe:exports_kitchen_csv'))
        self.assertIn('text/csv', response['Content-Type'])

    def test_csv_includes_dietary_columns(self):
        unit = _make_unit(self.owner)
        _make_participant(unit, arrived=True, diet_vegan=True)
        response = self.client.get(reverse('SkaRe:exports_kitchen_csv'))
        content = response.content.decode('utf-8-sig')
        self.assertIn('Vegan', content)

    def test_csv_has_bom_for_excel(self):
        response = self.client.get(reverse('SkaRe:exports_kitchen_csv'))
        self.assertTrue(response.content.startswith(b'\xef\xbb\xbf'))


class KitchenPrintTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_print_view_returns_200(self):
        response = self.client.get(reverse('SkaRe:exports_kitchen_print'))
        self.assertEqual(response.status_code, 200)

    def test_print_view_shows_arrived_people(self):
        unit = _make_unit(self.owner, 'Racci')
        _make_participant(unit, arrived=True)
        response = self.client.get(reverse('SkaRe:exports_kitchen_print'))
        self.assertContains(response, 'Racci')

    def test_print_view_excludes_not_arrived(self):
        unit = _make_unit(self.owner, 'Racci')
        _make_participant(unit, arrived=False)
        response = self.client.get(reverse('SkaRe:exports_kitchen_print'))
        self.assertNotContains(response, 'Racci')


class MedicalCsvTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_csv_only_includes_arrived_people_with_health_restrictions(self):
        unit = _make_unit(self.owner)
        arrived_sick = _make_participant(unit, arrived=True, health='peanut allergy')
        arrived_healthy = _make_participant(unit, arrived=True, health='')
        not_arrived_sick = _make_participant(unit, arrived=False, health='asthma')
        response = self.client.get(reverse('SkaRe:exports_medical_csv'))
        content = response.content.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        self.assertEqual(len(rows), 2)  # header + 1 arrived sick person

    def test_medical_csv_contains_health_info(self):
        unit = _make_unit(self.owner)
        _make_participant(unit, arrived=True, health='carries EpiPen')
        response = self.client.get(reverse('SkaRe:exports_medical_csv'))
        content = response.content.decode('utf-8-sig')
        self.assertIn('carries EpiPen', content)

    def test_medical_csv_content_type(self):
        response = self.client.get(reverse('SkaRe:exports_medical_csv'))
        self.assertIn('text/csv', response['Content-Type'])


class MedicalPrintTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_print_view_returns_200(self):
        response = self.client.get(reverse('SkaRe:exports_medical_print'))
        self.assertEqual(response.status_code, 200)

    def test_print_view_shows_health_info(self):
        unit = _make_unit(self.owner, 'Bobři')
        _make_participant(unit, arrived=True, health='severe nut allergy')
        response = self.client.get(reverse('SkaRe:exports_medical_print'))
        self.assertContains(response, 'severe nut allergy')

    def test_print_view_excludes_arrived_with_no_health_restrictions(self):
        unit = _make_unit(self.owner, 'Bobři')
        _make_participant(unit, arrived=True, health='')
        response = self.client.get(reverse('SkaRe:exports_medical_print'))
        self.assertNotContains(response, 'Novák')
