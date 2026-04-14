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


def _make_organizer(user):
    entity = Entity.objects.create(
        created_by=user, contact_email='o@example.com', contact_phone='+420777000000',
    )
    return Organizer.objects.create(
        entity=entity, first_name='Org', last_name='User',
        date_of_birth=date(1980, 1, 1),
    )


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


class ExportsAccessTest(TestCase):
    def test_anon_redirected(self):
        client = Client()
        url = reverse('SkaRe:exports_index')
        response = client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_non_infodesk_forbidden(self):
        client = Client()
        user = User.objects.create_user(username='regular', password='pw')
        client.login(username='regular', password='pw')
        url = reverse('SkaRe:exports_index')
        response = client.get(url)
        self.assertEqual(response.status_code, 403)


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

    def test_csv_includes_individual_participants(self):
        _make_individual(self.owner, arrived=True, health='diabetes')
        response = self.client.get(reverse('SkaRe:exports_medical_csv'))
        content = response.content.decode('utf-8-sig')
        self.assertIn('diabetes', content)


class OrganizerUnitsCsvAccessTest(TestCase):
    def test_anon_redirected(self):
        client = Client()
        url = reverse('SkaRe:exports_organizer_units_csv')
        response = client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_non_staff_forbidden(self):
        client = Client()
        user = User.objects.create_user(username='regular', password='pw')
        client.login(username='regular', password='pw')
        response = client.get(reverse('SkaRe:exports_organizer_units_csv'))
        self.assertEqual(response.status_code, 403)

    def test_staff_ok(self):
        client = Client()
        user = User.objects.create_user(username='admin', password='pw', is_staff=True)
        client.login(username='admin', password='pw')
        response = client.get(reverse('SkaRe:exports_organizer_units_csv'))
        self.assertEqual(response.status_code, 200)


class OrganizerUnitsCsvContentTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(username='admin2', password='pw', is_staff=True)
        self.client.login(username='admin2', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_contains_unit_name_and_bom(self):
        unit = _make_unit(self.owner, name='ExportTest Unit')
        _make_participant(unit, arrived=False)
        response = self.client.get(reverse('SkaRe:exports_organizer_units_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'\xef\xbb\xbf'))
        content = response.content.decode('utf-8-sig')
        self.assertIn('ExportTest Unit', content)

    def test_includes_all_units_not_only_arrived(self):
        unit = _make_unit(self.owner)
        _make_participant(unit, arrived=False)
        response = self.client.get(reverse('SkaRe:exports_organizer_units_csv'))
        reader = csv.reader(io.StringIO(response.content.decode('utf-8-sig')))
        rows = list(reader)
        self.assertGreaterEqual(len(rows), 2)

    def test_individual_row_present(self):
        _make_individual(self.owner)
        response = self.client.get(reverse('SkaRe:exports_organizer_units_csv'))
        content = response.content.decode('utf-8-sig')
        self.assertIn('Nováková', content)


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
