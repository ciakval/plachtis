from django.test import TestCase
from django.contrib.auth.models import User
from SkaRe.models import RegularParticipant, Unit, Entity
from datetime import date


def _make_unit(user):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='u@example.com',
        contact_phone='123456789',
    )
    return Unit.objects.create(
        entity=entity,
        contact_person_name='Leader',
    )


class PersonDietaryFieldsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.unit = _make_unit(self.user)

    def _make_person(self, **kw):
        return RegularParticipant.objects.create(
            unit=self.unit,
            first_name='Jan',
            last_name='Novak',
            date_of_birth=date(2000, 1, 1),
            **kw
        )

    def test_all_diet_booleans_default_false(self):
        p = self._make_person()
        for field in [
            'diet_vegetarian', 'diet_vegan',
            'diet_no_soy', 'diet_lactose_free', 'diet_gluten_free',
            'diet_no_peanuts', 'diet_no_eggs', 'diet_no_fish',
        ]:
            self.assertFalse(getattr(p, field), f'{field} should default to False')

    def test_diet_other_blank_by_default(self):
        p = self._make_person()
        self.assertEqual(p.diet_other, '')

    def test_diet_vegan_can_be_set(self):
        p = self._make_person(diet_vegan=True)
        p.refresh_from_db()
        self.assertTrue(p.diet_vegan)

    def test_dietary_summary_empty_when_no_restrictions(self):
        p = self._make_person()
        self.assertEqual(p.dietary_summary(), '')

    def test_dietary_summary_lists_active_flags(self):
        p = self._make_person(diet_vegan=True, diet_gluten_free=True)
        summary = p.dietary_summary()
        self.assertIn('Vegan', summary)
        self.assertIn('Gluten-free', summary)

    def test_dietary_summary_includes_diet_other(self):
        p = self._make_person(diet_other='no bee products')
        summary = p.dietary_summary()
        self.assertIn('no bee products', summary)

    def test_old_dietary_restrictions_field_gone(self):
        p = self._make_person()
        self.assertFalse(hasattr(p, 'dietary_restrictions'))
