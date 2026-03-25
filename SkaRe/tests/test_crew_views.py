from datetime import date

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from SkaRe.models import BoatClass, Boat, Entity, Unit, Person, RegularParticipant


def _make_user(username):
    return User.objects.create_user(username=username, password='pw')


def _make_entity(user):
    return Entity.objects.create(
        created_by=user, contact_email='a@a.com', contact_phone='123456789'
    )


def _make_unit(user):
    return Unit.objects.create(entity=_make_entity(user), contact_person_name='Test')


def _make_boat(user, **kw):
    bc = BoatClass.objects.get_or_create(name='P550', category=BoatClass.Category.SAIL, order=1)[0]
    return Boat.objects.create(
        created_by=user, boat_class=bc, name='ALBATROS',
        contact_person='J', contact_phone='123456789', **kw
    )


def _make_person(unit, first='Jan', last='Novák'):
    return RegularParticipant.objects.create(
        first_name=first, last_name=last,
        date_of_birth=date(2000, 1, 1),
        unit=unit,
    )


class BoatLendViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = _make_user('owner')
        self.stranger = _make_user('stranger')
        self.borrower = _make_user('borrower')
        self.boat = _make_boat(self.owner)

    def test_lend_page_requires_login(self):
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response['Location'])

    def test_lend_page_accessible_by_owner(self):
        self.client.login(username='owner', password='pw')
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_lend_page_forbidden_for_stranger(self):
        self.client.login(username='stranger', password='pw')
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_lend_page_accessible_by_infodesk(self):
        infodesk = _make_user('infodesk_user')
        group, _ = Group.objects.get_or_create(name='InfoDesk')
        infodesk.groups.add(group)
        self.client.login(username='infodesk_user', password='pw')
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_add_user_to_visible_to(self):
        self.client.login(username='owner', password='pw')
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        response = self.client.post(url, {'action': 'add', 'username': 'borrower'})
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.borrower, self.boat.visible_to.all())

    def test_remove_user_from_visible_to(self):
        self.boat.visible_to.add(self.borrower)
        self.client.login(username='owner', password='pw')
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        self.client.post(url, {'action': 'remove', 'user_id': self.borrower.pk})
        self.assertNotIn(self.borrower, self.boat.visible_to.all())


class PersonLendViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = _make_user('person_owner')
        self.stranger = _make_user('person_stranger')
        self.borrower = _make_user('person_borrower')
        self.unit = _make_unit(self.owner)
        self.person = _make_person(self.unit)

    def test_lend_page_requires_login(self):
        url = reverse('SkaRe:person_lend', kwargs={'person_id': self.person.pk})
        response = self.client.get(url)
        self.assertRedirects(response, f'/user/login/?next={url}', fetch_redirect_response=False)

    def test_lend_page_accessible_by_unit_owner(self):
        self.client.login(username='person_owner', password='pw')
        url = reverse('SkaRe:person_lend', kwargs={'person_id': self.person.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_lend_page_forbidden_for_stranger(self):
        self.client.login(username='person_stranger', password='pw')
        url = reverse('SkaRe:person_lend', kwargs={'person_id': self.person.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_add_user_to_visible_to(self):
        self.client.login(username='person_owner', password='pw')
        url = reverse('SkaRe:person_lend', kwargs={'person_id': self.person.pk})
        self.client.post(url, {'action': 'add', 'username': 'person_borrower'})
        person_base = Person.objects.get(pk=self.person.pk)
        self.assertIn(self.borrower, person_base.visible_to.all())

    def test_remove_user_from_visible_to(self):
        person_base = Person.objects.get(pk=self.person.pk)
        person_base.visible_to.add(self.borrower)
        self.client.login(username='person_owner', password='pw')
        url = reverse('SkaRe:person_lend', kwargs={'person_id': self.person.pk})
        self.client.post(url, {'action': 'remove', 'user_id': self.borrower.pk})
        person_base.refresh_from_db()
        self.assertNotIn(self.borrower, person_base.visible_to.all())
