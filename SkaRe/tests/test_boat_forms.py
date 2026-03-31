from django.test import TestCase
from SkaRe.forms import BoatForm
from SkaRe.models import BoatClass


class BoatFormTest(TestCase):
    def setUp(self):
        self.boat_class = BoatClass.objects.create(
            name='TestClass', category=BoatClass.Category.SAIL, order=99
        )

    def _valid_data(self, **overrides):
        data = {
            'boat_class': self.boat_class.pk,
            'class_supplement': '',
            'sail_number': 'CZE 42',
            'name': 'My Boat',
            'description': '',
            'sail_area': '',
            'hull_color': 'Bílá',
            'sail_color': 'Modrá',
            'harbor_number': '523.10',
            'harbor_name': '5. oddíl Koráb',
            'contact_person': 'Jan Novák',
            'contact_phone': '+420123456789',
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = BoatForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_name_required(self):
        form = BoatForm(data=self._valid_data(name=''))
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_contact_person_required(self):
        form = BoatForm(data=self._valid_data(contact_person=''))
        self.assertFalse(form.is_valid())
        self.assertIn('contact_person', form.errors)

    def test_contact_phone_required(self):
        form = BoatForm(data=self._valid_data(contact_phone=''))
        self.assertFalse(form.is_valid())
        self.assertIn('contact_phone', form.errors)

    def test_sail_number_optional(self):
        form = BoatForm(data=self._valid_data(sail_number=''))
        self.assertTrue(form.is_valid(), form.errors)

    def test_boat_class_queryset_ordered_by_order(self):
        BoatClass.objects.create(name='ZClass', category=BoatClass.Category.SAIL, order=100)
        form = BoatForm()
        pks = list(form.fields['boat_class'].queryset.values_list('pk', flat=True))
        # TestClass (order=99) should come before ZClass (order=100)
        idx_test = pks.index(self.boat_class.pk)
        zclass = BoatClass.objects.get(name='ZClass')
        idx_z = pks.index(zclass.pk)
        self.assertLess(idx_test, idx_z)


class ValidateEventPhoneTest(TestCase):
    def _valid(self, number):
        from SkaRe.forms import validate_event_phone
        from django.core.exceptions import ValidationError
        try:
            validate_event_phone(number)
            return True
        except ValidationError:
            return False

    def test_czech_with_prefix(self):
        self.assertTrue(self._valid('+420 123 456 789'))

    def test_czech_local_nine_digits(self):
        self.assertTrue(self._valid('123456789'))

    def test_slovak_prefix(self):
        self.assertTrue(self._valid('+421 900 123 456'))

    def test_german_prefix(self):
        self.assertTrue(self._valid('+49 30 12345678'))

    def test_austrian_prefix(self):
        self.assertTrue(self._valid('+43 1 58858'))

    def test_polish_prefix(self):
        self.assertTrue(self._valid('+48 600 123 456'))

    def test_hungarian_prefix(self):
        self.assertTrue(self._valid('+36 20 123 4567'))

    def test_too_short_rejected(self):
        self.assertFalse(self._valid('12345'))

    def test_letters_rejected(self):
        self.assertFalse(self._valid('abc def'))

    def test_eight_digits_without_prefix_rejected(self):
        self.assertFalse(self._valid('12345678'))


class BoatFormNewFieldsTest(TestCase):
    def _base_data(self):
        bc = BoatClass.objects.create(
            name='FormTestClass', category=BoatClass.Category.SAIL, order=99
        )
        return {
            'boat_class': bc.pk,
            'sail_number': '14',
            'name': 'Albatros',
            'hull_color': 'Bílá',
            'sail_color': 'Modrá',
            'contact_person': 'Jan Novák',
            'contact_phone': '+420 123 456 789',
        }

    def test_form_valid_with_hull_and_sail_color(self):
        data = self._base_data()
        data['hull_color'] = 'Modrá'
        data['sail_color'] = 'Červená'
        form = BoatForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_hull_color_required(self):
        data = self._base_data()
        data['hull_color'] = ''
        form = BoatForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('hull_color', form.errors)

    def test_sail_color_optional(self):
        data = self._base_data()
        data['sail_color'] = ''
        form = BoatForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn('sail_color', form.errors)

    def test_boat_class_now_required(self):
        data = self._base_data()
        data['boat_class'] = ''
        form = BoatForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('boat_class', form.errors)

    def test_contact_phone_validated_with_event_validator(self):
        data = self._base_data()
        data['contact_phone'] = '12345'  # too short
        form = BoatForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('contact_phone', form.errors)

    def test_german_phone_accepted(self):
        data = self._base_data()
        data['contact_phone'] = '+49 30 12345678'
        form = BoatForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


class BoatFormWillingToLendTest(TestCase):
    def setUp(self):
        from SkaRe.forms import BoatForm
        self.BoatForm = BoatForm
        BoatClass.objects.create(name='P550', category=BoatClass.Category.SAIL, order=1)

    def _valid_data(self, **overrides):
        bc = BoatClass.objects.first()
        data = {
            'boat_class': bc.pk,
            'name': 'Test Boat',
            'hull_color': 'Bílá',
            'sail_color': 'Modrá',
            'contact_person': 'Jan',
            'contact_phone': '123456789',
            'willing_to_lend': False,
        }
        data.update(overrides)
        return data

    def test_willing_to_lend_in_form(self):
        form = self.BoatForm(data=self._valid_data(willing_to_lend=True))
        self.assertIn('willing_to_lend', form.fields)

    def test_form_valid_with_willing_to_lend_true(self):
        form = self.BoatForm(data=self._valid_data(willing_to_lend=True))
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_valid_with_willing_to_lend_false(self):
        form = self.BoatForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)
