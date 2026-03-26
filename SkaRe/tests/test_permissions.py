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
