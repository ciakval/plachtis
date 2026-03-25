import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from SkaRe.models import BoatClass, Boat, Entity, Unit, IndividualParticipant


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


class BoatColorFieldTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='colortest', password='pw')
        self.bc = BoatClass.objects.create(
            name='TestClass', category=BoatClass.Category.SAIL, order=99
        )

    def _make_boat(self, **kw):
        return Boat.objects.create(
            created_by=self.user, boat_class=self.bc,
            name='Test', contact_person='J', contact_phone='123456789',
            **kw
        )

    def test_hull_color_blank_by_default(self):
        boat = self._make_boat()
        self.assertEqual(boat.hull_color, '')

    def test_sail_color_blank_by_default(self):
        boat = self._make_boat()
        self.assertEqual(boat.sail_color, '')

    def test_hull_color_accepts_valid_choice(self):
        boat = self._make_boat(hull_color=Boat.Color.WHITE)
        boat.refresh_from_db()
        self.assertEqual(boat.hull_color, 'bila')

    def test_vessel_registry_number_blank_by_default(self):
        boat = self._make_boat()
        self.assertEqual(boat.vessel_registry_number, '')

    def test_engine_power_hp_null_by_default(self):
        boat = self._make_boat()
        self.assertIsNone(boat.engine_power_hp)

    def test_engine_power_hp_stores_integer(self):
        boat = self._make_boat(engine_power_hp=15)
        boat.refresh_from_db()
        self.assertEqual(boat.engine_power_hp, 15)


class BoatLendingFieldsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='lendtest', password='pw')
        self.borrower = User.objects.create_user(username='borrower', password='pw')
        self.bc = BoatClass.objects.create(name='P550', category=BoatClass.Category.SAIL, order=1)

    def _make_boat(self, **kw):
        return Boat.objects.create(
            created_by=self.user, boat_class=self.bc,
            name='Lendable', contact_person='J', contact_phone='123456789',
            **kw
        )

    def test_willing_to_lend_defaults_false(self):
        boat = self._make_boat()
        boat.refresh_from_db()
        self.assertFalse(boat.willing_to_lend)

    def test_willing_to_lend_can_be_set_true(self):
        boat = self._make_boat(willing_to_lend=True)
        boat.refresh_from_db()
        self.assertTrue(boat.willing_to_lend)

    def test_visible_to_empty_by_default(self):
        boat = self._make_boat()
        self.assertEqual(boat.visible_to.count(), 0)

    def test_visible_to_add_user(self):
        boat = self._make_boat()
        boat.visible_to.add(self.borrower)
        self.assertIn(self.borrower, boat.visible_to.all())

    def test_borrowed_boats_reverse_relation(self):
        boat = self._make_boat()
        boat.visible_to.add(self.borrower)
        self.assertIn(boat, self.borrower.borrowed_boats.all())


class HatSizeSplitTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='htest', password='pw')
        self.entity = Entity.objects.create(
            created_by=self.user,
            contact_email='h@test.cz',
            contact_phone='123456789',
        )
        self.unit = Unit.objects.create(entity=self.entity, contact_person_name='Test')

    def test_unit_small_hat_count_defaults_to_zero(self):
        self.assertEqual(self.unit.small_hat_count, 0)

    def test_unit_hat_count_verbose_name(self):
        field = Unit._meta.get_field('hat_count')
        self.assertIn('L/XL', str(field.verbose_name))

    def test_unit_small_hat_count_verbose_name(self):
        field = Unit._meta.get_field('small_hat_count')
        self.assertIn('S/M', str(field.verbose_name))

    def test_unit_small_hat_count_stores_value(self):
        self.unit.small_hat_count = 3
        self.unit.save()
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.small_hat_count, 3)

    def test_individual_participant_small_hat_count_defaults_to_zero(self):
        ip = IndividualParticipant.objects.create(
            entity=Entity.objects.create(
                created_by=self.user,
                contact_email='ip@test.cz',
                contact_phone='123456789',
            ),
            first_name='A', last_name='B',
            date_of_birth=datetime.date(2000, 1, 1),
        )
        self.assertEqual(ip.small_hat_count, 0)
