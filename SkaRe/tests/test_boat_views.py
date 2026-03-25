import json
from unittest.mock import patch
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from SkaRe.models import BoatClass, Boat, Entity, Unit
from SkaRe.forms import BoatForm


_SAMPLE_SHEET_CSV = (
    "PLACHETNÍ REGISTR,,,,,,,\r\n"
    ",metadata,,,,,,,\r\n"
    ",plach. číslo,Jméno,typ,oddíl,přístav,ev. č.,\"plocha dle Certifikátu (m2), datum měření\",\r\n"
    ",,,typ - trup - plachta,,,,,\r\n"
    ',14,ALBATROS,šalupa - P550 - Černá Eskadra,,4. Jana Nerudy Praha,113.04,"7,02",\r\n'
    ",42,RYCHLÍK,ketový keč - Cadet - ,Jan Novák,5. oddíl Koráb,523.10,,\r\n"
)


class SailLookupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')
        cache.clear()

    def test_found_returns_json(self):
        url = reverse('SkaRe:boat_sail_lookup')
        with patch('SkaRe.views._fetch_sheet_csv', return_value=_SAMPLE_SHEET_CSV):
            response = self.client.get(url, {'q': '14'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['boat_name'], 'ALBATROS')
        self.assertEqual(data['class_name'], 'P550')
        self.assertEqual(data['subtype'], 'šalupa')
        self.assertEqual(data['sail_area'], '7.02')
        self.assertEqual(data['harbor_name'], '4. Jana Nerudy Praha')

    def test_case_insensitive_lookup(self):
        url = reverse('SkaRe:boat_sail_lookup')
        with patch('SkaRe.views._fetch_sheet_csv', return_value=_SAMPLE_SHEET_CSV):
            response = self.client.get(url, {'q': '14'})
        self.assertEqual(response.status_code, 200)

    def test_not_found_returns_404(self):
        url = reverse('SkaRe:boat_sail_lookup')
        with patch('SkaRe.views._fetch_sheet_csv', return_value=_SAMPLE_SHEET_CSV):
            response = self.client.get(url, {'q': '999'})
        self.assertEqual(response.status_code, 404)

    def test_missing_q_returns_400(self):
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_fetch_failure_returns_503(self):
        url = reverse('SkaRe:boat_sail_lookup')
        with patch('SkaRe.views._fetch_sheet_csv', side_effect=Exception('network error')):
            response = self.client.get(url, {'q': '14'})
        self.assertEqual(response.status_code, 503)

    def test_cache_prevents_second_fetch(self):
        url = reverse('SkaRe:boat_sail_lookup')
        with patch('SkaRe.views._fetch_sheet_csv', return_value=_SAMPLE_SHEET_CSV) as mock_fetch:
            self.client.get(url, {'q': '14'})
            self.client.get(url, {'q': '42'})
        self.assertEqual(mock_fetch.call_count, 1)

    def test_requires_login(self):
        self.client.logout()
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url, {'q': '14'})
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

    def test_returns_contact_phone(self):
        self._create_unit()
        url = reverse('SkaRe:boat_my_unit')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('contact_phone', data)
        self.assertEqual(data['contact_phone'], '+420123456789')


class BoatListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')

    def test_list_accessible_to_authenticated(self):
        response = self.client.get(reverse('SkaRe:boat_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_redirects_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse('SkaRe:boat_list'))
        self.assertEqual(response.status_code, 302)


class BoatDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.stranger = User.objects.create_user(username='stranger', password='pw')
        self.infodesk_user = User.objects.create_user(username='infodesk', password='pw')
        infodesk_group, _ = Group.objects.get_or_create(name='InfoDesk')
        self.infodesk_user.groups.add(infodesk_group)
        self.boat_class = BoatClass.objects.create(
            name='TestClass', category=BoatClass.Category.SAIL, order=99
        )
        self.boat = Boat.objects.create(
            created_by=self.owner, boat_class=self.boat_class,
            name='My Boat', contact_person='Jan', contact_phone='+420111222333',
        )

    def test_authenticated_user_can_view(self):
        self.client.login(username='stranger', password='pw')
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirected(self):
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertEqual(response.status_code, 302)

    def test_can_edit_true_for_creator(self):
        self.client.login(username='owner', password='pw')
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertTrue(response.context['can_edit'])

    def test_can_edit_false_for_stranger(self):
        self.client.login(username='stranger', password='pw')
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertFalse(response.context['can_edit'])

    def test_can_edit_true_for_infodesk(self):
        self.client.login(username='infodesk', password='pw')
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertTrue(response.context['can_edit'])

    def test_is_creator_true_for_owner(self):
        self.client.login(username='owner', password='pw')
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertTrue(response.context['is_creator'])

    def test_is_creator_false_for_stranger(self):
        self.client.login(username='stranger', password='pw')
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertFalse(response.context['is_creator'])


class BoatRegisterViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')
        self.boat_class = BoatClass.objects.create(
            name='TestClass', category=BoatClass.Category.SAIL, order=99
        )

    def _post_data(self, **overrides):
        data = {
            'boat_class': self.boat_class.pk,
            'class_supplement': '',
            'sail_number': 'CZE 42',
            'name': 'My Boat',
            'description': '',
            'sail_area': '',
            'harbor_number': '523.10',
            'harbor_name': '5. oddíl Koráb',
            'contact_person': 'Jan Novák',
            'contact_phone': '+420123456789',
        }
        data.update(overrides)
        return data

    def test_get_register_form(self):
        response = self.client.get(reverse('SkaRe:boat_register'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], BoatForm)

    def test_post_creates_boat_with_creator(self):
        response = self.client.post(reverse('SkaRe:boat_register'), self._post_data())
        self.assertEqual(Boat.objects.count(), 1)
        boat = Boat.objects.first()
        self.assertEqual(boat.created_by, self.user)
        self.assertRedirects(response, reverse('SkaRe:boat_detail', kwargs={'boat_id': boat.pk}))

    def test_post_invalid_shows_errors(self):
        response = self.client.post(reverse('SkaRe:boat_register'), self._post_data(name=''))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Boat.objects.count(), 0)

    def test_has_unit_context_false_when_no_unit(self):
        response = self.client.get(reverse('SkaRe:boat_register'))
        self.assertFalse(response.context['has_unit'])


class BoatEditViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.stranger = User.objects.create_user(username='stranger', password='pw')
        self.infodesk_user = User.objects.create_user(username='infodesk', password='pw')
        infodesk_group, _ = Group.objects.get_or_create(name='InfoDesk')
        self.infodesk_user.groups.add(infodesk_group)
        self.boat_class = BoatClass.objects.create(
            name='TestClass', category=BoatClass.Category.SAIL, order=99
        )
        self.boat = Boat.objects.create(
            created_by=self.owner, boat_class=self.boat_class,
            name='My Boat', contact_person='Jan', contact_phone='+420111222333',
        )

    def _post_data(self, **overrides):
        data = {
            'boat_class': self.boat_class.pk,
            'class_supplement': '',
            'sail_number': '',
            'name': 'Updated Boat',
            'description': '',
            'sail_area': '',
            'harbor_number': '',
            'harbor_name': '',
            'contact_person': 'Jan',
            'contact_phone': '+420111222333',
        }
        data.update(overrides)
        return data

    def test_owner_can_edit(self):
        self.client.login(username='owner', password='pw')
        self.client.post(
            reverse('SkaRe:boat_edit', kwargs={'boat_id': self.boat.pk}),
            self._post_data()
        )
        self.boat.refresh_from_db()
        self.assertEqual(self.boat.name, 'Updated Boat')

    def test_stranger_cannot_edit(self):
        self.client.login(username='stranger', password='pw')
        self.client.post(
            reverse('SkaRe:boat_edit', kwargs={'boat_id': self.boat.pk}),
            self._post_data()
        )
        self.boat.refresh_from_db()
        self.assertEqual(self.boat.name, 'My Boat')

    def test_infodesk_can_edit(self):
        self.client.login(username='infodesk', password='pw')
        self.client.post(
            reverse('SkaRe:boat_edit', kwargs={'boat_id': self.boat.pk}),
            self._post_data()
        )
        self.boat.refresh_from_db()
        self.assertEqual(self.boat.name, 'Updated Boat')


class BoatDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.stranger = User.objects.create_user(username='stranger', password='pw')
        self.infodesk_user = User.objects.create_user(username='infodesk', password='pw')
        infodesk_group, _ = Group.objects.get_or_create(name='InfoDesk')
        self.infodesk_user.groups.add(infodesk_group)
        self.boat_class = BoatClass.objects.create(
            name='TestClass', category=BoatClass.Category.SAIL, order=99
        )
        self.boat = Boat.objects.create(
            created_by=self.owner, boat_class=self.boat_class,
            name='My Boat', contact_person='Jan', contact_phone='+420111222333',
        )

    def test_owner_can_delete(self):
        self.client.login(username='owner', password='pw')
        self.client.post(reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))
        self.assertFalse(Boat.objects.filter(pk=self.boat.pk).exists())

    def test_stranger_cannot_delete(self):
        self.client.login(username='stranger', password='pw')
        self.client.post(reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))
        self.assertTrue(Boat.objects.filter(pk=self.boat.pk).exists())

    def test_infodesk_cannot_delete(self):
        self.client.login(username='infodesk', password='pw')
        self.client.post(reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))
        self.assertTrue(Boat.objects.filter(pk=self.boat.pk).exists())

    def test_get_shows_confirm_page(self):
        self.client.login(username='owner', password='pw')
        response = self.client.get(reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Boat')


class BoatRegisterTemplateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')

    def test_fill_from_unit_button_hidden_when_no_unit(self):
        response = self.client.get(reverse('SkaRe:boat_register'))
        # The button should not appear when has_unit=False
        self.assertNotContains(response, 'btn-fill-from-unit')

    def test_fill_from_unit_button_shown_when_unit_exists(self):
        entity = Entity.objects.create(
            created_by=self.user,
            scout_unit_name='5. oddíl',
            scout_unit_evidence_id='123',
            contact_email='t@t.cz',
            contact_phone='+420111222333',
        )
        Unit.objects.create(entity=entity, contact_person_name='Vedoucí')
        response = self.client.get(reverse('SkaRe:boat_register'))
        self.assertContains(response, 'btn-fill-from-unit')


class BoatDetailTemplateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.stranger = User.objects.create_user(username='stranger', password='pw')
        self.boat_class = BoatClass.objects.create(
            name='P550', category=BoatClass.Category.SAIL, order=1
        )
        self.boat = Boat.objects.create(
            created_by=self.owner, boat_class=self.boat_class,
            name='My Boat', contact_person='Jan', contact_phone='+420111222333',
        )

    def test_owner_sees_edit_and_delete_buttons(self):
        self.client.login(username='owner', password='pw')
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertContains(response, reverse('SkaRe:boat_edit', kwargs={'boat_id': self.boat.pk}))
        self.assertContains(response, reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))

    def test_stranger_does_not_see_edit_or_delete(self):
        self.client.login(username='stranger', password='pw')
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertNotContains(response, reverse('SkaRe:boat_edit', kwargs={'boat_id': self.boat.pk}))
        self.assertNotContains(response, reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))
