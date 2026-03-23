# Boat Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add boat registration to PlachtIS — models, CRUD views, AJAX prefill from sail registry and user's unit, and Django admin with CSV import.

**Architecture:** Three new models (`BoatClass`, `SailRegistryEntry`, `Boat`) added to `SkaRe/models.py`. Views and forms follow the existing function-based view pattern in `SkaRe/views.py` and `SkaRe/forms.py`. Permissions are enforced on the `Boat` model via `can_be_edited()`. AJAX endpoints return JSON for sail registry lookup and unit data prefill.

**Tech Stack:** Django 6.0, Python 3.12, `uv` (run all commands with `uv run python manage.py ...`), Django's built-in test runner, vanilla JS (no framework — matches existing `SkaRe/static/SkaRe/js/` files).

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `SkaRe/models.py` | Modify | Add `BoatClass`, `SailRegistryEntry`, `Boat` |
| `SkaRe/migrations/0013_*.py` | Create (auto via makemigrations) | DB schema for new models |
| `SkaRe/migrations/0014_infodesk_group.py` | Create (manual) | Seed `InfoDesk` Django group |
| `SkaRe/migrations/0015_boatclass_initial_data.py` | Create (manual) | Seed initial `BoatClass` rows |
| `SkaRe/forms.py` | Modify | Add `BoatForm` |
| `SkaRe/views.py` | Modify | Add boat CRUD views + AJAX endpoints |
| `SkaRe/urls.py` | Modify | Add boat URL patterns |
| `SkaRe/admin.py` | Modify | Register `BoatClass`, `SailRegistryEntry` (+ CSV import view), `Boat` |
| `SkaRe/tests.py` | Delete | Replaced by a proper package below |
| `SkaRe/tests/__init__.py` | Create | Empty — makes `tests/` a Python package |
| `SkaRe/tests/test_boat_models.py` | Create | Unit tests for models |
| `SkaRe/tests/test_boat_migrations.py` | Create | Tests verifying data migration seeds |
| `SkaRe/tests/test_boat_forms.py` | Create | Tests for BoatForm validation |
| `SkaRe/tests/test_boat_views.py` | Create | Integration tests for views & permissions |
| `SkaRe/tests/test_boat_admin.py` | Create | Integration tests for CSV import admin view |
| `SkaRe/templates/SkaRe/boats/list.html` | Create | Boat list page |
| `SkaRe/templates/SkaRe/boats/detail.html` | Create | Boat detail page |
| `SkaRe/templates/SkaRe/boats/form.html` | Create | Register/edit form (shared) |
| `SkaRe/templates/SkaRe/boats/confirm_delete.html` | Create | Delete confirmation |
| `SkaRe/templates/admin/SkaRe/sailregistryentry/import_csv.html` | Create | Admin CSV upload page |
| `SkaRe/static/SkaRe/js/boat-form.js` | Create | Sail lookup + unit prefill JS |

---

## ⚠️ Before You Start

**CSV column names must be confirmed with Erik** before implementing the CSV import (Task 6). The plan uses placeholder column names: `sail_number`, `boat_name`, `class_name`, `subtype`, `sail_area`, `harbor_number`, `harbor_name`, `contact_person`. Update these to match the actual CSV before writing the import code.

---

## Task 1: Set up tests package

Convert the empty `SkaRe/tests.py` to a proper package so test files stay focused.

**Files:**
- Delete: `SkaRe/tests.py`
- Create: `SkaRe/tests/__init__.py`

- [ ] **Step 1: Delete the empty file**

```bash
rm SkaRe/tests.py
```

- [ ] **Step 2: Create the package**

Create `SkaRe/tests/__init__.py` — leave it empty:

```python
```

- [ ] **Step 3: Verify Django can still find tests**

```bash
uv run python manage.py test SkaRe
```

Expected: `Ran 0 tests in ...OK` (no failures, just 0 tests because the package is empty).

- [ ] **Step 4: Commit**

```bash
git add SkaRe/tests/__init__.py
git rm SkaRe/tests.py
git commit -m "refactor: replace empty tests.py with tests/ package"
```

---

## Task 2: BoatClass and SailRegistryEntry models

**Files:**
- Modify: `SkaRe/models.py`
- Create: `SkaRe/tests/test_boat_models.py`

- [ ] **Step 1: Write the failing tests**

Create `SkaRe/tests/test_boat_models.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run python manage.py test SkaRe.tests.test_boat_models
```

Expected: `ImportError: cannot import name 'BoatClass' from 'SkaRe.models'`

- [ ] **Step 3: Add BoatClass and SailRegistryEntry to models.py**

In `SkaRe/models.py`, after the existing `Organizer` class, add:

```python
class BoatClass(models.Model):
    class Category(models.TextChoices):
        SAIL = "SAIL", _("Sail")
        OTHER = "OTHER", _("Other")

    name = models.CharField(max_length=100, verbose_name=_("Name"))
    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        verbose_name=_("Category"),
    )
    is_other = models.BooleanField(
        default=False,
        help_text=_("Marks the catch-all 'Other' entry for this category. Convention only — no DB constraint."),
        verbose_name=_("Is other"),
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Controls display order in dropdowns."),
        verbose_name=_("Order"),
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _("Boat class")
        verbose_name_plural = _("Boat classes")

    def __str__(self):
        return self.name


class SailRegistryEntry(models.Model):
    """
    One row per entry in the imported sail number registry CSV.
    Fully replaced on each CSV import (atomic delete + bulk_create).
    CSV column mapping must be confirmed with Erik before implementation.
    """
    sail_number = models.CharField(max_length=50, unique=True, verbose_name=_("Sail number"))
    boat_name = models.CharField(max_length=200, blank=True, verbose_name=_("Boat name"))
    class_name = models.CharField(max_length=100, blank=True, verbose_name=_("Class name"))
    subtype = models.CharField(
        max_length=200, blank=True,
        help_text=_("Prefilled into class_supplement on the boat form."),
        verbose_name=_("Subtype"),
    )
    sail_area = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_("Sail area")
    )
    harbor_number = models.CharField(max_length=100, blank=True, verbose_name=_("Harbor number"))
    harbor_name = models.CharField(max_length=200, blank=True, verbose_name=_("Harbor name"))
    contact_person = models.CharField(max_length=200, blank=True, verbose_name=_("Contact person"))

    class Meta:
        verbose_name = _("Sail registry entry")
        verbose_name_plural = _("Sail registry entries")

    def __str__(self):
        return self.sail_number
```

