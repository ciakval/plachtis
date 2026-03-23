from django.test import TestCase
from SkaRe.models import BoatClass, SailRegistryEntry


class BoatClassModelTest(TestCase):
    def test_str_returns_name(self):
        bc = BoatClass(name='P550', category=BoatClass.Category.SAIL, is_other=False, order=1)
        self.assertEqual(str(bc), 'P550')

    def test_category_choices_exist(self):
        self.assertIn('SAIL', [c[0] for c in BoatClass.Category.choices])
        self.assertIn('OTHER', [c[0] for c in BoatClass.Category.choices])

    def test_default_ordering_by_order_then_name(self):
        BoatClass.objects.create(name='Zeta', category=BoatClass.Category.SAIL, order=2)
        BoatClass.objects.create(name='Alpha', category=BoatClass.Category.SAIL, order=1)
        names = list(BoatClass.objects.values_list('name', flat=True))
        self.assertEqual(names, ['Alpha', 'Zeta'])


class SailRegistryEntryModelTest(TestCase):
    def test_str_returns_sail_number(self):
        entry = SailRegistryEntry(sail_number='CZE 1234')
        self.assertEqual(str(entry), 'CZE 1234')

    def test_sail_number_unique(self):
        SailRegistryEntry.objects.create(sail_number='CZE 1234')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SailRegistryEntry.objects.create(sail_number='CZE 1234')
