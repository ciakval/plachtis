from datetime import date

from django.test import TestCase
from django.contrib.auth.models import User

from SkaRe.models import BoatClass, Boat, Entity, Unit, RegularParticipant, Crew, Person


def _make_user(username):
    return User.objects.create_user(username=username, password='pw')


def _make_entity(user):
    return Entity.objects.create(
        created_by=user, contact_email='a@a.com', contact_phone='123456789'
    )


def _make_unit(user):
    return Unit.objects.create(entity=_make_entity(user), contact_person_name='Test')


def _make_person(unit, first='Jan', last='Novák'):
    return RegularParticipant.objects.create(
        first_name=first, last_name=last, date_of_birth=date(2000, 1, 1), unit=unit
    )


def _make_boat(user):
    bc = BoatClass.objects.get_or_create(name='P550', category=BoatClass.Category.SAIL, order=1)[0]
    return Boat.objects.create(
        created_by=user, boat_class=bc, name='ALBATROS',
        contact_person='J', contact_phone='123456789'
    )


class CrewRegistrationFormTest(TestCase):
    def setUp(self):
        from SkaRe.forms import CrewRegistrationForm
        self.Form = CrewRegistrationForm
        self.user = _make_user('formowner')
        self.unit = _make_unit(self.user)
        self.helmsman = _make_person(self.unit, 'Helm', 'Man')
        self.crew1 = _make_person(self.unit, 'Crew', 'One')
        self.boat = _make_boat(self.user)

    def _valid_data(self, **overrides):
        data = {
            'boat': self.boat.pk,
            'category': Crew.CATEGORY_S,
            'helmsman': self.helmsman.pk,
        }
        data.update(overrides)
        return data

    def test_valid_form_with_helmsman_only(self):
        form = self.Form(user=self.user, data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_form_with_one_crew_member(self):
        form = self.Form(user=self.user, data=self._valid_data(crew_member_1=self.crew1.pk))
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_when_helmsman_missing(self):
        data = self._valid_data()
        del data['helmsman']
        form = self.Form(user=self.user, data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_when_helmsman_same_as_crew_member(self):
        form = self.Form(
            user=self.user,
            data=self._valid_data(crew_member_1=self.helmsman.pk),
        )
        self.assertFalse(form.is_valid())

    def test_only_visible_boats_in_queryset(self):
        other_user = _make_user('boatstranger')
        other_boat = _make_boat(other_user)
        form = self.Form(user=self.user, data=self._valid_data())
        boat_pks = list(form.fields['boat'].queryset.values_list('pk', flat=True))
        self.assertIn(self.boat.pk, boat_pks)
        self.assertNotIn(other_boat.pk, boat_pks)

    def test_only_visible_persons_in_helmsman_queryset(self):
        other_user = _make_user('personstranger')
        other_unit = _make_unit(other_user)
        other_person = _make_person(other_unit, 'Other', 'Person')
        form = self.Form(user=self.user, data=self._valid_data())
        person_pks = list(form.fields['helmsman'].queryset.values_list('pk', flat=True))
        self.assertIn(self.helmsman.pk, person_pks)
        self.assertNotIn(other_person.pk, person_pks)

    def test_borrowed_person_in_queryset(self):
        other_user = _make_user('lender')
        other_unit = _make_unit(other_user)
        lent_person = _make_person(other_unit, 'Lent', 'Person')
        Person.objects.get(pk=lent_person.pk).visible_to.add(self.user)
        form = self.Form(user=self.user, data=self._valid_data())
        person_pks = list(form.fields['helmsman'].queryset.values_list('pk', flat=True))
        self.assertIn(lent_person.pk, person_pks)
