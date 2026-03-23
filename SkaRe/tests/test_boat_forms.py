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

    def test_boat_class_optional(self):
        form = BoatForm(data=self._valid_data(boat_class=''))
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
