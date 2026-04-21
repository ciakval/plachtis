from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group


def _make_infodesk_user():
    user = User.objects.create_user(username='desk', password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


def _make_regular_user():
    return User.objects.create_user(username='reg', password='pw')


INFODESK_URLS = [
    ('infodesk_dashboard', {}),
    ('infodesk_registrations', {}),
    ('attendance_units_list', {}),
    ('attendance_individuals_list', {}),
    ('attendance_organizers_list', {}),
    ('ticket_list', {}),
    ('ticket_lookup', {}),
    ('ticket_on_water', {}),
    ('exports_index', {}),
]


class InfodeskAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.infodesk = _make_infodesk_user()
        self.regular = _make_regular_user()

    def test_anonymous_redirected_to_login(self):
        for name, kwargs in INFODESK_URLS:
            with self.subTest(url=name):
                url = reverse(f'SkaRe:{name}', kwargs=kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302, msg=name)
                self.assertIn('login', response['Location'], msg=name)

    def test_regular_user_gets_403(self):
        self.client.login(username='reg', password='pw')
        for name, kwargs in INFODESK_URLS:
            with self.subTest(url=name):
                url = reverse(f'SkaRe:{name}', kwargs=kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403, msg=name)

    def test_infodesk_user_gets_200(self):
        self.client.login(username='desk', password='pw')
        for name, kwargs in INFODESK_URLS:
            with self.subTest(url=name):
                url = reverse(f'SkaRe:{name}', kwargs=kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, msg=name)


from datetime import date
from SkaRe.models import Entity, Unit, IndividualParticipant, RegularParticipant


def _make_unit_entity(user, confirmed=False, name='Test Unit'):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='t@example.com',
        contact_phone='123456789',
        scout_unit_name=name,
        confirmed=confirmed,
    )
    Unit.objects.create(entity=entity, contact_person_name='Leader')
    return entity


class RegistrationQueueTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.infodesk = _make_infodesk_user()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_queue_shows_all_entities(self):
        _make_unit_entity(self.owner, confirmed=False, name='Alpha')
        _make_unit_entity(self.owner, confirmed=True, name='Beta')
        url = reverse('SkaRe:infodesk_registrations')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alpha')
        self.assertContains(response, 'Beta')

    def test_confirm_entity_sets_confirmed_true(self):
        entity = _make_unit_entity(self.owner, confirmed=False)
        url = reverse('SkaRe:infodesk_confirm_entity', kwargs={'entity_id': entity.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))
        entity.refresh_from_db()
        self.assertTrue(entity.confirmed)

    def test_reject_entity_sets_confirmed_false(self):
        entity = _make_unit_entity(self.owner, confirmed=True)
        url = reverse('SkaRe:infodesk_reject_entity', kwargs={'entity_id': entity.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))
        entity.refresh_from_db()
        self.assertFalse(entity.confirmed)

    def test_bulk_confirm_sets_multiple_confirmed(self):
        e1 = _make_unit_entity(self.owner, confirmed=False, name='A')
        e2 = _make_unit_entity(self.owner, confirmed=False, name='B')
        url = reverse('SkaRe:infodesk_bulk_confirm')
        response = self.client.post(url, {'entity_ids': [e1.pk, e2.pk]})
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))
        e1.refresh_from_db()
        e2.refresh_from_db()
        self.assertTrue(e1.confirmed)
        self.assertTrue(e2.confirmed)

    def test_confirm_get_redirects_to_registrations(self):
        entity = _make_unit_entity(self.owner)
        url = reverse('SkaRe:infodesk_confirm_entity', kwargs={'entity_id': entity.pk})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))


from SkaRe.models import Organizer  # Entity, Unit, IndividualParticipant already imported at top of file


