from django.test import TestCase
from django.contrib.auth.models import Group
from SkaRe.models import BoatClass


class InfoDeskGroupMigrationTest(TestCase):
    def test_infodesk_group_exists(self):
        self.assertTrue(Group.objects.filter(name='InfoDesk').exists())


class BoatClassSeedTest(TestCase):
    def test_p550_class_exists(self):
        self.assertTrue(BoatClass.objects.filter(name='P550').exists())

    def test_canoe_class_exists(self):
        self.assertTrue(BoatClass.objects.filter(name='canoe').exists())

    def test_sail_category_other_exists(self):
        self.assertTrue(
            BoatClass.objects.filter(category=BoatClass.Category.SAIL, is_other=True).exists()
        )

    def test_other_category_other_exists(self):
        self.assertTrue(
            BoatClass.objects.filter(category=BoatClass.Category.OTHER, is_other=True).exists()
        )

    def test_expected_sail_class_count(self):
        # P550, 420, Cadet, Fireball, Evropa, Optimist, Finn, Other = 8
        self.assertEqual(BoatClass.objects.filter(category=BoatClass.Category.SAIL).count(), 8)

    def test_expected_other_class_count(self):
        # paddleboard, windsurf, canoe, motorboat, seakayak, Other = 6
        self.assertEqual(BoatClass.objects.filter(category=BoatClass.Category.OTHER).count(), 6)
