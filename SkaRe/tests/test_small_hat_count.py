"""
Tests for the hat size split: small_hat_count (S/M) added alongside hat_count (L/XL).
Covers form field presence, view persistence, and template rendering.
"""
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from SkaRe.forms import UnitRegistrationForm, IndividualParticipantRegistrationForm
from SkaRe.models import Entity, Unit, IndividualParticipant


# ---------------------------------------------------------------------------
# Form field presence
# ---------------------------------------------------------------------------

class UnitRegistrationFormSmallHatTest(TestCase):
    def test_small_hat_count_in_fields(self):
        form = UnitRegistrationForm()
        self.assertIn('small_hat_count', form.fields)

    def test_hat_count_in_fields(self):
        """hat_count (L/XL) must still be present."""
        form = UnitRegistrationForm()
        self.assertIn('hat_count', form.fields)

    def test_small_hat_count_accepts_value(self):
        """Form is valid when small_hat_count is provided."""
        data = {
            # Entity / scout unit fields
            'scout_unit_name': '5. oddíl Koráb',
            'scout_unit_evidence_id': '523.10',
            'contact_email': 'test@test.cz',
            'contact_phone': '+420123456789',
            # Unit fields
            'contact_person_name': 'Jan Novák',
            'backup_contact_phone': '',
            'boats_p550': 0,
            'boats_sail': 0,
            'boats_paddle': 0,
            'boats_motor': 0,
            'scarf_count': 0,
            'hat_count': 2,
            'small_hat_count': 3,
            'accommodation_expectations': '',
            'estimated_accommodation_area': '',
        }
        form = UnitRegistrationForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['small_hat_count'], 3)


class IndividualParticipantFormSmallHatTest(TestCase):
    def test_small_hat_count_in_fields(self):
        form = IndividualParticipantRegistrationForm()
        self.assertIn('small_hat_count', form.fields)

    def test_hat_count_in_fields(self):
        form = IndividualParticipantRegistrationForm()
        self.assertIn('hat_count', form.fields)


# ---------------------------------------------------------------------------
# edit_unit view: small_hat_count persists to the database
# ---------------------------------------------------------------------------

class EditUnitSmallHatCountTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='owner', password='pw')
        self.client.login(username='owner', password='pw')
        self.entity = Entity.objects.create(
            created_by=self.user,
            contact_email='owner@test.cz',
            contact_phone='+420123456789',
            scout_unit_name='5. oddíl Koráb',
            scout_unit_evidence_id='523.10',
            unlocked_for_editing=True,
        )
        self.unit = Unit.objects.create(
            entity=self.entity,
            contact_person_name='Jan Novák',
        )

    def _post_data(self, **overrides):
        data = {
            # UnitEditForm fields
            'contact_person_name': 'Jan Novák',
            'backup_contact_phone': '',
            'boats_p550': 0,
            'boats_sail': 0,
            'boats_paddle': 0,
            'boats_motor': 0,
            'scarf_count': 0,
            'hat_count': 0,
            'small_hat_count': 0,
            'accommodation_expectations': '',
            'estimated_accommodation_area': '',
            # EntityEditForm fields
            'scout_unit_name': '5. oddíl Koráb',
            'scout_unit_evidence_id': '523.10',
            'contact_email': 'owner@test.cz',
            'contact_phone': '+420123456789',
            'expected_arrival': '',
            'expected_departure': '',
            'home_town': '',
            # Participant formset management form (no participants)
            'participants-TOTAL_FORMS': '0',
            'participants-INITIAL_FORMS': '0',
            'participants-MIN_NUM_FORMS': '0',
            'participants-MAX_NUM_FORMS': '1000',
        }
        data.update(overrides)
        return data

    def test_small_hat_count_saved_on_edit(self):
        url = reverse('SkaRe:edit_unit', kwargs={'unit_id': self.unit.pk})
        response = self.client.post(url, self._post_data(small_hat_count=5))
        self.assertRedirects(response, reverse('SkaRe:list_units'))
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.small_hat_count, 5)

    def test_hat_count_still_saved_on_edit(self):
        url = reverse('SkaRe:edit_unit', kwargs={'unit_id': self.unit.pk})
        response = self.client.post(url, self._post_data(hat_count=4, small_hat_count=2))
        self.assertRedirects(response, reverse('SkaRe:list_units'))
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.hat_count, 4)
        self.assertEqual(self.unit.small_hat_count, 2)