def _make_infodesk_group_user(username='desk2'):
    user = User.objects.create_user(username=username, password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


class InfodeskEditUnitTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.infodesk = _make_infodesk_group_user()
        self.owner = User.objects.create_user(username='unitowner', password='pw')
        self.client.login(username='desk2', password='pw')

        entity = Entity.objects.create(
            created_by=self.owner,
            contact_email='u@example.com',
            contact_phone='+420123456789',
            scout_unit_name='Old Name',
        )
        self.unit = Unit.objects.create(entity=entity, contact_person_name='Leader')

    def _post_data(self, unit_name='New Name'):
        return {
            'scout_unit_name': unit_name,
            'scout_unit_evidence_id': '',
            'contact_email': 'u@example.com',
            'contact_phone': '+420123456789',
            'contact_person_name': 'Leader',
            'backup_contact_phone': '',
            'boats_p550': '0', 'boats_sail': '0',
            'boats_paddle': '0', 'boats_motor': '0',
            'scarf_count': '0', 'hat_count': '0', 'small_hat_count': '0',
            'accommodation_expectations': '',
            'estimated_accommodation_area': '',
            'participants-TOTAL_FORMS': '0',
            'participants-INITIAL_FORMS': '0',
            'participants-MIN_NUM_FORMS': '0',
            'participants-MAX_NUM_FORMS': '1000',
        }

    def test_infodesk_can_get_edit_unit(self):
        url = reverse('SkaRe:edit_unit', kwargs={'unit_id': self.unit.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_infodesk_edit_unit_redirects_to_infodesk_registrations(self):
        url = reverse('SkaRe:edit_unit', kwargs={'unit_id': self.unit.pk})
        response = self.client.post(url, self._post_data('Updated Name'))
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))

    def test_infodesk_edit_unit_saves_changes(self):
        url = reverse('SkaRe:edit_unit', kwargs={'unit_id': self.unit.pk})
        self.client.post(url, self._post_data('Updated Name'))
        self.unit.entity.refresh_from_db()
        self.assertEqual(self.unit.entity.scout_unit_name, 'Updated Name')


class InfodeskEditIndividualParticipantTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.infodesk = _make_infodesk_group_user(username='desk3')
        self.owner = User.objects.create_user(username='indowner', password='pw')
        self.client.login(username='desk3', password='pw')

        entity = Entity.objects.create(
            created_by=self.owner,
            contact_email='i@example.com',
            contact_phone='+420123456789',
        )
        self.participant = IndividualParticipant.objects.create(
            entity=entity,
            first_name='Old',
            last_name='Name',
            date_of_birth=date(1990, 1, 1),
        )

    def _post_data(self, first_name='New'):
        return {
            'contact_email': 'i@example.com',
            'contact_phone': '+420123456789',
            'first_name': first_name,
            'last_name': 'Name',
            'nickname': '',
            'date_of_birth': '1990-01-01',
            'health_restrictions': '',
            'diet_vegetarian': '',
            'diet_vegan': '',
            'diet_no_soy': '',
            'diet_lactose_free': '',
            'diet_gluten_free': '',
            'diet_no_peanuts': '',
            'diet_no_eggs': '',
            'diet_no_fish': '',
            'diet_other': '',
            'relevant_information': '',
            'boats_p550': '0', 'boats_sail': '0',
            'boats_paddle': '0', 'boats_motor': '0',
            'scarf_count': '0', 'hat_count': '0', 'small_hat_count': '0',
            'accommodation_expectations': '',
            'estimated_accommodation_area': '',
        }

    def test_infodesk_can_get_edit_individual_participant(self):
        url = reverse('SkaRe:edit_individual_participant', kwargs={'participant_id': self.participant.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_infodesk_edit_individual_participant_redirects_to_infodesk_registrations(self):
        url = reverse('SkaRe:edit_individual_participant', kwargs={'participant_id': self.participant.pk})
        response = self.client.post(url, self._post_data('Updated'))
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))

    def test_infodesk_edit_individual_participant_saves_changes(self):
        url = reverse('SkaRe:edit_individual_participant', kwargs={'participant_id': self.participant.pk})
        self.client.post(url, self._post_data('Updated'))
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.first_name, 'Updated')