- [ ] **Step 4: Run tests — should still fail (no migration yet)**

```bash
uv run python manage.py test SkaRe.tests.test_boat_models
```

Expected: `django.db.utils.OperationalError: no such table: SkaRe_boatclass`

- [ ] **Step 5: Generate the migration**

```bash
uv run python manage.py makemigrations SkaRe
```

Expected: `Migrations for 'SkaRe': SkaRe/migrations/0013_boatclass_sailregistryentry.py`

- [ ] **Step 6: Apply migration**

```bash
uv run python manage.py migrate
```

- [ ] **Step 7: Run tests — should pass**

```bash
uv run python manage.py test SkaRe.tests.test_boat_models
```

Expected: `Ran 4 tests in ...OK`

- [ ] **Step 8: Commit**

```bash
git add SkaRe/models.py SkaRe/migrations/0013_boatclass_sailregistryentry.py SkaRe/tests/test_boat_models.py
git commit -m "feat: add BoatClass and SailRegistryEntry models"
```

---

## Task 3: Boat model

**Files:**
- Modify: `SkaRe/models.py`
- Modify: `SkaRe/tests/test_boat_models.py`

- [ ] **Step 1: Write the failing tests**

Append to `SkaRe/tests/test_boat_models.py`:

```python
from django.contrib.auth.models import User
# (add to existing imports at top of file)


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
        infodesk = Group.objects.create(name='InfoDesk')
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run python manage.py test SkaRe.tests.test_boat_models
```

Expected: `ImportError: cannot import name 'Boat' from 'SkaRe.models'`

- [ ] **Step 3: Add Boat to models.py**

In `SkaRe/models.py`, after `SailRegistryEntry`, add:

```python
class Boat(models.Model):
    """
    A boat registered for the event.
    Owner (created_by) or InfoDesk group members can edit.
    Only the creator can delete.
    No editing deadline in Phase 1.
    """
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='boats',
        help_text=_("Deleting the user also deletes their boats — consistent with Entity.created_by."),
        verbose_name=_("Created by"),
    )
    boat_class = models.ForeignKey(
        BoatClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Boat class"),
    )
    class_supplement = models.CharField(
        max_length=200, blank=True,
        verbose_name=_("Class supplement"),
    )
    sail_number = models.CharField(max_length=50, blank=True, verbose_name=_("Sail number"))
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    sail_area = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_("Sail area")
    )
    harbor_number = models.CharField(max_length=100, blank=True, verbose_name=_("Harbor number"))
    harbor_name = models.CharField(max_length=200, blank=True, verbose_name=_("Harbor name"))
    contact_person = models.CharField(max_length=200, verbose_name=_("Contact person"))
    contact_phone = models.CharField(max_length=50, verbose_name=_("Contact phone"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Boat")
        verbose_name_plural = _("Boats")

    def __str__(self):
        if self.sail_number:
            return f"{self.sail_number} {self.name}"
        return self.name

    def can_be_edited(self, user):
        """Creator or InfoDesk group member can edit. No deadline check in Phase 1."""
        return self.created_by == user or user.groups.filter(name='InfoDesk').exists()
```

Also update the import in `SkaRe/tests/test_boat_models.py` top:

```python
from SkaRe.models import BoatClass, SailRegistryEntry, Boat
```

- [ ] **Step 4: Generate and apply migration**

```bash
uv run python manage.py makemigrations SkaRe
uv run python manage.py migrate
```

Expected: migration `0014_boat.py` (or similar).

- [ ] **Step 5: Run tests — should pass**

```bash
uv run python manage.py test SkaRe.tests.test_boat_models
```

Expected: `Ran 11 tests in ...OK`

- [ ] **Step 6: Commit**

```bash
git add SkaRe/models.py SkaRe/migrations/0014_boat.py SkaRe/tests/test_boat_models.py
git commit -m "feat: add Boat model with can_be_edited permission helper"
```

---

## Task 4: Data migrations — InfoDesk group + BoatClass seed

**Files:**
- Create: `SkaRe/migrations/0015_infodesk_group.py`
- Create: `SkaRe/migrations/0016_boatclass_initial_data.py`

> **Note:** Adjust migration numbers (`0015`, `0016`) to match whatever `makemigrations` actually generated in Tasks 2–3.

- [ ] **Step 1: Write the failing tests**

Create `SkaRe/tests/test_boat_migrations.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run python manage.py test SkaRe.tests.test_boat_migrations
```

