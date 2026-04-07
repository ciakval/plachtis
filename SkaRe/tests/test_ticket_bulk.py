from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from SkaRe.models import SailTicket, SailTicketLog, Boat, BoatClass
from SkaRe.views.tickets import _extract_numeric, _build_ticket_plan


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_infodesk():
    user = User.objects.create_user(username='desk', password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


def _p550_class():
    bc, _ = BoatClass.objects.get_or_create(
        name='P550', defaults={'category': BoatClass.Category.SAIL, 'order': 1}
    )
    return bc


def _sail_class():
    bc, _ = BoatClass.objects.get_or_create(
        name='Laser', defaults={'category': BoatClass.Category.SAIL, 'order': 2}
    )
    return bc


def _other_class():
    bc, _ = BoatClass.objects.get_or_create(
        name='Motorboat', defaults={'category': BoatClass.Category.OTHER, 'order': 3}
    )
    return bc


def _make_boat(user, sail_number='', boat_class=None, name='Test Boat'):
    return Boat.objects.create(
        created_by=user,
        boat_class=boat_class or _p550_class(),
        sail_number=sail_number,
        name=name,
        contact_person='Leader',
        contact_phone='123456789',
    )


_NO_RESERVES = {
    SailTicket.Color.P550: 0,
    SailTicket.Color.SAIL: 0,
    SailTicket.Color.OTHER: 0,
}


# ── _extract_numeric ──────────────────────────────────────────────────────────

class ExtractNumericTest(TestCase):
    def test_digits_only(self):
        self.assertEqual(_extract_numeric('1234'), 1234)

    def test_country_code_prefix(self):
        self.assertEqual(_extract_numeric('CZE 1234'), 1234)

    def test_country_code_no_space(self):
        self.assertEqual(_extract_numeric('CZE1234'), 1234)

    def test_empty_string(self):
        self.assertIsNone(_extract_numeric(''))

    def test_no_digits(self):
        self.assertIsNone(_extract_numeric('CZE'))

    def test_zero_treated_as_none(self):
        self.assertIsNone(_extract_numeric('0'))

    def test_leading_zeros_still_zero(self):
        self.assertIsNone(_extract_numeric('00'))


# ── _build_ticket_plan ────────────────────────────────────────────────────────

class BuildTicketPlanTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('owner', password='pw')

    def test_boat_with_sail_number_gets_numeric_code(self):
        _make_boat(self.user, sail_number='CZE 1234')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        codes = [t.code for t in plan]
        self.assertIn('P550-1234', codes)

    def test_boat_without_sail_number_gets_sequential_code(self):
        _make_boat(self.user, sail_number='')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        codes = [t.code for t in plan]
        self.assertIn('P550-1', codes)

    def test_sail_numbered_boat_linked_to_ticket(self):
        boat = _make_boat(self.user, sail_number='CZE 5')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        ticket = next(t for t in plan if t.code == 'P550-5')
        self.assertEqual(ticket.boat, boat)

    def test_conflict_first_boat_keeps_number_second_gets_sequential(self):
        _make_boat(self.user, sail_number='CZE 1234', name='First')
        _make_boat(self.user, sail_number='1234', name='Second')
        boats = Boat.objects.select_related('boat_class').order_by('pk')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        codes = [t.code for t in plan]
        self.assertIn('P550-1234', codes)
        self.assertIn('P550-1', codes)   # second boat → sequential (1 is first unused)
        self.assertEqual(len([c for c in codes if c.startswith('P550-')]), 2)

    def test_reserves_fill_unused_numbers_skipping_sail_numbers(self):
        _make_boat(self.user, sail_number='CZE 3')   # claims 3
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, {
            SailTicket.Color.P550: 2,
            SailTicket.Color.SAIL: 0,
            SailTicket.Color.OTHER: 0,
        }, 0)
        codes = [t.code for t in plan]
        self.assertIn('P550-3', codes)   # from sail number
        self.assertIn('P550-1', codes)   # reserve
        self.assertIn('P550-2', codes)   # reserve
        self.assertNotIn('P550-4', codes)

    def test_reserve_tickets_have_no_boat(self):
        boats = Boat.objects.none()
        plan = _build_ticket_plan(boats, {
            SailTicket.Color.P550: 2,
            SailTicket.Color.SAIL: 0,
            SailTicket.Color.OTHER: 0,
        }, 0)
        for ticket in plan:
            self.assertIsNone(ticket.boat)

    def test_spare_tickets_sequential_from_1(self):
        boats = Boat.objects.none()
        plan = _build_ticket_plan(boats, _NO_RESERVES, 3)
        spare = [t for t in plan if t.color == SailTicket.Color.SPARE]
        self.assertEqual([t.code for t in spare], ['SPARE-1', 'SPARE-2', 'SPARE-3'])

    def test_spare_tickets_have_no_boat(self):
        boats = Boat.objects.none()
        plan = _build_ticket_plan(boats, _NO_RESERVES, 2)
        for ticket in plan:
            if ticket.color == SailTicket.Color.SPARE:
                self.assertIsNone(ticket.boat)

    def test_spare_independent_of_other_categories(self):
        _make_boat(self.user, sail_number='1')   # P550-1 claimed
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 2)
        spare = [t for t in plan if t.color == SailTicket.Color.SPARE]
        self.assertEqual([t.code for t in spare], ['SPARE-1', 'SPARE-2'])

    def test_from_sail_number_annotation_true_for_numbered_boat(self):
        _make_boat(self.user, sail_number='CZE 7')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        ticket = next(t for t in plan if t.code == 'P550-7')
        self.assertTrue(ticket._from_sail_number)

    def test_from_sail_number_annotation_false_for_unnumbered_boat(self):
        _make_boat(self.user, sail_number='')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        self.assertFalse(plan[0]._from_sail_number)

    def test_from_sail_number_annotation_false_for_reserve(self):
        boats = Boat.objects.none()
        plan = _build_ticket_plan(boats, {
            SailTicket.Color.P550: 1,
            SailTicket.Color.SAIL: 0,
            SailTicket.Color.OTHER: 0,
        }, 0)
        self.assertFalse(plan[0]._from_sail_number)

    def test_categories_are_independent(self):
        """P550 and SAIL sail numbers don't conflict with each other."""
        _make_boat(self.user, sail_number='5', boat_class=_p550_class(), name='P550 Boat')
        _make_boat(self.user, sail_number='5', boat_class=_sail_class(), name='SAIL Boat')
        boats = Boat.objects.select_related('boat_class')
        plan = _build_ticket_plan(boats, _NO_RESERVES, 0)
        codes = [t.code for t in plan]
        self.assertIn('P550-5', codes)
        self.assertIn('SAIL-5', codes)


class TicketCreateBulkViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user('owner', password='pw')

    def _post(self, extra=None):
        data = {
            'p550_reserves': 0,
            'sail_reserves': 0,
            'other_reserves': 0,
            'spare_count': 0,
        }
        if extra:
            data.update(extra)
        return self.client.post(reverse('SkaRe:ticket_create_bulk'), data)

    def test_get_renders_form_no_plan(self):
        response = self.client.get(reverse('SkaRe:ticket_create_bulk'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertNotIn('plan', response.context)

    def test_post_step1_renders_preview_without_db_changes(self):
        response = self._post({'p550_reserves': 2})
        self.assertEqual(response.status_code, 200)
        self.assertIn('plan', response.context)
        self.assertEqual(SailTicket.objects.count(), 0)

    def test_post_step1_plan_in_context_matches_reserves(self):
        response = self._post({'p550_reserves': 3})
        plan = response.context['plan']
        p550_tickets = [t for t in plan if t.color == SailTicket.Color.P550]
        self.assertEqual(len(p550_tickets), 3)

    def test_post_step2_deletes_existing_tickets(self):
        SailTicket.objects.create(code='OLD-001', color=SailTicket.Color.SPARE)
        self._post({'confirm': '1', 'spare_count': 1})
        self.assertFalse(SailTicket.objects.filter(code='OLD-001').exists())

    def test_post_step2_deletes_logs_via_cascade(self):
        ticket = SailTicket.objects.create(code='OLD-001', color=SailTicket.Color.SPARE)
        SailTicketLog.objects.create(ticket=ticket, status=SailTicket.Status.ASHORE)
        self._post({'confirm': '1'})
        self.assertEqual(SailTicketLog.objects.count(), 0)

    def test_post_step2_creates_correct_tickets(self):
        response = self._post({'confirm': '1', 'p550_reserves': 2, 'spare_count': 1})
        self.assertRedirects(response, reverse('SkaRe:ticket_list'))
        self.assertEqual(SailTicket.objects.count(), 3)
        codes = set(SailTicket.objects.values_list('code', flat=True))
        self.assertIn('P550-1', codes)
        self.assertIn('P550-2', codes)
        self.assertIn('SPARE-1', codes)

    def test_post_step2_zero_existing_tickets_works(self):
        self.assertEqual(SailTicket.objects.count(), 0)
        self._post({'confirm': '1', 'spare_count': 2})
        self.assertEqual(SailTicket.objects.count(), 2)

    def test_post_step2_assigns_sail_number_as_code(self):
        _make_boat(self.owner, sail_number='CZE 99', boat_class=_p550_class())
        self._post({'confirm': '1'})
        self.assertTrue(SailTicket.objects.filter(code='P550-99').exists())

    def test_post_step2_conflict_one_gets_number_other_gets_sequential(self):
        _make_boat(self.owner, sail_number='CZE 1234', name='First', boat_class=_p550_class())
        _make_boat(self.owner, sail_number='1234', name='Second', boat_class=_p550_class())
        self._post({'confirm': '1'})
        codes = set(SailTicket.objects.values_list('code', flat=True))
        self.assertIn('P550-1234', codes)
        self.assertIn('P550-1', codes)
        self.assertEqual(SailTicket.objects.count(), 2)

    def test_post_step2_redirects_to_ticket_list(self):
        response = self._post({'confirm': '1'})
        self.assertRedirects(response, reverse('SkaRe:ticket_list'))

    def test_get_requires_infodesk(self):
        self.client.logout()
        response = self.client.get(reverse('SkaRe:ticket_create_bulk'))
        self.assertNotEqual(response.status_code, 200)
