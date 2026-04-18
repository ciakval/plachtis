import json
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from SkaRe.models import SailTicket, Boat, BoatClass
from django.contrib.auth.models import User


def _make_user():
    return User.objects.create_user(username='owner', password='pw')


def _make_boat(user, name='Albatros', sail_number='CZE1234'):
    bc = BoatClass.objects.get_or_create(
        name='P550', defaults={'category': BoatClass.Category.SAIL, 'order': 1}
    )[0]
    return Boat.objects.create(
        created_by=user, boat_class=bc, name=name, sail_number=sail_number,
        contact_person='Leader', contact_phone='123456789',
        hull_color='white',
    )


def _make_ticket(code='P550-001', color=None, status=None, boat=None,
                 rfid_uid='', pending_pairing=False):
    return SailTicket.objects.create(
        code=code,
        color=color or SailTicket.Color.P550,
        status=status or SailTicket.Status.ASHORE,
        boat=boat,
        rfid_uid=rfid_uid,
        pending_pairing=pending_pairing,
    )


@override_settings(RFID_API_KEY='testkey')
class RfidAliveAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('SkaRe:rfid_alive')

    def test_no_key_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_wrong_key_returns_401(self):
        response = self.client.get(self.url, HTTP_AUTHORIZATION='Bearer wrongkey')
        self.assertEqual(response.status_code, 401)

    def test_correct_key_returns_200(self):
        response = self.client.get(self.url, HTTP_AUTHORIZATION='Bearer testkey')
        self.assertEqual(response.status_code, 200)


@override_settings(RFID_API_KEY='testkey')
class RfidAliveResponseTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('SkaRe:rfid_alive')
        self.headers = {'HTTP_AUTHORIZATION': 'Bearer testkey'}

    def _get(self):
        response = self.client.get(self.url, **self.headers)
        return json.loads(response.content)

    def test_scanning_mode_when_no_pending(self):
        data = self._get()
        self.assertEqual(data['mode'], 'scanning')
        self.assertNotIn('pairing_ticket', data)

    def test_pairing_mode_when_pending(self):
        _make_ticket('P550-001', pending_pairing=True)
        data = self._get()
        self.assertEqual(data['mode'], 'pairing')
        self.assertEqual(data['pairing_ticket'], 'P550-001')

    def test_counts_only_tickets_with_boats(self):
        user = _make_user()
        boat = _make_boat(user)
        _make_ticket('P550-001', status=SailTicket.Status.ON_WATER, boat=boat)
        _make_ticket('P550-002', status=SailTicket.Status.ON_WATER)  # no boat
        _make_ticket('P550-003', status=SailTicket.Status.ASHORE, boat=boat)
        _make_ticket('P550-004', status=SailTicket.Status.LOST, boat=boat)  # excluded
        data = self._get()
        self.assertEqual(data['boats_on_water'], 1)
        self.assertEqual(data['boats_ashore'], 1)

    def test_timestamp_present(self):
        data = self._get()
        self.assertIn('timestamp', data)
