from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from SkaRe.models import SailTicket, SailTicketLog, Boat, BoatClass


def _make_infodesk():
    user = User.objects.create_user(username='desk', password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


def _make_boat(user, name='Albatros', sail_number='CZE1234'):
    bc = BoatClass.objects.get_or_create(
        name='P550', defaults={'category': BoatClass.Category.SAIL, 'order': 1}
    )[0]
    return Boat.objects.create(
        created_by=user, boat_class=bc, name=name, sail_number=sail_number,
        contact_person='Leader', contact_phone='123456789',
    )


def _make_ticket(code='P550-001', color=None, status=None, boat=None, rfid_uid=''):
    kwargs = {
        'code': code,
        'color': color or SailTicket.Color.P550,
        'rfid_uid': rfid_uid,
    }
    if status:
        kwargs['status'] = status
    if boat:
        kwargs['boat'] = boat
    return SailTicket.objects.create(**kwargs)


class TicketListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')

    def test_list_returns_200(self):
        url = reverse('SkaRe:ticket_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_list_shows_ticket_codes(self):
        _make_ticket('P550-001')
        _make_ticket('SAIL-001', SailTicket.Color.SAIL)
        url = reverse('SkaRe:ticket_list')
        response = self.client.get(url)
        self.assertContains(response, 'P550-001')
        self.assertContains(response, 'SAIL-001')

    def test_list_filter_by_status(self):
        _make_ticket('P550-001', status=SailTicket.Status.ON_WATER)
        _make_ticket('P550-002', status=SailTicket.Status.ASHORE)
        url = reverse('SkaRe:ticket_list') + '?status=on_water'
        response = self.client.get(url)
        self.assertContains(response, 'P550-001')
        self.assertNotContains(response, 'P550-002')

    def test_list_filter_by_color(self):
        _make_ticket('P550-001', SailTicket.Color.P550)
        _make_ticket('SAIL-001', SailTicket.Color.SAIL)
        url = reverse('SkaRe:ticket_list') + '?color=p550'
        response = self.client.get(url)
        self.assertContains(response, 'P550-001')
        self.assertNotContains(response, 'SAIL-001')


class TicketDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.ticket = _make_ticket('P550-001')

    def test_detail_returns_200(self):
        url = reverse('SkaRe:ticket_detail', kwargs={'ticket_id': self.ticket.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'P550-001')

    def test_detail_shows_logs(self):
        SailTicketLog.objects.create(
            ticket=self.ticket,
            status=SailTicket.Status.ON_WATER,
            changed_by=self.desk,
        )
        url = reverse('SkaRe:ticket_detail', kwargs={'ticket_id': self.ticket.pk})
        response = self.client.get(url)
        self.assertContains(response, 'on_water')


class TicketSetStatusTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.ticket = _make_ticket('P550-001')

    def _post(self, new_status, next_url=None):
        url = reverse('SkaRe:ticket_set_status', kwargs={'ticket_id': self.ticket.pk})
        data = {'new_status': new_status}
        if next_url:
            data['next'] = next_url
        return self.client.post(url, data)

    def test_set_on_water_updates_status(self):
        self._post('on_water')
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, SailTicket.Status.ON_WATER)

    def test_set_status_creates_log(self):
        self._post('on_water')
        self.assertEqual(SailTicketLog.objects.filter(ticket=self.ticket).count(), 1)
        log = SailTicketLog.objects.get(ticket=self.ticket)
        self.assertEqual(log.status, SailTicket.Status.ON_WATER)
        self.assertEqual(log.changed_by, self.desk)

    def test_invalid_status_returns_400(self):
        response = self._post('flying')
        self.assertEqual(response.status_code, 400)

    def test_redirects_to_next(self):
        next_url = reverse('SkaRe:ticket_lookup')
        response = self._post('on_water', next_url=next_url)
        self.assertRedirects(response, next_url)

    def test_get_not_allowed(self):
        url = reverse('SkaRe:ticket_set_status', kwargs={'ticket_id': self.ticket.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_external_next_url_is_ignored(self):
        response = self._post('on_water', next_url='https://evil.com/steal')
        self.assertRedirects(
            response,
            reverse('SkaRe:ticket_detail', kwargs={'ticket_id': self.ticket.pk})
        )


class TicketPairRfidTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.ticket = _make_ticket('P550-001')

    def test_pair_rfid_sets_pending_pairing(self):
        url = reverse('SkaRe:ticket_pair_rfid', kwargs={'ticket_id': self.ticket.pk})
        self.client.post(url)
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.pending_pairing)

    def test_pair_rfid_clears_other_pending(self):
        other = _make_ticket('P550-002')
        other.pending_pairing = True
        other.save()
        url = reverse('SkaRe:ticket_pair_rfid', kwargs={'ticket_id': self.ticket.pk})
        self.client.post(url)
        other.refresh_from_db()
        self.assertFalse(other.pending_pairing)
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.pending_pairing)


class TicketLookupTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_lookup_empty_shows_no_results(self):
        url = reverse('SkaRe:ticket_lookup')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_lookup_by_code(self):
        _make_ticket('P550-042')
        url = reverse('SkaRe:ticket_lookup') + '?q=P550-042'
        response = self.client.get(url)
        self.assertContains(response, 'P550-042')

    def test_lookup_by_boat_name(self):
        boat = _make_boat(self.owner, name='Albatros')
        _make_ticket('P550-001', boat=boat)
        url = reverse('SkaRe:ticket_lookup') + '?q=Albatros'
        response = self.client.get(url)
        self.assertContains(response, 'P550-001')

    def test_lookup_by_sail_number(self):
        boat = _make_boat(self.owner, sail_number='CZE9999')
        _make_ticket('P550-002', boat=boat)
        url = reverse('SkaRe:ticket_lookup') + '?q=CZE9999'
        response = self.client.get(url)
        self.assertContains(response, 'P550-002')


class BulkTicketCreateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_get_shows_form(self):
        url = reverse('SkaRe:ticket_create_bulk')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_creates_boat_tickets_and_reserves(self):
        _make_boat(self.owner)  # one P550 boat
        url = reverse('SkaRe:ticket_create_bulk')
        response = self.client.post(url, {
            'p550_reserves': 2,
            'sail_reserves': 0,
            'other_reserves': 0,
            'spare_count': 1,
            'confirm': '1',
        })
        self.assertRedirects(response, reverse('SkaRe:ticket_list'))
        # 1 boat ticket + 2 reserves + 1 spare = 4
        self.assertEqual(SailTicket.objects.count(), 4)

    def test_boat_ticket_has_boat_fk_set(self):
        boat = _make_boat(self.owner)
        url = reverse('SkaRe:ticket_create_bulk')
        self.client.post(url, {
            'p550_reserves': 0, 'sail_reserves': 0,
            'other_reserves': 0, 'spare_count': 0,
            'confirm': '1',
        })
        ticket = SailTicket.objects.filter(boat=boat).first()
        self.assertIsNotNone(ticket)

    def test_spare_tickets_have_no_boat(self):
        url = reverse('SkaRe:ticket_create_bulk')
        self.client.post(url, {
            'p550_reserves': 0, 'sail_reserves': 0,
            'other_reserves': 0, 'spare_count': 3,
            'confirm': '1',
        })
        spares = SailTicket.objects.filter(color=SailTicket.Color.SPARE)
        self.assertEqual(spares.count(), 3)
        self.assertTrue(all(t.boat is None for t in spares))

    def test_skips_boats_already_assigned_a_ticket(self):
        boat = _make_boat(self.owner)
        _make_ticket('P550-001', boat=boat)
        url = reverse('SkaRe:ticket_create_bulk')
        self.client.post(url, {
            'p550_reserves': 0, 'sail_reserves': 0,
            'other_reserves': 0, 'spare_count': 0,
            'confirm': '1',
        })
        # Bulk create wipes all tickets and re-creates; boat gets exactly one ticket
        self.assertEqual(SailTicket.objects.filter(boat=boat).count(), 1)
        # Total tickets: 1 (just the one boat)
        self.assertEqual(SailTicket.objects.count(), 1)


class TicketOnWaterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_on_water_shows_only_on_water_tickets(self):
        boat = _make_boat(self.owner, 'Albatros')
        _make_ticket('P550-001', boat=boat, status=SailTicket.Status.ON_WATER)
        _make_ticket('P550-002', status=SailTicket.Status.ASHORE)
        url = reverse('SkaRe:ticket_on_water')
        response = self.client.get(url)
        self.assertContains(response, 'P550-001')
        self.assertNotContains(response, 'P550-002')


class TicketExportCsvTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_csv_export_returns_csv(self):
        boat = _make_boat(self.owner, 'Albatros', 'CZE1234')
        _make_ticket('P550-001', boat=boat)
        url = reverse('SkaRe:ticket_export_csv')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode()
        self.assertIn('P550-001', content)
        self.assertIn('Albatros', content)


class TicketUnpairRfidTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')

    def test_unpair_clears_rfid_uid(self):
        ticket = _make_ticket('P550-001', rfid_uid='AABBCCDD')
        url = reverse('SkaRe:ticket_unpair_rfid', args=[ticket.pk])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('SkaRe:ticket_detail', args=[ticket.pk]))
        ticket.refresh_from_db()
        self.assertEqual(ticket.rfid_uid, '')

    def test_unpair_creates_log_entry(self):
        ticket = _make_ticket('P550-001', rfid_uid='AABBCCDD')
        url = reverse('SkaRe:ticket_unpair_rfid', args=[ticket.pk])
        self.client.post(url)
        log = SailTicketLog.objects.get(ticket=ticket)
        self.assertIn('unpaired', log.note.lower())
        self.assertEqual(log.changed_by, self.desk)

    def test_unpair_requires_infodesk(self):
        User.objects.create_user(username='pleb', password='pw')
        self.client.login(username='pleb', password='pw')
        ticket = _make_ticket('P550-001', rfid_uid='AABBCCDD')
        url = reverse('SkaRe:ticket_unpair_rfid', args=[ticket.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_unpair_returns_400_when_no_rfid(self):
        ticket = _make_ticket('P550-001', rfid_uid='')
        url = reverse('SkaRe:ticket_unpair_rfid', args=[ticket.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)

    def test_unpair_requires_post(self):
        ticket = _make_ticket('P550-001', rfid_uid='AABBCCDD')
        url = reverse('SkaRe:ticket_unpair_rfid', args=[ticket.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)
