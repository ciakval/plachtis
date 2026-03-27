from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from SkaRe.models import Entity, Unit, RegularParticipant, EventSettings
from django.utils import timezone
from datetime import timedelta, date


class StableParticipantIdTest(TestCase):
    """Issue #34: Saving a unit must not delete and recreate participants."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='owner', password='pw')
        self.client.login(username='owner', password='pw')

        # Open editing
        settings = EventSettings.get_solo()
        settings.editing_deadline = timezone.now() + timedelta(hours=1)
        settings.save()

        # Create a unit with two participants
        entity = Entity.objects.create(
            created_by=self.user,
            contact_email='t@example.com',
            contact_phone='123456789',
        )
        self.unit = Unit.objects.create(entity=entity, contact_person_name='Leader')
        self.p1 = RegularParticipant.objects.create(
            unit=self.unit,
            first_name='Alice',
            last_name='Smith',
            date_of_birth=date(2000, 1, 1),
        )
        self.p2 = RegularParticipant.objects.create(
            unit=self.unit,
            first_name='Bob',
            last_name='Jones',
            date_of_birth=date(2001, 6, 15),
        )
        self.original_p1_pk = self.p1.pk
        self.original_p2_pk = self.p2.pk

    def test_participant_ids_unchanged_after_edit(self):
        url = reverse('SkaRe:edit_unit', kwargs={'unit_id': self.unit.pk})
        data = {
            # Entity fields
            'scout_unit_name': 'Test Unit',
            'scout_unit_evidence_id': '523.10',
            'contact_email': 't@example.com',
            'contact_phone': '123456789',
            # Unit fields
            'contact_person_name': 'Leader',
            'backup_contact_phone': '',
            'boats_p550': '0', 'boats_sail': '0', 'boats_paddle': '0', 'boats_motor': '0',
            'scarf_count': '0', 'hat_count': '0', 'small_hat_count': '0',
            'accommodation_expectations': '', 'estimated_accommodation_area': '',
            # Formset management
            'participants-TOTAL_FORMS': '2',
            'participants-INITIAL_FORMS': '2',
            'participants-MIN_NUM_FORMS': '0',
            'participants-MAX_NUM_FORMS': '1000',
            # Existing participant 0
            f'participants-0-id': str(self.p1.pk),
            f'participants-0-first_name': 'Alice',
            f'participants-0-last_name': 'Smith',
            f'participants-0-date_of_birth': '2000-01-01',
            f'participants-0-nickname': '',
            f'participants-0-health_restrictions': '',
            f'participants-0-diet_vegan': '',
            f'participants-0-diet_vegetarian': '',
            f'participants-0-diet_gluten_free': '',
            f'participants-0-diet_lactose_free': '',
            f'participants-0-diet_no_eggs': '',
            f'participants-0-diet_no_peanuts': '',
            f'participants-0-diet_no_tree_nuts': '',
            f'participants-0-diet_no_soy': '',
            f'participants-0-diet_no_fish': '',
            f'participants-0-diet_no_fruits': '',
            f'participants-0-diet_other': '',
            f'participants-0-relevant_information': '',
            f'participants-0-DELETE': '',
            # Existing participant 1
            f'participants-1-id': str(self.p2.pk),
            f'participants-1-first_name': 'Bob',
            f'participants-1-last_name': 'Jones',
            f'participants-1-date_of_birth': '2001-06-15',
            f'participants-1-nickname': '',
            f'participants-1-health_restrictions': '',
            f'participants-1-diet_vegan': '',
            f'participants-1-diet_vegetarian': '',
            f'participants-1-diet_gluten_free': '',
            f'participants-1-diet_lactose_free': '',
            f'participants-1-diet_no_eggs': '',
            f'participants-1-diet_no_peanuts': '',
            f'participants-1-diet_no_tree_nuts': '',
            f'participants-1-diet_no_soy': '',
            f'participants-1-diet_no_fish': '',
            f'participants-1-diet_no_fruits': '',
            f'participants-1-diet_other': '',
            f'participants-1-relevant_information': '',
            f'participants-1-DELETE': '',
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('SkaRe:list_units'))

        # PKs must be unchanged
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.pk, self.original_p1_pk)
        self.assertEqual(self.p2.pk, self.original_p2_pk)

        # Count must still be 2
        self.assertEqual(RegularParticipant.objects.filter(unit=self.unit).count(), 2)
