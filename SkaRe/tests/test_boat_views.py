import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from SkaRe.models import BoatClass, SailRegistryEntry, Boat, Entity, Unit


class SailLookupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')
        SailRegistryEntry.objects.create(
            sail_number='CZE 42',
            boat_name='Rychlík',
            class_name='Cadet',
            subtype='Dřevěný',
            sail_area='7.50',
            harbor_number='523.10',
            harbor_name='5. oddíl Koráb',
            contact_person='Jan Novák',
        )

    def test_found_returns_json(self):
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url, {'q': 'CZE 42'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['boat_name'], 'Rychlík')
        self.assertEqual(data['subtype'], 'Dřevěný')

    def test_case_insensitive_lookup(self):
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url, {'q': 'cze 42'})
        self.assertEqual(response.status_code, 200)

    def test_not_found_returns_404(self):
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url, {'q': 'ZZZ 999'})
        self.assertEqual(response.status_code, 404)

    def test_missing_q_returns_400(self):
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_requires_login(self):
        self.client.logout()
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url, {'q': 'CZE 42'})
        self.assertEqual(response.status_code, 302)


class MyUnitViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')

    def _create_unit(self, unit_name='5. oddíl Koráb', evidence_id='523.10'):
        entity = Entity.objects.create(
            created_by=self.user,
            scout_unit_name=unit_name,
            scout_unit_evidence_id=evidence_id,
            contact_email='test@test.cz',
            contact_phone='+420123456789',
        )
        unit = Unit.objects.create(
            entity=entity,
            contact_person_name='Jan Novák',
        )
        return unit

    def test_returns_unit_data(self):
        self._create_unit()
        url = reverse('SkaRe:boat_my_unit')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['harbor_number'], '523.10')
        self.assertEqual(data['harbor_name'], '5. oddíl Koráb')
        self.assertEqual(data['contact_person'], 'Jan Novák')

    def test_no_unit_returns_404(self):
        url = reverse('SkaRe:boat_my_unit')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_multiple_units_returns_most_recent(self):
        self._create_unit(unit_name='Starší oddíl', evidence_id='111.11')
        self._create_unit(unit_name='Novější oddíl', evidence_id='999.99')
        url = reverse('SkaRe:boat_my_unit')
        response = self.client.get(url)
        data = json.loads(response.content)
        self.assertEqual(data['harbor_number'], '999.99')

    def test_requires_login(self):
        self.client.logout()
        url = reverse('SkaRe:boat_my_unit')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