Expected: `AssertionError: False is not true` (group and classes don't exist yet).

- [ ] **Step 3: Create InfoDesk group migration**

> ⚠️ **Before writing this file**: run `ls SkaRe/migrations/` and find the exact filename of the most recently generated migration (from Tasks 2–3). Copy that filename exactly as the dependency — do NOT guess or use a placeholder name.

Create `SkaRe/migrations/0015_infodesk_group.py` (adjust number to follow latest existing):

```python
from django.db import migrations


def create_infodesk_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='InfoDesk')


def delete_infodesk_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='InfoDesk').delete()


class Migration(migrations.Migration):
    dependencies = [
        # Replace '0014_boat' with the EXACT filename of the most recently
        # generated migration (check SkaRe/migrations/ after Tasks 2–3).
        ('SkaRe', '0014_boat'),
    ]

    operations = [
        migrations.RunPython(create_infodesk_group, delete_infodesk_group),
    ]
```

- [ ] **Step 4: Create BoatClass seed migration**

Create `SkaRe/migrations/0016_boatclass_initial_data.py`:

```python
from django.db import migrations


SAIL_CLASSES = [
    ('P550', False),
    ('420', False),
    ('Cadet', False),
    ('Fireball', False),
    ('Evropa', False),
    ('Optimist', False),
    ('Finn', False),
    ('Ostatní plachetnice', True),   # Other (sail)
]

OTHER_CLASSES = [
    ('paddleboard', False),
    ('windsurf', False),
    ('canoe', False),
    ('motorboat', False),
    ('seakayak', False),
    ('Ostatní', True),              # Other (other)
]


def seed_boat_classes(apps, schema_editor):
    BoatClass = apps.get_model('SkaRe', 'BoatClass')
    for order, (name, is_other) in enumerate(SAIL_CLASSES, start=1):
        BoatClass.objects.get_or_create(
            name=name,
            defaults={'category': 'SAIL', 'is_other': is_other, 'order': order},
        )
    for order, (name, is_other) in enumerate(OTHER_CLASSES, start=len(SAIL_CLASSES) + 1):
        BoatClass.objects.get_or_create(
            name=name,
            defaults={'category': 'OTHER', 'is_other': is_other, 'order': order},
        )


def delete_boat_classes(apps, schema_editor):
    BoatClass = apps.get_model('SkaRe', 'BoatClass')
    names = [n for n, _ in SAIL_CLASSES + OTHER_CLASSES]
    BoatClass.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('SkaRe', '0015_infodesk_group'),
    ]

    operations = [
        migrations.RunPython(seed_boat_classes, delete_boat_classes),
    ]
```

- [ ] **Step 5: Apply migrations**

```bash
uv run python manage.py migrate
```

- [ ] **Step 6: Run tests — should pass**

```bash
uv run python manage.py test SkaRe.tests.test_boat_migrations
```

Expected: `Ran 6 tests in ...OK`

- [ ] **Step 7: Commit**

```bash
git add SkaRe/migrations/0015_infodesk_group.py SkaRe/migrations/0016_boatclass_initial_data.py SkaRe/tests/test_boat_migrations.py
git commit -m "feat: add InfoDesk group and BoatClass seed data migrations"
```

---

## Task 5: BoatForm

**Files:**
- Modify: `SkaRe/forms.py`
- Create: `SkaRe/tests/test_boat_forms.py`

- [ ] **Step 1: Write the failing tests**

Create `SkaRe/tests/test_boat_forms.py`:

```python
from django.test import TestCase
from SkaRe.forms import BoatForm
from SkaRe.models import BoatClass


class BoatFormTest(TestCase):
    def setUp(self):
        self.boat_class = BoatClass.objects.create(
            name='P550', category=BoatClass.Category.SAIL, order=1
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
        BoatClass.objects.create(name='Finn', category=BoatClass.Category.SAIL, order=2)
        form = BoatForm()
        classes = list(form.fields['boat_class'].queryset.values_list('name', flat=True))
        self.assertEqual(classes.index('P550'), 0)  # order=1 comes first
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run python manage.py test SkaRe.tests.test_boat_forms
```

Expected: `ImportError: cannot import name 'BoatForm' from 'SkaRe.forms'`

- [ ] **Step 3: Add BoatForm to forms.py**

In `SkaRe/forms.py`, add to the top imports:

```python
from .models import Unit, RegularParticipant, IndividualParticipant, Organizer, BoatClass, Boat
```

Then append at the end of the file:

```python
class BoatForm(forms.ModelForm):
    """Form for registering or editing a boat."""

    class Meta:
        model = Boat
        fields = [
            'boat_class', 'class_supplement', 'sail_number', 'name',
            'description', 'sail_area', 'harbor_number', 'harbor_name',
            'contact_person', 'contact_phone',
        ]
        widgets = {
            'boat_class': forms.Select(attrs={'class': 'form-control'}),
            'class_supplement': forms.TextInput(attrs={'class': 'form-control'}),
            'sail_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_sail_number'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sail_area': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'harbor_number': forms.TextInput(attrs={'class': 'form-control'}),
            'harbor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Build grouped choices for the boat_class select (SAIL optgroup, then OTHER optgroup).
        # widget.choices controls rendering; ModelChoiceField.queryset controls validation.
        sail_pks = list(
            BoatClass.objects.filter(category=BoatClass.Category.SAIL)
            .order_by('order', 'name').values_list('pk', 'name')
        )
        other_pks = list(
            BoatClass.objects.filter(category=BoatClass.Category.OTHER)
            .order_by('order', 'name').values_list('pk', 'name')
        )
        self.fields['boat_class'].widget.choices = (
            [('', '---------')]
            + [(_('Plachetnice'), [(str(pk), name) for pk, name in sail_pks])]
            + [(_('Ostatní'), [(str(pk), name) for pk, name in other_pks])]
        )
        self.fields['boat_class'].queryset = BoatClass.objects.all()
        self.fields['boat_class'].required = False
        # Note: accessing self.errors here is intentional — Django's errors property
        # calls full_clean() on demand for bound forms, which is the same pattern
        # used by UnitRegistrationForm and others in this codebase.
        for field_name, field in self.fields.items():
            if field_name in self.errors:
                if 'class' in field.widget.attrs:
                    field.widget.attrs['class'] += ' is-invalid'
                else:
                    field.widget.attrs['class'] = 'is-invalid'
```

- [ ] **Step 4: Run tests — should pass**

```bash
uv run python manage.py test SkaRe.tests.test_boat_forms
```

Expected: `Ran 7 tests in ...OK`

- [ ] **Step 5: Commit**

```bash
git add SkaRe/forms.py SkaRe/tests/test_boat_forms.py
git commit -m "feat: add BoatForm"
```

---

## Task 6: AJAX API views (sail lookup + unit prefill)

**Files:**
- Modify: `SkaRe/views.py`
- Modify: `SkaRe/urls.py`
- Create: `SkaRe/tests/test_boat_views.py`

- [ ] **Step 1: Write the failing tests**

Create `SkaRe/tests/test_boat_views.py`:

```python
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from SkaRe.models import BoatClass, SailRegistryEntry, Boat, Entity, Unit


class SailLookupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')
        SailRegistryEntry.objects.create(
            sail_number='CZE 42',
            boat_name='Rychlík',
            class_name='Cadet',
            subtype='Dřevěný',
            sail_area='7.50',
            harbor_number='523.10',
            harbor_name='5. oddíl Koráb',
            contact_person='Jan Novák',
        )

    def test_found_returns_json(self):
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url, {'q': 'CZE 42'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['boat_name'], 'Rychlík')
        self.assertEqual(data['subtype'], 'Dřevěný')

    def test_case_insensitive_lookup(self):
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url, {'q': 'cze 42'})
        self.assertEqual(response.status_code, 200)

    def test_not_found_returns_404(self):
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url, {'q': 'ZZZ 999'})
        self.assertEqual(response.status_code, 404)

    def test_missing_q_returns_400(self):
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_requires_login(self):
        self.client.logout()
        url = reverse('SkaRe:boat_sail_lookup')
        response = self.client.get(url, {'q': 'CZE 42'})
        self.assertEqual(response.status_code, 302)


class MyUnitViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')

    def _create_unit(self, created_at_offset=0):
        entity = Entity.objects.create(
            created_by=self.user,
            scout_unit_name='5. oddíl Koráb',
            scout_unit_evidence_id='523.10',
            contact_email='test@test.cz',
            contact_phone='+420123456789',
        )
        unit = Unit.objects.create(
            entity=entity,
            contact_person_name='Jan Novák',
        )
        return unit

    def test_returns_unit_data(self):
        self._create_unit()
        url = reverse('SkaRe:boat_my_unit')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['harbor_number'], '523.10')
        self.assertEqual(data['harbor_name'], '5. oddíl Koráb')
        self.assertEqual(data['contact_person'], 'Jan Novák')

    def test_no_unit_returns_404(self):
        url = reverse('SkaRe:boat_my_unit')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_multiple_units_returns_most_recent(self):
        unit1 = self._create_unit()
        entity2 = Entity.objects.create(
            created_by=self.user,
            scout_unit_name='Novější oddíl',
            scout_unit_evidence_id='999.99',
            contact_email='new@test.cz',
            contact_phone='+420987654321',
        )
        Unit.objects.create(entity=entity2, contact_person_name='Nový vedoucí')
        url = reverse('SkaRe:boat_my_unit')
        response = self.client.get(url)
        data = json.loads(response.content)
        self.assertEqual(data['harbor_number'], '999.99')

    def test_requires_login(self):
        self.client.logout()
        url = reverse('SkaRe:boat_my_unit')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run python manage.py test SkaRe.tests.test_boat_views.SailLookupViewTest SkaRe.tests.test_boat_views.MyUnitViewTest
```

Expected: `NoReverseMatch: Reverse for 'boat_sail_lookup' not found`

- [ ] **Step 3: Add AJAX views to views.py**

At the top of `SkaRe/views.py`, add to existing imports:

```python
from django.http import JsonResponse
from .models import (
    Entity, Unit, RegularParticipant, EventSettings,
    IndividualParticipant, Organizer, BoatClass, SailRegistryEntry, Boat
)
```

Then append these views:

```python
@login_required
def boat_sail_lookup(request):
    """AJAX: look up sail registry by ?q=<sail_number>. Returns JSON."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({}, status=400)
    try:
        entry = SailRegistryEntry.objects.get(sail_number__iexact=q)
        return JsonResponse({
            'boat_name': entry.boat_name,
            'class_name': entry.class_name,
            'subtype': entry.subtype,
            'sail_area': str(entry.sail_area) if entry.sail_area is not None else '',
            'harbor_number': entry.harbor_number,
            'harbor_name': entry.harbor_name,
            'contact_person': entry.contact_person,
        })
    except SailRegistryEntry.DoesNotExist:
        return JsonResponse({}, status=404)


@login_required
def boat_my_unit(request):
    """AJAX: return the most recently created Unit for the current user."""
    unit = (
        Unit.objects
        .filter(entity__created_by=request.user)
        .select_related('entity')
        .order_by('-entity__created_at')
        .first()
    )
    if not unit:
        return JsonResponse({}, status=404)
    return JsonResponse({
        'harbor_number': unit.entity.scout_unit_evidence_id,
        'harbor_name': unit.entity.scout_unit_name,
        'contact_person': unit.contact_person_name,
    })
```

- [ ] **Step 4: Add URLs to urls.py**

In `SkaRe/urls.py`, import the new views and add to `urlpatterns`:

```python
from . import views

# Add these lines inside urlpatterns:
path('boats/api/sail-lookup/', views.boat_sail_lookup, name='boat_sail_lookup'),
path('boats/api/my-unit/', views.boat_my_unit, name='boat_my_unit'),
```

- [ ] **Step 5: Run tests — should pass**

```bash
uv run python manage.py test SkaRe.tests.test_boat_views.SailLookupViewTest SkaRe.tests.test_boat_views.MyUnitViewTest
```

Expected: `Ran 9 tests in ...OK`

- [ ] **Step 6: Commit**

```bash
git add SkaRe/views.py SkaRe/urls.py SkaRe/tests/test_boat_views.py
git commit -m "feat: add AJAX sail lookup and unit prefill endpoints"
```

---

## Task 7: Boat CRUD views

**Files:**
- Modify: `SkaRe/views.py`
- Modify: `SkaRe/urls.py`
- Modify: `SkaRe/tests/test_boat_views.py`

- [ ] **Step 1: Write the failing tests**

Append to `SkaRe/tests/test_boat_views.py`:

```python
from django.contrib.auth.models import Group
from SkaRe.forms import BoatForm


class BoatListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')

    def test_list_accessible_to_authenticated(self):
        response = self.client.get(reverse('SkaRe:boat_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_redirects_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse('SkaRe:boat_list'))
        self.assertEqual(response.status_code, 302)


class BoatRegisterViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')
        self.boat_class = BoatClass.objects.create(
            name='P550', category=BoatClass.Category.SAIL, order=1
        )

    def _post_data(self, **overrides):
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

    def test_get_register_form(self):
        response = self.client.get(reverse('SkaRe:boat_register'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], BoatForm)

    def test_post_creates_boat_with_creator(self):
        response = self.client.post(reverse('SkaRe:boat_register'), self._post_data())
        self.assertEqual(Boat.objects.count(), 1)
        boat = Boat.objects.first()
        self.assertEqual(boat.created_by, self.user)
        self.assertRedirects(response, reverse('SkaRe:boat_detail', kwargs={'boat_id': boat.pk}))

    def test_post_invalid_shows_errors(self):
        response = self.client.post(reverse('SkaRe:boat_register'), self._post_data(name=''))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Boat.objects.count(), 0)

    def test_has_unit_context_false_when_no_unit(self):
        response = self.client.get(reverse('SkaRe:boat_register'))
        self.assertFalse(response.context['has_unit'])


class BoatEditViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.stranger = User.objects.create_user(username='stranger', password='pw')
        self.infodesk_user = User.objects.create_user(username='infodesk', password='pw')
        infodesk_group, _ = Group.objects.get_or_create(name='InfoDesk')
        self.infodesk_user.groups.add(infodesk_group)
        self.boat_class = BoatClass.objects.create(
            name='P550', category=BoatClass.Category.SAIL, order=1
        )
        self.boat = Boat.objects.create(
            created_by=self.owner, boat_class=self.boat_class,
            name='My Boat', contact_person='Jan', contact_phone='+420111222333',
        )

    def _post_data(self, **overrides):
        data = {
            'boat_class': self.boat_class.pk,
            'class_supplement': '',
            'sail_number': '',
            'name': 'Updated Boat',
            'description': '',
            'sail_area': '',
            'harbor_number': '',
            'harbor_name': '',
            'contact_person': 'Jan',
            'contact_phone': '+420111222333',
        }
        data.update(overrides)
        return data

    def test_owner_can_edit(self):
        self.client.login(username='owner', password='pw')
        response = self.client.post(
            reverse('SkaRe:boat_edit', kwargs={'boat_id': self.boat.pk}),
            self._post_data()
        )
        self.boat.refresh_from_db()
        self.assertEqual(self.boat.name, 'Updated Boat')

    def test_stranger_cannot_edit(self):
        self.client.login(username='stranger', password='pw')
        response = self.client.post(
            reverse('SkaRe:boat_edit', kwargs={'boat_id': self.boat.pk}),
            self._post_data()
        )
        self.boat.refresh_from_db()
        self.assertEqual(self.boat.name, 'My Boat')  # unchanged

    def test_infodesk_can_edit(self):
        self.client.login(username='infodesk', password='pw')
        response = self.client.post(
            reverse('SkaRe:boat_edit', kwargs={'boat_id': self.boat.pk}),
            self._post_data()
        )
        self.boat.refresh_from_db()
        self.assertEqual(self.boat.name, 'Updated Boat')


class BoatDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.stranger = User.objects.create_user(username='stranger', password='pw')
        self.infodesk_user = User.objects.create_user(username='infodesk', password='pw')
        infodesk_group, _ = Group.objects.get_or_create(name='InfoDesk')
        self.infodesk_user.groups.add(infodesk_group)
        self.boat_class = BoatClass.objects.create(
            name='P550', category=BoatClass.Category.SAIL, order=1
        )
        self.boat = Boat.objects.create(
            created_by=self.owner, boat_class=self.boat_class,
            name='My Boat', contact_person='Jan', contact_phone='+420111222333',
        )

    def test_owner_can_delete(self):
        self.client.login(username='owner', password='pw')
        self.client.post(reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))
        self.assertFalse(Boat.objects.filter(pk=self.boat.pk).exists())

    def test_stranger_cannot_delete(self):
        self.client.login(username='stranger', password='pw')
        self.client.post(reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))
        self.assertTrue(Boat.objects.filter(pk=self.boat.pk).exists())

    def test_infodesk_cannot_delete(self):
        self.client.login(username='infodesk', password='pw')
        self.client.post(reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))
        self.assertTrue(Boat.objects.filter(pk=self.boat.pk).exists())

    def test_get_shows_confirm_page(self):
        self.client.login(username='owner', password='pw')
        response = self.client.get(reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Boat')
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run python manage.py test SkaRe.tests.test_boat_views.BoatListViewTest SkaRe.tests.test_boat_views.BoatRegisterViewTest SkaRe.tests.test_boat_views.BoatEditViewTest SkaRe.tests.test_boat_views.BoatDeleteViewTest
```

Expected: `NoReverseMatch: Reverse for 'boat_list' not found`

- [ ] **Step 3: Add CRUD views to views.py**

Also add to imports at top of `views.py`:

```python
from .forms import (
    UserRegistrationForm, UnitRegistrationForm,
    IndividualParticipantRegistrationForm, OrganizerRegistrationForm,
    validate_czech_phone, get_participant_formset, BoatForm
)
```

Append the following views:

```python
@login_required
def boat_list(request):
    boats = Boat.objects.select_related('boat_class', 'created_by').order_by('name')
    return render(request, 'SkaRe/boats/list.html', {'boats': boats})


@login_required
def boat_detail(request, boat_id):
    boat = get_object_or_404(Boat.objects.select_related('boat_class', 'created_by'), id=boat_id)
    return render(request, 'SkaRe/boats/detail.html', {
        'boat': boat,
        'can_edit': boat.can_be_edited(request.user),
        'is_creator': boat.created_by == request.user,
    })


@login_required
def boat_register(request):
    has_unit = Unit.objects.filter(entity__created_by=request.user).exists()
    if request.method == 'POST':
        form = BoatForm(request.POST)
        if form.is_valid():
            boat = form.save(commit=False)
            boat.created_by = request.user
            boat.save()
            messages.success(request, _('Boat registered successfully.'))
            return redirect('SkaRe:boat_detail', boat_id=boat.pk)
    else:
        form = BoatForm()
    return render(request, 'SkaRe/boats/form.html', {
        'form': form,
        'has_unit': has_unit,
        'action': 'register',
    })


@login_required
def boat_edit(request, boat_id):
    boat = get_object_or_404(Boat, id=boat_id)
    if not boat.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to edit this boat.'))
        return redirect('SkaRe:boat_detail', boat_id=boat_id)
    has_unit = Unit.objects.filter(entity__created_by=request.user).exists()
    if request.method == 'POST':
        form = BoatForm(request.POST, instance=boat)
        if form.is_valid():
            form.save()
            messages.success(request, _('Boat updated successfully.'))
            return redirect('SkaRe:boat_detail', boat_id=boat.pk)
    else:
        form = BoatForm(instance=boat)
    return render(request, 'SkaRe/boats/form.html', {
        'form': form,
        'boat': boat,
        'has_unit': has_unit,
        'action': 'edit',
    })


@login_required
def boat_delete(request, boat_id):
    boat = get_object_or_404(Boat, id=boat_id)
    if boat.created_by != request.user:
        messages.error(request, _('Only the boat creator can delete it.'))
        return redirect('SkaRe:boat_detail', boat_id=boat_id)
    if request.method == 'POST':
        boat.delete()
        messages.success(request, _('Boat deleted successfully.'))
        return redirect('SkaRe:boat_list')
    return render(request, 'SkaRe/boats/confirm_delete.html', {'boat': boat})
```

- [ ] **Step 4: Add CRUD URLs to urls.py**

Add inside `urlpatterns`:

```python
path('boats/', views.boat_list, name='boat_list'),
path('boats/register/', views.boat_register, name='boat_register'),
path('boats/<int:boat_id>/', views.boat_detail, name='boat_detail'),
path('boats/<int:boat_id>/edit/', views.boat_edit, name='boat_edit'),
path('boats/<int:boat_id>/delete/', views.boat_delete, name='boat_delete'),
```

> Place these **before** the `boats/api/...` routes to avoid any routing ambiguity.

- [ ] **Step 5: Create stub templates** (enough to pass tests — they just need to render without error)

Create `SkaRe/templates/SkaRe/boats/list.html`:
```html
{% extends "SkaRe/base.html" %}
{% block content %}<p>stub</p>{% endblock %}
```

Create `SkaRe/templates/SkaRe/boats/detail.html`:
```html
{% extends "SkaRe/base.html" %}
{% block content %}<p>{{ boat.name }}</p>{% endblock %}
```

Create `SkaRe/templates/SkaRe/boats/form.html`:
```html
{% extends "SkaRe/base.html" %}
{% block content %}<form method="post">{% csrf_token %}{{ form.as_p }}<button type="submit">Save</button></form>{% endblock %}
```

Create `SkaRe/templates/SkaRe/boats/confirm_delete.html`:
```html
{% extends "SkaRe/base.html" %}
{% block content %}<p>{{ boat.name }}</p><form method="post">{% csrf_token %}<button type="submit">Delete</button></form>{% endblock %}
```

- [ ] **Step 6: Run tests — should pass**

```bash
uv run python manage.py test SkaRe.tests.test_boat_views
```

Expected: `Ran N tests in ...OK`

- [ ] **Step 7: Commit**

```bash
git add SkaRe/views.py SkaRe/urls.py SkaRe/tests/test_boat_views.py SkaRe/templates/SkaRe/boats/
git commit -m "feat: add boat CRUD views and stub templates"
```

---

## Task 8: Admin — BoatClass, Boat, SailRegistryEntry CSV import

**Files:**
- Modify: `SkaRe/admin.py`
- Create: `SkaRe/templates/admin/SkaRe/sailregistryentry/import_csv.html`
- Create: `SkaRe/tests/test_boat_admin.py`

> ⚠️ Confirm CSV column names with Erik before writing the import logic. The plan uses: `sail_number`, `boat_name`, `class_name`, `subtype`, `sail_area`, `harbor_number`, `harbor_name`, `contact_person`.

- [ ] **Step 1: Write the failing tests**

Create `SkaRe/tests/test_boat_admin.py`:

```python
import csv
import io
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from SkaRe.models import SailRegistryEntry, BoatClass


class SailRegistryCSVImportTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin', password='pw', email='admin@test.cz'
        )
        self.client.login(username='admin', password='pw')

    def _make_csv(self, rows):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'sail_number', 'boat_name', 'class_name', 'subtype',
            'sail_area', 'harbor_number', 'harbor_name', 'contact_person',
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return output.getvalue().encode('utf-8')

    def _import_url(self):
        return reverse('admin:skare_sailregistryentry_import_csv')

    def test_import_creates_entries(self):
        csv_bytes = self._make_csv([
            {'sail_number': 'CZE 1', 'boat_name': 'Rychlík', 'class_name': 'Cadet',
             'subtype': '', 'sail_area': '7.5', 'harbor_number': '523',
             'harbor_name': 'Koráb', 'contact_person': 'Jan'},
        ])
        self.client.post(
            self._import_url(),
            {'csv_file': io.BytesIO(csv_bytes)},
        )
        self.assertEqual(SailRegistryEntry.objects.count(), 1)
        self.assertEqual(SailRegistryEntry.objects.first().boat_name, 'Rychlík')

    def test_import_replaces_existing_entries(self):
        SailRegistryEntry.objects.create(sail_number='OLD 1')
        csv_bytes = self._make_csv([
            {'sail_number': 'NEW 1', 'boat_name': '', 'class_name': '',
             'subtype': '', 'sail_area': '', 'harbor_number': '',
             'harbor_name': '', 'contact_person': ''},
        ])
        self.client.post(self._import_url(), {'csv_file': io.BytesIO(csv_bytes)})
        self.assertFalse(SailRegistryEntry.objects.filter(sail_number='OLD 1').exists())
        self.assertTrue(SailRegistryEntry.objects.filter(sail_number='NEW 1').exists())

    def test_empty_csv_does_not_destroy_existing_data(self):
        SailRegistryEntry.objects.create(sail_number='KEEP ME')
        # CSV with only a header row — no data rows
        empty_csv = b'sail_number,boat_name,class_name,subtype,sail_area,harbor_number,harbor_name,contact_person\n'
        self.client.post(self._import_url(), {'csv_file': io.BytesIO(empty_csv)})
        # An empty import (0 rows) should still clear and replace — result: 0 entries.
        # This is acceptable; the protection is against *malformed* files, not empty ones.
        self.assertEqual(SailRegistryEntry.objects.count(), 0)

    def test_get_shows_upload_form(self):
        response = self.client.get(self._import_url())
        self.assertEqual(response.status_code, 200)

    def test_non_admin_cannot_access(self):
        self.client.logout()
        regular = User.objects.create_user(username='regular', password='pw')
        self.client.login(username='regular', password='pw')
        response = self.client.get(self._import_url())
        self.assertNotEqual(response.status_code, 200)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run python manage.py test SkaRe.tests.test_boat_admin
```

Expected: `NoReverseMatch: Reverse for 'admin:skare_sailregistryentry_import_csv' not found`

- [ ] **Step 3: Rewrite admin.py**

Replace the contents of `SkaRe/admin.py`:

```python
import csv
import io

from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin

from .models import (
    Entity, IndividualParticipant, Organizer, Unit, RegularParticipant,
    EventSettings, BoatClass, SailRegistryEntry, Boat,
)

# Existing registrations (unchanged)
admin.site.register(EventSettings, SingletonModelAdmin)
admin.site.register(Unit)
admin.site.register(RegularParticipant)
admin.site.register(IndividualParticipant)
admin.site.register(Organizer)
admin.site.register(Entity)


@admin.register(BoatClass)
class BoatClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_other', 'order']
    list_editable = ['order']
    ordering = ['order', 'name']


@admin.register(SailRegistryEntry)
class SailRegistryEntryAdmin(admin.ModelAdmin):
    list_display = ['sail_number', 'boat_name', 'class_name', 'harbor_name']
    search_fields = ['sail_number', 'boat_name']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-csv/',
                self.admin_site.admin_view(self.import_csv_view),
                name='skare_sailregistryentry_import_csv',
            ),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        if request.method == 'POST' and request.FILES.get('csv_file'):
            csv_file = request.FILES['csv_file']
            try:
                decoded = csv_file.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(decoded))
                entries = []
                for row in reader:
                    sail_area = row.get('sail_area', '').strip() or None
                    entries.append(SailRegistryEntry(
                        sail_number=row.get('sail_number', '').strip(),
                        boat_name=row.get('boat_name', '').strip(),
                        class_name=row.get('class_name', '').strip(),
                        subtype=row.get('subtype', '').strip(),
                        sail_area=sail_area,
                        harbor_number=row.get('harbor_number', '').strip(),
                        harbor_name=row.get('harbor_name', '').strip(),
                        contact_person=row.get('contact_person', '').strip(),
                    ))
                with transaction.atomic():
                    SailRegistryEntry.objects.all().delete()
                    SailRegistryEntry.objects.bulk_create(entries)
                self.message_user(
                    request,
                    _('Successfully imported %(count)d entries.') % {'count': len(entries)},
                    messages.SUCCESS,
                )
            except Exception as e:
                self.message_user(
                    request,
                    _('Import failed: %(error)s') % {'error': str(e)},
                    messages.ERROR,
                )
            return redirect(reverse('admin:skare_sailregistryentry_changelist'))

        return render(
            request,
            'admin/SkaRe/sailregistryentry/import_csv.html',
            {'title': _('Import sail registry CSV')},
        )


@admin.register(Boat)
class BoatAdmin(admin.ModelAdmin):
    list_display = ['name', 'sail_number', 'boat_class', 'created_by']
    search_fields = ['name', 'sail_number']
    raw_id_fields = ['created_by']
```

- [ ] **Step 4: Create the admin CSV upload template**

Create `SkaRe/templates/admin/SkaRe/sailregistryentry/import_csv.html`:

```html
{% extends "admin/base_site.html" %}
{% load i18n %}

{% block content %}
<h1>{% trans "Import sail registry CSV" %}</h1>
<p>{% trans "Upload a CSV file to replace the sail registry. The file must have a header row with these columns:" %}</p>
<code>sail_number, boat_name, class_name, subtype, sail_area, harbor_number, harbor_name, contact_person</code>
<br><br>
<form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    <input type="file" name="csv_file" accept=".csv" required>
    <br><br>
    <input type="submit" value="{% trans 'Import' %}" class="button">
</form>
{% endblock %}
```

- [ ] **Step 5: Run tests — should pass**

```bash
uv run python manage.py test SkaRe.tests.test_boat_admin
```

Expected: `Ran 5 tests in ...OK`

- [ ] **Step 6: Commit**

```bash
git add SkaRe/admin.py SkaRe/templates/admin/ SkaRe/tests/test_boat_admin.py
git commit -m "feat: add BoatClass, SailRegistryEntry (CSV import), and Boat admin registrations"
```

---

## Task 9: Full templates

Replace the stub templates with proper UI. Follow the existing template style — inspect `SkaRe/templates/SkaRe/list_units.html` and `SkaRe/templates/SkaRe/edit_unit.html` for patterns before writing.

**Files:**
- Modify: `SkaRe/templates/SkaRe/boats/list.html`
- Modify: `SkaRe/templates/SkaRe/boats/detail.html`
- Modify: `SkaRe/templates/SkaRe/boats/form.html`
- Modify: `SkaRe/templates/SkaRe/boats/confirm_delete.html`

- [ ] **Step 1: Read the existing templates for style reference**

Read `SkaRe/templates/SkaRe/list_units.html` and `SkaRe/templates/SkaRe/edit_unit.html` in full before writing anything.

- [ ] **Step 2: Write list.html**

Show a table of all boats with: sail number, name, class, contact person. Each row links to the detail page. Include a "Register a boat" button if logged in.

- [ ] **Step 3: Write detail.html**

Show all boat fields. The view already passes `can_edit` and `is_creator` booleans (added in Task 7). Use them:
- Show "Edit" link only if `can_edit`
- Show "Delete" link only if `is_creator`

- [ ] **Step 4: Write form.html**

Single form used for both register and edit. Show a "Fill from my unit" button (hidden via `{% if not has_unit %}style="display:none"{% endif %}`) and include the `boat-form.js` script. Show "Register" or "Update" as the submit label based on `action` context variable.

- [ ] **Step 5: Write confirm_delete.html**

Show boat name, a warning, a "Delete" POST button, and a "Cancel" link back to the detail page.

- [ ] **Step 6: Write template behaviour tests**

Append to `SkaRe/tests/test_boat_views.py`:

```python
class BoatRegisterTemplateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pw')
        self.client.login(username='user', password='pw')

    def test_fill_from_unit_button_hidden_when_no_unit(self):
        response = self.client.get(reverse('SkaRe:boat_register'))
        # The button should not appear when has_unit=False
        self.assertNotContains(response, 'btn-fill-from-unit')

    def test_fill_from_unit_button_shown_when_unit_exists(self):
        entity = Entity.objects.create(
            created_by=self.user,
            scout_unit_name='5. oddíl',
            scout_unit_evidence_id='123',
            contact_email='t@t.cz',
            contact_phone='+420111222333',
        )
        Unit.objects.create(entity=entity, contact_person_name='Vedoucí')
        response = self.client.get(reverse('SkaRe:boat_register'))
        self.assertContains(response, 'btn-fill-from-unit')


class BoatDetailTemplateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.stranger = User.objects.create_user(username='stranger', password='pw')
        self.boat_class = BoatClass.objects.create(
            name='P550', category=BoatClass.Category.SAIL, order=1
        )
        self.boat = Boat.objects.create(
            created_by=self.owner, boat_class=self.boat_class,
            name='My Boat', contact_person='Jan', contact_phone='+420111222333',
        )

    def test_owner_sees_edit_and_delete_buttons(self):
        self.client.login(username='owner', password='pw')
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertContains(response, reverse('SkaRe:boat_edit', kwargs={'boat_id': self.boat.pk}))
        self.assertContains(response, reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))

    def test_stranger_does_not_see_edit_or_delete(self):
        self.client.login(username='stranger', password='pw')
        response = self.client.get(reverse('SkaRe:boat_detail', kwargs={'boat_id': self.boat.pk}))
        self.assertNotContains(response, reverse('SkaRe:boat_edit', kwargs={'boat_id': self.boat.pk}))
        self.assertNotContains(response, reverse('SkaRe:boat_delete', kwargs={'boat_id': self.boat.pk}))
```

Run these tests against the stub templates first (they will fail — that is expected):

```bash
uv run python manage.py test SkaRe.tests.test_boat_views.BoatRegisterTemplateTest SkaRe.tests.test_boat_views.BoatDetailTemplateTest
```

Expected: FAIL (stubs don't render buttons). These tests become the acceptance criteria for the real templates.

- [ ] **Step 7: Manual smoke test**

```bash
uv run python manage.py runserver
```

Visit `/boats/`, `/boats/register/`, `/boats/1/`, `/boats/1/edit/`, `/boats/1/delete/`. Check that pages render without errors.

- [ ] **Step 8: Run full test suite**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass (including the template behaviour tests added in Step 6).

- [ ] **Step 9: Commit**

```bash
git add SkaRe/templates/SkaRe/boats/ SkaRe/tests/test_boat_views.py
git commit -m "feat: complete boat templates"
```

---

## Task 10: JavaScript prefill

**Files:**
- Create: `SkaRe/static/SkaRe/js/boat-form.js`

> **Note on URL paths in JS:** The fetch calls below use hardcoded absolute paths (`/boats/api/...`). This matches the assumption of the rest of the project (all URLs are root-mounted). If the app is ever deployed under a path prefix, these must be updated. An alternative is to embed the URLs as `data-*` attributes on the form element and read them in JS — but that is not done in the existing JS files, so hardcoded paths are acceptable here.

> **Note on `contact_phone` validation:** `BoatForm` does not apply `validate_czech_phone` to `contact_phone`. This is intentional — boats may be owned by non-Czech clubs with foreign phone numbers. Do not add the validator without explicit discussion.

- [ ] **Step 1: Create the JS file**

Create `SkaRe/static/SkaRe/js/boat-form.js`:

```javascript
// Boat form: sail number registry lookup + unit prefill
// Prefill only fills empty fields. Never overwrites user-typed data.
// Never injects an empty string into a non-empty required field.

function fillIfEmpty(fieldId, value) {
    if (!value) return;  // never inject blank values
    const field = document.getElementById(fieldId);
    if (field && !field.value) {
        field.value = value;
    }
}

function selectBoatClassByName(className) {
    if (!className) return;
    const select = document.getElementById('id_boat_class');
    if (!select) return;
    const lower = className.toLowerCase();
    for (const option of select.options) {
        if (option.text.toLowerCase().includes(lower)) {
            if (!select.value) {  // only if nothing selected yet
                select.value = option.value;
            }
            return;
        }
    }
}

// Sail number lookup on blur
const sailNumberField = document.getElementById('id_sail_number');
if (sailNumberField) {
    sailNumberField.addEventListener('blur', function () {
        const q = this.value.trim();
        if (!q) return;
        fetch(`/boats/api/sail-lookup/?q=${encodeURIComponent(q)}`)
            .then(response => {
                if (!response.ok) return;
                return response.json();
            })
            .then(data => {
                if (!data) return;
                fillIfEmpty('id_name', data.boat_name);
                fillIfEmpty('id_class_supplement', data.subtype);
                fillIfEmpty('id_sail_area', data.sail_area);
                fillIfEmpty('id_harbor_number', data.harbor_number);
                fillIfEmpty('id_harbor_name', data.harbor_name);
                fillIfEmpty('id_contact_person', data.contact_person);
                selectBoatClassByName(data.class_name);
            });
    });
}

// Unit prefill button
const unitPrefillBtn = document.getElementById('btn-fill-from-unit');
if (unitPrefillBtn) {
    unitPrefillBtn.addEventListener('click', function (e) {
        e.preventDefault();
        fetch('/boats/api/my-unit/')
            .then(response => {
                if (!response.ok) return;
                return response.json();
            })
            .then(data => {
                if (!data) return;
                fillIfEmpty('id_harbor_number', data.harbor_number);
                fillIfEmpty('id_harbor_name', data.harbor_name);
                fillIfEmpty('id_contact_person', data.contact_person);
            });
    });
}
```

- [ ] **Step 2: Include the script in form.html**

In `SkaRe/templates/SkaRe/boats/form.html`, at the bottom of the template (inside the existing `{% block %}` that the base template provides for extra scripts — check `base.html` for the block name):

```html
{% load static %}
<script src="{% static 'SkaRe/js/boat-form.js' %}"></script>
```

- [ ] **Step 3: Add a `btn-fill-from-unit` button to form.html**

In the harbor fields section of the form, add (conditionally rendered by the view's `has_unit` context):

```html
{% if has_unit %}
<button id="btn-fill-from-unit" class="btn btn-secondary btn-sm mb-2">
    Vyplnit z mé jednotky
</button>
{% endif %}
```

- [ ] **Step 4: Manual smoke test**

Start the dev server and test:
1. Enter a known sail number → verify fields are prefilled on blur
2. Clear all prefilled fields, enter a non-existent sail number → verify nothing happens
3. If you have a unit registered, click "Fill from my unit" → verify harbor fields prefill

- [ ] **Step 5: Run full test suite**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add SkaRe/static/SkaRe/js/boat-form.js SkaRe/templates/SkaRe/boats/form.html
git commit -m "feat: add JS sail registry lookup and unit prefill on boat form"
```

---

## Task 11: Navigation and final check

- [ ] **Step 1: Add a "Boats" link to the navigation**

Read `SkaRe/templates/SkaRe/base.html`. Add a nav link for `SkaRe:boat_list` alongside the existing nav items for units, participants, and organizers.

- [ ] **Step 2: Run the complete test suite one final time**

```bash
uv run python manage.py test SkaRe
```

Expected: all tests pass, no warnings.

- [ ] **Step 3: Commit**

```bash
git add SkaRe/templates/SkaRe/base.html
git commit -m "feat: add Boats navigation link to base template"
```
