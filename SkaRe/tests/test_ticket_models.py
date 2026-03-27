from django.test import TestCase
from django.contrib.auth.models import User
from SkaRe.models import SailTicket, SailTicketLog, Boat, BoatClass


def _make_boat(user):
    bc = BoatClass.objects.create(name='P550', category=BoatClass.Category.SAIL, order=1)
    return Boat.objects.create(
        created_by=user,
        boat_class=bc,
        name='Albatros',
        contact_person='Jan',
        contact_phone='123456789',
    )


class SailTicketTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.boat = _make_boat(self.user)

    def test_status_defaults_to_ashore(self):
        ticket = SailTicket.objects.create(
            code='P550-001',
            color=SailTicket.Color.P550,
        )
        self.assertEqual(ticket.status, SailTicket.Status.ASHORE)

    def test_pending_pairing_defaults_to_false(self):
        ticket = SailTicket.objects.create(code='P550-002', color=SailTicket.Color.P550)
        self.assertFalse(ticket.pending_pairing)

    def test_rfid_uid_blank_by_default(self):
        ticket = SailTicket.objects.create(code='P550-003', color=SailTicket.Color.P550)
        self.assertEqual(ticket.rfid_uid, '')

    def test_boat_can_be_assigned(self):
        ticket = SailTicket.objects.create(
            code='P550-004',
            color=SailTicket.Color.P550,
            boat=self.boat,
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.boat, self.boat)

    def test_boat_fk_nulls_on_boat_deletion(self):
        ticket = SailTicket.objects.create(
            code='P550-005',
            color=SailTicket.Color.P550,
            boat=self.boat,
        )
        self.boat.delete()
        ticket.refresh_from_db()
        self.assertIsNone(ticket.boat)

    def test_code_is_unique(self):
        from django.db import IntegrityError
        SailTicket.objects.create(code='UNIQUE-001', color=SailTicket.Color.SPARE)
        with self.assertRaises(IntegrityError):
            SailTicket.objects.create(code='UNIQUE-001', color=SailTicket.Color.SPARE)


class SailTicketLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.ticket = SailTicket.objects.create(code='SAIL-001', color=SailTicket.Color.SAIL)

    def test_can_create_log_entry(self):
        log = SailTicketLog.objects.create(
            ticket=self.ticket,
            status=SailTicket.Status.ON_WATER,
            changed_by=self.user,
        )
        self.assertEqual(log.status, SailTicket.Status.ON_WATER)

    def test_note_defaults_to_empty(self):
        log = SailTicketLog.objects.create(
            ticket=self.ticket,
            status=SailTicket.Status.ASHORE,
            changed_by=None,
        )
        self.assertEqual(log.note, '')

    def test_ticket_has_logs_reverse_relation(self):
        SailTicketLog.objects.create(
            ticket=self.ticket,
            status=SailTicket.Status.ON_WATER,
            changed_by=self.user,
        )
        self.assertEqual(self.ticket.logs.count(), 1)