# ---------------------------------------------------------------------------
# edit_individual_participant view: small_hat_count persists
# ---------------------------------------------------------------------------

class EditIndividualParticipantSmallHatCountTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='ipowner', password='pw')
        self.client.login(username='ipowner', password='pw')
        self.entity = Entity.objects.create(
            created_by=self.user,
            contact_email='ip@test.cz',
            contact_phone='+420123456789',
            unlocked_for_editing=True,
        )
        self.participant = IndividualParticipant.objects.create(
            entity=self.entity,
            first_name='Anna',
            last_name='Nováková',
            date_of_birth=datetime.date(1995, 6, 15),
        )

    def _post_data(self, **overrides):
        data = {
            # IndividualParticipantEditForm fields
            'first_name': 'Anna',
            'last_name': 'Nováková',
            'nickname': '',
            'date_of_birth': '1995-06-15',
            'health_restrictions': '',
            'diet_other': '',
            'relevant_information': '',
            'boats_p550': 0,
            'boats_sail': 0,
            'boats_paddle': 0,
            'boats_motor': 0,
            'scarf_count': 0,
            'hat_count': 0,
            'small_hat_count': 0,
            'accommodation_expectations': '',
            'estimated_accommodation_area': '',
            # EntityEditForm fields
            'contact_email': 'ip@test.cz',
            'contact_phone': '+420123456789',
            'expected_arrival': '',
            'expected_departure': '',
            'home_town': '',
        }
        data.update(overrides)
        return data

    def test_small_hat_count_saved_on_edit(self):
        url = reverse('SkaRe:edit_individual_participant', kwargs={'participant_id': self.participant.pk})
        response = self.client.post(url, self._post_data(small_hat_count=7))
        self.assertRedirects(response, reverse('SkaRe:list_individual_participants'))
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.small_hat_count, 7)

    def test_hat_count_still_saved_on_edit(self):
        url = reverse('SkaRe:edit_individual_participant', kwargs={'participant_id': self.participant.pk})
        response = self.client.post(url, self._post_data(hat_count=3, small_hat_count=1))
        self.assertRedirects(response, reverse('SkaRe:list_individual_participants'))
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.hat_count, 3)
        self.assertEqual(self.participant.small_hat_count, 1)


# ---------------------------------------------------------------------------
# Merchandise template rendering
# ---------------------------------------------------------------------------

class MerchandiseTemplateHatSplitTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(username='staff', password='pw', is_staff=True)
        self.client.login(username='staff', password='pw')

    def _make_entity(self):
        return Entity.objects.create(
            created_by=self.staff,
            contact_email='x@x.cz',
            contact_phone='123456789',
        )

    def test_template_renders_hat_size_column_headers(self):
        response = self.client.get(reverse('SkaRe:list_merchandise'))
        self.assertContains(response, 'L/XL')
        self.assertContains(response, 'S/M')

    def test_template_renders_unit_small_hat_count(self):
        entity = self._make_entity()
        Unit.objects.create(entity=entity, contact_person_name='A', hat_count=2, small_hat_count=9)
        response = self.client.get(reverse('SkaRe:list_merchandise'))
        # The total footer should show the correct values
        self.assertEqual(response.context['total_hats_large'], 2)
        self.assertEqual(response.context['total_hats_small'], 9)
        # The rendered page should contain both values
        self.assertContains(response, '>2<')
        self.assertContains(response, '>9<')

    def test_template_does_not_render_old_total_hats_key(self):
        """Regression: renamed from total_hats to total_hats_large — old key must not appear."""
        response = self.client.get(reverse('SkaRe:list_merchandise'))
        self.assertNotIn('total_hats', response.context)
