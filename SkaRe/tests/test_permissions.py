from django.test import TestCase
from django.contrib.auth.models import User, Group
from SkaRe.permissions import is_infodesk, is_race_management


class IsInfodeskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='pass')
        self.group, _ = Group.objects.get_or_create(name='InfoDesk')

    def test_returns_false_for_user_without_group(self):
        self.assertFalse(is_infodesk(self.user))

    def test_returns_true_for_user_in_infodesk_group(self):
        self.user.groups.add(self.group)
        self.assertTrue(is_infodesk(self.user))

    def test_race_management_user_is_not_infodesk(self):
        rm_group, _ = Group.objects.get_or_create(name='RaceManagement')
        self.user.groups.add(rm_group)
        self.assertFalse(is_infodesk(self.user))


class IsRaceManagementTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester2', password='pass')
        self.group, _ = Group.objects.get_or_create(name='RaceManagement')

    def test_returns_false_for_user_without_group(self):
        self.assertFalse(is_race_management(self.user))

    def test_returns_true_for_user_in_race_management_group(self):
        self.user.groups.add(self.group)
        self.assertTrue(is_race_management(self.user))

    def test_infodesk_user_is_not_race_management(self):
        id_group, _ = Group.objects.get_or_create(name='InfoDesk')
        self.user.groups.add(id_group)
        self.assertFalse(is_race_management(self.user))


from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from SkaRe.permissions import is_infodesk, is_race_management, infodesk_required
from SkaRe.models import Entity, EventSettings
from django.utils import timezone
from datetime import timedelta


class InfodeskRequiredDecoratorTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='reg_user', password='pw')
        self.infodesk_user = User.objects.create_user(username='infodesk', password='pw')
        infodesk_group, _ = Group.objects.get_or_create(name='InfoDesk')
        self.infodesk_user.groups.add(infodesk_group)

        @infodesk_required
        def protected_view(request):
            return HttpResponse('ok')

        self.view = protected_view

    def test_anonymous_redirected(self):
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        response = self.view(request)
        self.assertEqual(response.status_code, 302)

    def test_regular_user_returns_403(self):
        request = self.factory.get('/test/')
        request.user = self.user
        response = self.view(request)
        self.assertEqual(response.status_code, 403)

    def test_infodesk_user_allowed(self):
        request = self.factory.get('/test/')
        request.user = self.infodesk_user
        response = self.view(request)
        self.assertEqual(response.status_code, 200)


class EntityCanBeEditedInfodeskTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.other = User.objects.create_user(username='other', password='pw')
        self.infodesk_user = User.objects.create_user(username='infodesk', password='pw')
        infodesk_group, _ = Group.objects.get_or_create(name='InfoDesk')
        self.infodesk_user.groups.add(infodesk_group)

        self.entity = Entity.objects.create(
            created_by=self.owner,
            contact_email='test@example.com',
            contact_phone='123456789',
        )

    def _set_editing_closed(self):
        settings = EventSettings.get_solo()
        settings.editing_deadline = timezone.now() - timedelta(hours=1)
        settings.save()

    def _set_editing_open(self):
        settings = EventSettings.get_solo()
        settings.editing_deadline = timezone.now() + timedelta(hours=1)
        settings.save()

    def test_owner_can_edit_when_open(self):
        self._set_editing_open()
        self.assertTrue(self.entity.can_be_edited(self.owner))

    def test_owner_cannot_edit_when_closed(self):
        self._set_editing_closed()
        self.assertFalse(self.entity.can_be_edited(self.owner))

    def test_infodesk_can_edit_when_open(self):
        self._set_editing_open()
        self.assertTrue(self.entity.can_be_edited(self.infodesk_user))

    def test_infodesk_can_edit_when_closed(self):
        self._set_editing_closed()
        self.assertTrue(self.entity.can_be_edited(self.infodesk_user))

    def test_infodesk_can_edit_entity_they_dont_own(self):
        self._set_editing_closed()
        # infodesk_user is neither owner nor editor
        self.assertTrue(self.entity.can_be_edited(self.infodesk_user))

    def test_non_owner_non_infodesk_cannot_edit(self):
        self._set_editing_open()
        self.assertFalse(self.entity.can_be_edited(self.other))
