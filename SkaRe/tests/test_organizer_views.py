from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from SkaRe.models import Entity, Organizer, EventSettings


def _make_organizer(user):
    entity = Entity.objects.create(
        created_by=user, contact_email='o@example.com', contact_phone='+420777000000',
    )
    return Organizer.objects.create(
        entity=entity, first_name='Org', last_name='User',
        date_of_birth=date(1980, 1, 1),
    )


class OrganizerRegistrationDeadlineTest(TestCase):
    """Organizer registration must not be blocked by the registration deadline (issue #124)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='owner', password='pw')
        self.client.login(username='owner', password='pw')

        # Close registration deadline
        settings = EventSettings.get_solo()
        settings.registration_deadline = timezone.now() - timedelta(hours=1)
        settings.save()

    def test_register_organizer_allowed_after_deadline(self):
        url = reverse('SkaRe:register_organizer')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_register_organizer_post_allowed_after_deadline(self):
        url = reverse('SkaRe:register_organizer')
        # GET first to generate a form token in the session
        get_response = self.client.get(url)
        form_token = self.client.session.get('form_token', '')
        data = {
            'first_name': 'Jan',
            'last_name': 'Novák',
            'date_of_birth': '1990-01-01',
            'contact_email': 'jan@example.com',
            'contact_phone': '+420123456789',
            'division': 'OTHERS',
            'transport': 'PUBLIC',
            'accommodation': 'OWN_TENT',
            'codex_agreement': True,
            'form_token': form_token,
        }
        response = self.client.post(url, data)
        self.assertEqual(Organizer.objects.count(), 1)
        self.assertRedirects(response, reverse('SkaRe:home'))

    def test_register_organizer_page_has_no_deadline_info(self):
        url = reverse('SkaRe:register_organizer')
        response = self.client.get(url)
        self.assertNotContains(response, 'Registration deadline')


class OrganizerEditDeadlineTest(TestCase):
    """Organizer editing must not be blocked by the editing deadline (issue #124)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='owner', password='pw')
        self.client.login(username='owner', password='pw')

        # Close editing deadline
        settings = EventSettings.get_solo()
        settings.editing_deadline = timezone.now() - timedelta(hours=1)
        settings.save()

        self.organizer = _make_organizer(self.user)

    def test_edit_organizer_allowed_after_editing_deadline(self):
        url = reverse('SkaRe:edit_organizer', kwargs={'organizer_id': self.organizer.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
