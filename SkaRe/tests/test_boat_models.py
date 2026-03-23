from django.test import TestCase
from django.contrib.auth.models import User
from SkaRe.models import BoatClass, SailRegistryEntry, Boat


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
        names = list(BoatClass.objects.filter(name__in=['Alpha', 'Zeta']).values_list('name', flat=True))
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


class BoatModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='pw')
        self.boat_class = BoatClass.objects.create(
            name='P550', category=BoatClass.Category.SAIL, order=1
        )

    def _make_boat(self, **kwargs):
        defaults = dict(
            created_by=self.user,
            boat_class=self.boat_class,
            name='My Boat',
            contact_person='Jan Novák',
            contact_phone='+420123456789',
        )
        defaults.update(kwargs)
        return Boat.objects.create(**defaults)

    def test_str_with_sail_number(self):
        boat = self._make_boat(sail_number='CZE 42')
        self.assertEqual(str(boat), 'CZE 42 My Boat')

    def test_str_without_sail_number(self):
        boat = self._make_boat(sail_number='')
        self.assertEqual(str(boat), 'My Boat')

    def test_can_be_edited_by_creator(self):
        boat = self._make_boat()
        self.assertTrue(boat.can_be_edited(self.user))

    def test_cannot_be_edited_by_stranger(self):
        stranger = User.objects.create_user(username='stranger', password='pw')
        boat = self._make_boat()
        self.assertFalse(boat.can_be_edited(stranger))

    def test_can_be_edited_by_infodesk_member(self):
        from django.contrib.auth.models import Group
        infodesk, _ = Group.objects.get_or_create(name='InfoDesk')
        infodesk_user = User.objects.create_user(username='infodesk', password='pw')
        infodesk_user.groups.add(infodesk)
        boat = self._make_boat()
        self.assertTrue(boat.can_be_edited(infodesk_user))

    def test_cascade_delete_with_user(self):
        boat = self._make_boat()
        boat_id = boat.id
        self.user.delete()
        self.assertFalse(Boat.objects.filter(id=boat_id).exists())

    def test_boat_class_set_null_on_class_delete(self):
        boat = self._make_boat()
        self.boat_class.delete()
        boat.refresh_from_db()
        self.assertIsNone(boat.boat_class)
