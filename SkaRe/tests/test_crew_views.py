from datetime import date

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from SkaRe.models import BoatClass, Boat, Entity, Unit, Person, RegularParticipant, Crew, CrewMember


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


class CrewRegisterViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = _make_user('crewreg')
        self.unit = _make_unit(self.user)
        self.helmsman = _make_person(self.unit)
        self.boat = _make_boat(self.user)

    def test_register_requires_login(self):
        url = reverse('SkaRe:crew_register')
        self.assertRedirects(
            self.client.get(url),
            f'/user/login/?next={url}',
            fetch_redirect_response=False,
        )

    def test_register_get_renders_form(self):
        self.client.login(username='crewreg', password='pw')
        response = self.client.get(reverse('SkaRe:crew_register'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_register_creates_crew_and_members(self):
        self.client.login(username='crewreg', password='pw')
        response = self.client.post(reverse('SkaRe:crew_register'), {
            'boat': self.boat.pk,
            'category': Crew.CATEGORY_S,
            'helmsman': self.helmsman.pk,
        })
        self.assertEqual(Crew.objects.count(), 1)
        crew = Crew.objects.first()
        self.assertEqual(crew.members.count(), 1)
        self.assertEqual(crew.members.first().role, CrewMember.ROLE_HELMSMAN)
        self.assertRedirects(
            response,
            reverse('SkaRe:crew_detail', kwargs={'crew_id': crew.pk}),
            fetch_redirect_response=False,
        )

    def test_duplicate_boat_category_shows_error(self):
        self.client.login(username='crewreg', password='pw')
        Crew.objects.create(boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user)
        response = self.client.post(reverse('SkaRe:crew_register'), {
            'boat': self.boat.pk,
            'category': Crew.CATEGORY_S,
            'helmsman': self.helmsman.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Crew.objects.count(), 1)  # no new crew created


class CrewListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = _make_user('crewlist')

    def test_list_requires_login(self):
        url = reverse('SkaRe:crew_list')
        self.assertRedirects(
            self.client.get(url),
            f'/user/login/?next={url}',
            fetch_redirect_response=False,
        )

    def test_list_shows_only_user_crews(self):
        unit = _make_unit(self.user)
        helmsman = _make_person(unit)
        boat = _make_boat(self.user)
        other_user = _make_user('crewother')
        Crew.objects.create(boat=boat, category=Crew.CATEGORY_S, created_by=self.user)
        other_boat = _make_boat(other_user)
        Crew.objects.create(boat=other_boat, category=Crew.CATEGORY_S, created_by=other_user)
        self.client.login(username='crewlist', password='pw')
        response = self.client.get(reverse('SkaRe:crew_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['crews']), 1)


class CrewEditDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = _make_user('editowner')
        self.stranger = _make_user('editstranger')
        self.unit = _make_unit(self.user)
        self.helmsman = _make_person(self.unit)
        self.new_helm = _make_person(self.unit, 'New', 'Helm')
        self.boat = _make_boat(self.user)
        self.crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        CrewMember.objects.create(
            crew=self.crew, role=CrewMember.ROLE_HELMSMAN,
            participant=Person.objects.get(pk=self.helmsman.pk)
        )

    def test_edit_requires_login(self):
        url = reverse('SkaRe:crew_edit', kwargs={'crew_id': self.crew.pk})
        self.assertRedirects(self.client.get(url), f'/user/login/?next={url}', fetch_redirect_response=False)

    def test_edit_forbidden_for_stranger(self):
        self.client.login(username='editstranger', password='pw')
        response = self.client.get(reverse('SkaRe:crew_edit', kwargs={'crew_id': self.crew.pk}))
        self.assertEqual(response.status_code, 302)

    def test_edit_get_renders_form(self):
        self.client.login(username='editowner', password='pw')
        response = self.client.get(reverse('SkaRe:crew_edit', kwargs={'crew_id': self.crew.pk}))
        self.assertEqual(response.status_code, 200)

    def test_edit_post_updates_crew(self):
        self.client.login(username='editowner', password='pw')
        response = self.client.post(
            reverse('SkaRe:crew_edit', kwargs={'crew_id': self.crew.pk}),
            {
                'boat': self.boat.pk,
                'category': Crew.CATEGORY_R,
                'helmsman': self.new_helm.pk,
            }
        )
        self.crew.refresh_from_db()
        self.assertEqual(self.crew.category, Crew.CATEGORY_R)
        self.assertRedirects(
            response,
            reverse('SkaRe:crew_detail', kwargs={'crew_id': self.crew.pk}),
            fetch_redirect_response=False,
        )

    def test_delete_requires_login(self):
        url = reverse('SkaRe:crew_delete', kwargs={'crew_id': self.crew.pk})
        self.assertRedirects(self.client.get(url), f'/user/login/?next={url}', fetch_redirect_response=False)

    def test_delete_removes_crew(self):
        self.client.login(username='editowner', password='pw')
        self.client.post(reverse('SkaRe:crew_delete', kwargs={'crew_id': self.crew.pk}))
        self.assertFalse(Crew.objects.filter(pk=self.crew.pk).exists())

    def test_delete_forbidden_for_stranger(self):
        self.client.login(username='editstranger', password='pw')
        self.client.post(reverse('SkaRe:crew_delete', kwargs={'crew_id': self.crew.pk}))
        self.assertTrue(Crew.objects.filter(pk=self.crew.pk).exists())


class CrewExportCsvTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(username='csvstaff', password='pw', is_staff=True)
        self.regular = _make_user('csvregular')
        self.user = _make_user('csvowner')
        self.unit = _make_unit(self.user)
        self.helmsman = _make_person(self.unit)
        self.boat = _make_boat(self.user)
        self.crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        CrewMember.objects.create(
            crew=self.crew, role=CrewMember.ROLE_HELMSMAN,
            participant=Person.objects.get(pk=self.helmsman.pk),
        )

    def test_export_requires_staff(self):
        self.client.login(username='csvregular', password='pw')
        response = self.client.get(reverse('SkaRe:crew_export_csv'))
        self.assertEqual(response.status_code, 302)

    def test_export_returns_csv_for_staff(self):
        self.client.login(username='csvstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_export_contains_helmsman_row(self):
        self.client.login(username='csvstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_export_csv'))
        content = response.content.decode('utf-8-sig')
        self.assertIn('Jan', content)
        self.assertIn(Crew.CATEGORY_S, content)


class CrewAllViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user('allstaff', password='pw', is_staff=True)
        self.regular = _make_user('allregular')
        self.user = _make_user('allowner')
        self.unit = _make_unit(self.user)
        self.helmsman = _make_person(self.unit)
        self.boat = _make_boat(self.user)
        self.crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        CrewMember.objects.create(
            crew=self.crew, role=CrewMember.ROLE_HELMSMAN,
            participant=Person.objects.get(pk=self.helmsman.pk),
        )

    # --- crew_all ---

    def test_crew_all_requires_login(self):
        url = reverse('SkaRe:crew_all')
        response = self.client.get(url)
        self.assertRedirects(response, f'/user/login/?next={url}', fetch_redirect_response=False)

    def test_crew_all_requires_staff(self):
        self.client.login(username='allregular', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all'))
        self.assertEqual(response.status_code, 302)

    def test_crew_all_accessible_by_staff(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all'))
        self.assertEqual(response.status_code, 200)

    # --- crew_all_export_csv ---

    def test_crew_all_export_requires_staff(self):
        self.client.login(username='allregular', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all_export_csv'))
        self.assertEqual(response.status_code, 302)

    def test_crew_all_export_accessible_by_staff(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_all_export_csv'))
        self.assertEqual(response.status_code, 200)

    # --- crew_detail_staff ---

    def test_crew_detail_staff_requires_login(self):
        url = reverse('SkaRe:crew_detail_staff', kwargs={'crew_id': self.crew.pk})
        response = self.client.get(url)
        self.assertRedirects(response, f'/user/login/?next={url}', fetch_redirect_response=False)

    def test_crew_detail_staff_requires_staff(self):
        self.client.login(username='allregular', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_detail_staff', kwargs={'crew_id': self.crew.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_crew_detail_staff_accessible_by_staff(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_detail_staff', kwargs={'crew_id': self.crew.pk})
        )
        self.assertEqual(response.status_code, 200)

    # --- crew_export_single_csv ---

    def test_crew_export_single_requires_staff(self):
        self.client.login(username='allregular', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_export_single_csv', kwargs={'crew_id': self.crew.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_crew_export_single_accessible_by_staff(self):
        self.client.login(username='allstaff', password='pw')
        response = self.client.get(
            reverse('SkaRe:crew_export_single_csv', kwargs={'crew_id': self.crew.pk})
        )
        self.assertEqual(response.status_code, 200)
