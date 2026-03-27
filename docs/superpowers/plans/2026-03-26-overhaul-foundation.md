# PlachtIS Overhaul — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add RaceManagement group, InfoDesk permission bypass, structured dietary fields, attendance model, sail ticket model, and fix issues #34 (stable participant IDs), #41 (password UX), and #44 (evidence ID optional).

**Architecture:** Four migrations (0024–0027); two new model files (`models/attendance.py`, `models/tickets.py`); updates to `models/registration.py`, all three registration forms, all dietary-related templates, and `permissions.py`. No URL changes; no InfoDesk views in this plan — those are Plan B.

**Tech Stack:** Django 6.0, Python 3.12, `uv run python manage.py ...` for all commands.

**Starting state:** 162 tests passing. Last migration: `0023_merge_0019_hat_size_split_0022_review_fixes`.

**Spec:** `docs/superpowers/specs/2026-03-26-plachtis-overhaul-design.md` — Sections 2, 3, 6.

---

## File Map

| File | Action | Purpose |
|------|---------|---------|
| `SkaRe/migrations/0024_race_management_group.py` | Create (auto) | Data migration: create RaceManagement group |
| `SkaRe/models/registration.py` | Modify | Entity.can_be_edited: InfoDesk bypass; Person: AttendanceStatus + fields; dietary boolean fields |
| `SkaRe/permissions.py` | Modify | Add `@infodesk_required` decorator |
| `SkaRe/tests/test_permissions.py` | Modify | Tests for can_be_edited InfoDesk bypass + infodesk_required decorator |
| `SkaRe/migrations/0025_dietary_restructure.py` | Create (auto + RunPython) | Add boolean dietary fields + diet_other; copy dietary_restrictions → diet_other; remove dietary_restrictions |
| `SkaRe/forms/registration.py` | Modify | dietary_restrictions → boolean fields in RegularParticipantForm, IndividualParticipantRegistrationForm, OrganizerRegistrationForm; evidence ID optional (#44); password help text (#41) |
| `SkaRe/templates/SkaRe/registration/register_unit.html` | Modify | Dietary checkboxes in participant formset; evidence ID optional label |
| `SkaRe/templates/SkaRe/registration/edit_unit.html` | Modify | Dietary checkboxes in participant formset; evidence ID optional label |
| `SkaRe/templates/SkaRe/registration/register_individual_participant.html` | Modify | Dietary checkboxes |
| `SkaRe/templates/SkaRe/registration/edit_individual_participant.html` | Modify | Dietary checkboxes |
| `SkaRe/templates/SkaRe/registration/register_organizer.html` | Modify | Dietary checkboxes |
| `SkaRe/templates/SkaRe/registration/edit_organizer.html` | Modify | Dietary checkboxes |
| `SkaRe/templates/SkaRe/registration/list_all.html` | Modify | dietary column: show dietary_summary |
| `SkaRe/templates/SkaRe/registration/list_individual_participants.html` | Modify | dietary display: show dietary_summary |
| `SkaRe/templates/SkaRe/registration/list_organizers.html` | Modify | dietary display: show dietary_summary |
| `SkaRe/models/attendance.py` | Create | `AttendanceLog` model |
| `SkaRe/models/__init__.py` | Modify | Re-export `AttendanceLog`, `SailTicket`, `SailTicketLog` |
| `SkaRe/migrations/0026_attendance.py` | Create (auto) | Add `attendance_status`, `arrived_at`, `departed_at` to Person; create AttendanceLog table |
| `SkaRe/tests/test_attendance_models.py` | Create | AttendanceLog + Person attendance field tests |
| `SkaRe/models/tickets.py` | Create | `SailTicket` + `SailTicketLog` models |
| `SkaRe/migrations/0027_sail_tickets.py` | Create (auto) | Create SailTicket + SailTicketLog tables |
| `SkaRe/tests/test_ticket_models.py` | Create | SailTicket + SailTicketLog model tests |
| `SkaRe/views/registration.py` | Modify | Fix stable participant IDs (#34) |

---

## Task 1: RaceManagement group + Entity.can_be_edited + @infodesk_required

**Files:**
- Create: `SkaRe/migrations/0024_race_management_group.py`
- Modify: `SkaRe/models/registration.py`
- Modify: `SkaRe/permissions.py`
- Modify: `SkaRe/tests/test_permissions.py`

- [ ] **Step 1: Write failing tests for Entity.can_be_edited InfoDesk bypass and @infodesk_required**

Append to `SkaRe/tests/test_permissions.py` (after the existing `IsRaceManagementTest` class):

```python
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Group
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
        Group.objects.create(name='InfoDesk')
        self.infodesk_user.groups.add(Group.objects.get(name='InfoDesk'))

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
        Group.objects.create(name='InfoDesk')
        self.infodesk_user.groups.add(Group.objects.get(name='InfoDesk'))

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
```

Run (expected: FAIL because `infodesk_required` doesn't exist yet):

```bash
uv run python manage.py test SkaRe.tests.test_permissions --verbosity=0 2>&1 | tail -5
```

- [ ] **Step 2: Create migration 0024 (RaceManagement group)**

Create `SkaRe/migrations/0024_race_management_group.py`:

```python
from django.db import migrations


def create_race_management_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='RaceManagement')


def delete_race_management_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='RaceManagement').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('SkaRe', '0023_merge_0019_hat_size_split_0022_review_fixes'),
    ]

    operations = [
        migrations.RunPython(create_race_management_group, delete_race_management_group),
    ]
```

- [ ] **Step 3: Add @infodesk_required to permissions.py**

Replace the contents of `SkaRe/permissions.py` with:

```python
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def is_infodesk(user) -> bool:
    """Return True if the user is a member of the InfoDesk group."""
    return user.groups.filter(name='InfoDesk').exists()


def is_race_management(user) -> bool:
    """Return True if the user is a member of the RaceManagement group."""
    return user.groups.filter(name='RaceManagement').exists()


def infodesk_required(view_func):
    """Decorator: requires login AND InfoDesk group membership. Returns 403 for non-InfoDesk users."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.conf import settings as django_settings
            from django.shortcuts import redirect
            return redirect(f'{django_settings.LOGIN_URL}?next={request.path}')
        if not is_infodesk(request.user):
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)
    return wrapper
```

- [ ] **Step 4: Update Entity.can_be_edited in models/registration.py**

In `SkaRe/models/registration.py`, add the import for `is_infodesk` at the top (after the existing imports):

```python
from ..permissions import is_infodesk
```

Then replace the existing `can_be_edited` method on `Entity` (lines ~323–337) with:

```python
def can_be_edited(self, user):
    """Check if this entity can be edited by the given user.

    InfoDesk members bypass ownership and deadline checks entirely.
    """
    if is_infodesk(user):
        return True
    is_owner = self.created_by == user
    is_editor = self.editors.filter(id=user.id).exists()
    if not (is_owner or is_editor):
        return False
    return EventSettings.is_editing_open() or self.unlocked_for_editing
```

- [ ] **Step 5: Run tests**

```bash
uv run python manage.py test SkaRe --verbosity=0 2>&1 | tail -5
```

Expected: all tests pass (baseline 162 + new tests).

- [ ] **Step 6: Commit**

```bash
git add SkaRe/migrations/0024_race_management_group.py \
        SkaRe/models/registration.py \
        SkaRe/permissions.py \
        SkaRe/tests/test_permissions.py
git commit -m "feat: add RaceManagement group, InfoDesk bypass in Entity.can_be_edited, @infodesk_required decorator"
```

---

## Task 2: Dietary restrictions restructure

**Files:**
- Modify: `SkaRe/models/registration.py`
- Create: `SkaRe/migrations/0025_dietary_restructure.py` (via makemigrations then customised)
- Modify: `SkaRe/forms/registration.py`
- Modify: 8 templates

- [ ] **Step 1: Write failing model tests**

Create `SkaRe/tests/test_registration_models.py`:

```python
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
            'diet_vegan', 'diet_vegetarian', 'diet_gluten_free',
            'diet_lactose_free', 'diet_no_eggs', 'diet_no_peanuts',
            'diet_no_tree_nuts', 'diet_no_soy', 'diet_no_fish', 'diet_no_fruits',
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
```

Run (expected FAIL — fields don't exist yet):

```bash
uv run python manage.py test SkaRe.tests.test_registration_models --verbosity=0 2>&1 | tail -5
```

- [ ] **Step 2: Add dietary fields to Person in models/registration.py**

In `SkaRe/models/registration.py`, inside the `Person` class, **replace** the `dietary_restrictions` field:

```python
dietary_restrictions = models.TextField(
    blank=True, help_text=_("Any dietary restrictions or preferences"),
    verbose_name=_("Dietary restrictions")
)
```

with these 11 fields (place them at the same location):

```python
# Dietary preferences
diet_vegan = models.BooleanField(default=False, verbose_name=_('Vegan'))
diet_vegetarian = models.BooleanField(default=False, verbose_name=_('Vegetarian'))

# Major allergens / exclusions
diet_gluten_free = models.BooleanField(default=False, verbose_name=_('Gluten-free'))
diet_lactose_free = models.BooleanField(default=False, verbose_name=_('Lactose/dairy-free'))
diet_no_eggs = models.BooleanField(default=False, verbose_name=_('No eggs'))
diet_no_peanuts = models.BooleanField(default=False, verbose_name=_('No peanuts'))
diet_no_tree_nuts = models.BooleanField(default=False, verbose_name=_('No tree nuts'))
diet_no_soy = models.BooleanField(default=False, verbose_name=_('No soy'))
diet_no_fish = models.BooleanField(default=False, verbose_name=_('No fish'))
diet_no_fruits = models.BooleanField(default=False, verbose_name=_('No fruits'))

# Catch-all
diet_other = models.TextField(blank=True, verbose_name=_('Other dietary restrictions'))
```

Also add the `dietary_summary` method to `Person` (after the `save()` method):

```python
def dietary_summary(self) -> str:
    """Return a comma-separated string of active dietary restrictions."""
    parts = []
    flag_labels = [
        ('diet_vegan', 'Vegan'),
        ('diet_vegetarian', 'Vegetarian'),
        ('diet_gluten_free', 'Gluten-free'),
        ('diet_lactose_free', 'Lactose/dairy-free'),
        ('diet_no_eggs', 'No eggs'),
        ('diet_no_peanuts', 'No peanuts'),
        ('diet_no_tree_nuts', 'No tree nuts'),
        ('diet_no_soy', 'No soy'),
        ('diet_no_fish', 'No fish'),
        ('diet_no_fruits', 'No fruits'),
    ]
    for field, label in flag_labels:
        if getattr(self, field):
            parts.append(label)
    if self.diet_other:
        parts.append(self.diet_other)
    return ', '.join(parts)
```

- [ ] **Step 3: Generate migration skeleton**

```bash
uv run python manage.py makemigrations SkaRe --name dietary_restructure
```

This will generate a migration that adds the new fields and removes `dietary_restrictions`. Open the generated file (`SkaRe/migrations/0025_dietary_restructure.py`) and **add a RunPython data migration step between** the add-fields operation and the remove-field operation. The final migration operations list should be:

```python
operations = [
    # 1. Add new fields (generated by makemigrations — keep as-is)
    migrations.AddField(model_name='person', name='diet_vegan', ...),
    migrations.AddField(model_name='person', name='diet_vegetarian', ...),
    migrations.AddField(model_name='person', name='diet_gluten_free', ...),
    migrations.AddField(model_name='person', name='diet_lactose_free', ...),
    migrations.AddField(model_name='person', name='diet_no_eggs', ...),
    migrations.AddField(model_name='person', name='diet_no_peanuts', ...),
    migrations.AddField(model_name='person', name='diet_no_tree_nuts', ...),
    migrations.AddField(model_name='person', name='diet_no_soy', ...),
    migrations.AddField(model_name='person', name='diet_no_fish', ...),
    migrations.AddField(model_name='person', name='diet_no_fruits', ...),
    migrations.AddField(model_name='person', name='diet_other', ...),
    # 2. Copy existing data
    migrations.RunPython(copy_dietary_data, migrations.RunPython.noop),
    # 3. Remove old field (generated by makemigrations — keep as-is)
    migrations.RemoveField(model_name='person', name='dietary_restrictions'),
]
```

Add this function above the `Migration` class in the migration file:

```python
def copy_dietary_data(apps, schema_editor):
    Person = apps.get_model('SkaRe', 'Person')
    Person.objects.exclude(dietary_restrictions='').update(
        diet_other=models.F('dietary_restrictions')
    )
```

Also add `from django.db import models` at the top of the migration file if it is not already there.

- [ ] **Step 4: Run model tests**

```bash
uv run python manage.py test SkaRe.tests.test_registration_models --verbosity=0 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 5: Update RegularParticipantForm in forms/registration.py**

In `SkaRe/forms/registration.py`, replace the `RegularParticipantForm.Meta.fields` and `widgets` to remove `dietary_restrictions` and add the new dietary fields:

```python
class Meta:
    model = RegularParticipant
    fields = [
        'first_name',
        'last_name',
        'nickname',
        'date_of_birth',
        'health_restrictions',
        'diet_vegan',
        'diet_vegetarian',
        'diet_gluten_free',
        'diet_lactose_free',
        'diet_no_eggs',
        'diet_no_peanuts',
        'diet_no_tree_nuts',
        'diet_no_soy',
        'diet_no_fish',
        'diet_no_fruits',
        'diet_other',
        'relevant_information',
    ]
    widgets = {
        'first_name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _('First name')}),
        'last_name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _('Last name')}),
        'nickname': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _('Nickname')}),
        'date_of_birth': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}, format='%Y-%m-%d'),
        'health_restrictions': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': _('e.g. Anxiety, asthma')}),
        'diet_vegan': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'diet_vegetarian': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'diet_gluten_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'diet_lactose_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'diet_no_eggs': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'diet_no_peanuts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'diet_no_tree_nuts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'diet_no_soy': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'diet_no_fish': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'diet_no_fruits': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'diet_other': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _('Other restrictions')}),
        'relevant_information': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': _('e.g. Special needs')}),
    }
```

- [ ] **Step 6: Update IndividualParticipantRegistrationForm in forms/registration.py**

Replace `'dietary_restrictions'` in `Meta.fields` with the new fields list, and update `widgets` similarly. In `Meta.fields`, replace the single `'dietary_restrictions'` entry with:

```python
'diet_vegan',
'diet_vegetarian',
'diet_gluten_free',
'diet_lactose_free',
'diet_no_eggs',
'diet_no_peanuts',
'diet_no_tree_nuts',
'diet_no_soy',
'diet_no_fish',
'diet_no_fruits',
'diet_other',
```

In `widgets`, remove the `'dietary_restrictions'` entry and add:

```python
'diet_vegan': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
'diet_vegetarian': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
'diet_gluten_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
'diet_lactose_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
'diet_no_eggs': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
'diet_no_peanuts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
'diet_no_tree_nuts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
'diet_no_soy': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
'diet_no_fish': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
'diet_no_fruits': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
'diet_other': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Other restrictions')}),
```

- [ ] **Step 7: Update OrganizerRegistrationForm in forms/registration.py**

Same substitution as Step 6: replace `'dietary_restrictions'` in `Meta.fields` with the 11 new fields, and update `widgets` identically to Step 6.

- [ ] **Step 8: Update register_unit.html and edit_unit.html (participant formset)**

Both templates have a participant formset rendered as a table. Each table row renders formset form fields. There is also a JavaScript `__prefix__` row used as the template for dynamically-added rows.

**In both templates**, find the table cell containing `dietary_restrictions` (grep for `dietary_restrictions` in each file to locate it). Replace that single `<td>` with this compact multi-checkbox cell:

```html
<td>
    <div class="small">
        <div class="form-check form-check-inline">
            <input type="checkbox" name="{{ form.diet_vegan.html_name }}" id="{{ form.diet_vegan.id_for_label }}" class="form-check-input"{% if form.diet_vegan.value %} checked{% endif %}>
            <label class="form-check-label" for="{{ form.diet_vegan.id_for_label }}">{% trans "Vegan" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="{{ form.diet_vegetarian.html_name }}" id="{{ form.diet_vegetarian.id_for_label }}" class="form-check-input"{% if form.diet_vegetarian.value %} checked{% endif %}>
            <label class="form-check-label" for="{{ form.diet_vegetarian.id_for_label }}">{% trans "Vegetarian" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="{{ form.diet_gluten_free.html_name }}" id="{{ form.diet_gluten_free.id_for_label }}" class="form-check-input"{% if form.diet_gluten_free.value %} checked{% endif %}>
            <label class="form-check-label" for="{{ form.diet_gluten_free.id_for_label }}">{% trans "Gluten-free" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="{{ form.diet_lactose_free.html_name }}" id="{{ form.diet_lactose_free.id_for_label }}" class="form-check-input"{% if form.diet_lactose_free.value %} checked{% endif %}>
            <label class="form-check-label" for="{{ form.diet_lactose_free.id_for_label }}">{% trans "Lactose-free" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="{{ form.diet_no_eggs.html_name }}" id="{{ form.diet_no_eggs.id_for_label }}" class="form-check-input"{% if form.diet_no_eggs.value %} checked{% endif %}>
            <label class="form-check-label" for="{{ form.diet_no_eggs.id_for_label }}">{% trans "No eggs" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="{{ form.diet_no_peanuts.html_name }}" id="{{ form.diet_no_peanuts.id_for_label }}" class="form-check-input"{% if form.diet_no_peanuts.value %} checked{% endif %}>
            <label class="form-check-label" for="{{ form.diet_no_peanuts.id_for_label }}">{% trans "No peanuts" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="{{ form.diet_no_tree_nuts.html_name }}" id="{{ form.diet_no_tree_nuts.id_for_label }}" class="form-check-input"{% if form.diet_no_tree_nuts.value %} checked{% endif %}>
            <label class="form-check-label" for="{{ form.diet_no_tree_nuts.id_for_label }}">{% trans "No tree nuts" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="{{ form.diet_no_soy.html_name }}" id="{{ form.diet_no_soy.id_for_label }}" class="form-check-input"{% if form.diet_no_soy.value %} checked{% endif %}>
            <label class="form-check-label" for="{{ form.diet_no_soy.id_for_label }}">{% trans "No soy" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="{{ form.diet_no_fish.html_name }}" id="{{ form.diet_no_fish.id_for_label }}" class="form-check-input"{% if form.diet_no_fish.value %} checked{% endif %}>
            <label class="form-check-label" for="{{ form.diet_no_fish.id_for_label }}">{% trans "No fish" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="{{ form.diet_no_fruits.html_name }}" id="{{ form.diet_no_fruits.id_for_label }}" class="form-check-input"{% if form.diet_no_fruits.value %} checked{% endif %}>
            <label class="form-check-label" for="{{ form.diet_no_fruits.id_for_label }}">{% trans "No fruits" %}</label>
        </div>
        <input type="text" name="{{ form.diet_other.html_name }}" id="{{ form.diet_other.id_for_label }}"
               class="form-control form-control-sm mt-1"
               placeholder="{% trans 'Other' %}"
               value="{{ form.diet_other.value|default:'' }}">
    </div>
</td>
```

For the `__prefix__` static HTML template row at the bottom of each template (the JavaScript-cloning template), replace the `dietary_restrictions` `<td>` with the same structure but use hardcoded `__prefix__` names:

```html
<td>
    <div class="small">
        <div class="form-check form-check-inline">
            <input type="checkbox" name="participants-__prefix__-diet_vegan" id="id_participants-__prefix__-diet_vegan" class="form-check-input">
            <label class="form-check-label" for="id_participants-__prefix__-diet_vegan">{% trans "Vegan" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="participants-__prefix__-diet_vegetarian" id="id_participants-__prefix__-diet_vegetarian" class="form-check-input">
            <label class="form-check-label" for="id_participants-__prefix__-diet_vegetarian">{% trans "Vegetarian" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="participants-__prefix__-diet_gluten_free" id="id_participants-__prefix__-diet_gluten_free" class="form-check-input">
            <label class="form-check-label" for="id_participants-__prefix__-diet_gluten_free">{% trans "Gluten-free" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="participants-__prefix__-diet_lactose_free" id="id_participants-__prefix__-diet_lactose_free" class="form-check-input">
            <label class="form-check-label" for="id_participants-__prefix__-diet_lactose_free">{% trans "Lactose-free" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="participants-__prefix__-diet_no_eggs" id="id_participants-__prefix__-diet_no_eggs" class="form-check-input">
            <label class="form-check-label" for="id_participants-__prefix__-diet_no_eggs">{% trans "No eggs" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="participants-__prefix__-diet_no_peanuts" id="id_participants-__prefix__-diet_no_peanuts" class="form-check-input">
            <label class="form-check-label" for="id_participants-__prefix__-diet_no_peanuts">{% trans "No peanuts" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="participants-__prefix__-diet_no_tree_nuts" id="id_participants-__prefix__-diet_no_tree_nuts" class="form-check-input">
            <label class="form-check-label" for="id_participants-__prefix__-diet_no_tree_nuts">{% trans "No tree nuts" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="participants-__prefix__-diet_no_soy" id="id_participants-__prefix__-diet_no_soy" class="form-check-input">
            <label class="form-check-label" for="id_participants-__prefix__-diet_no_soy">{% trans "No soy" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="participants-__prefix__-diet_no_fish" id="id_participants-__prefix__-diet_no_fish" class="form-check-input">
            <label class="form-check-label" for="id_participants-__prefix__-diet_no_fish">{% trans "No fish" %}</label>
        </div>
        <div class="form-check form-check-inline">
            <input type="checkbox" name="participants-__prefix__-diet_no_fruits" id="id_participants-__prefix__-diet_no_fruits" class="form-check-input">
            <label class="form-check-label" for="id_participants-__prefix__-diet_no_fruits">{% trans "No fruits" %}</label>
        </div>
        <input type="text" name="participants-__prefix__-diet_other" id="id_participants-__prefix__-diet_other"
               class="form-control form-control-sm mt-1" placeholder="{% trans 'Other' %}">
    </div>
</td>
```

- [ ] **Step 9: Update dietary section in individual participant and organizer templates**

In each of these 4 templates, find the block that renders `dietary_restrictions` (grep for `dietary_restrictions` in each to locate it). Replace the entire field block (label + widget + error display) with this reusable block:

```html
<div class="mb-3">
    <label class="form-label">{% trans "Dietary restrictions" %}</label>
    <div class="row row-cols-2 g-1 mb-2">
        <div class="col">
            <div class="form-check">
                {{ form.diet_vegan }} <label class="form-check-label" for="{{ form.diet_vegan.id_for_label }}">{% trans "Vegan" %}</label>
            </div>
        </div>
        <div class="col">
            <div class="form-check">
                {{ form.diet_vegetarian }} <label class="form-check-label" for="{{ form.diet_vegetarian.id_for_label }}">{% trans "Vegetarian" %}</label>
            </div>
        </div>
        <div class="col">
            <div class="form-check">
                {{ form.diet_gluten_free }} <label class="form-check-label" for="{{ form.diet_gluten_free.id_for_label }}">{% trans "Gluten-free" %}</label>
            </div>
        </div>
        <div class="col">
            <div class="form-check">
                {{ form.diet_lactose_free }} <label class="form-check-label" for="{{ form.diet_lactose_free.id_for_label }}">{% trans "Lactose/dairy-free" %}</label>
            </div>
        </div>
        <div class="col">
            <div class="form-check">
                {{ form.diet_no_eggs }} <label class="form-check-label" for="{{ form.diet_no_eggs.id_for_label }}">{% trans "No eggs" %}</label>
            </div>
        </div>
        <div class="col">
            <div class="form-check">
                {{ form.diet_no_peanuts }} <label class="form-check-label" for="{{ form.diet_no_peanuts.id_for_label }}">{% trans "No peanuts" %}</label>
            </div>
        </div>
        <div class="col">
            <div class="form-check">
                {{ form.diet_no_tree_nuts }} <label class="form-check-label" for="{{ form.diet_no_tree_nuts.id_for_label }}">{% trans "No tree nuts" %}</label>
            </div>
        </div>
        <div class="col">
            <div class="form-check">
                {{ form.diet_no_soy }} <label class="form-check-label" for="{{ form.diet_no_soy.id_for_label }}">{% trans "No soy" %}</label>
            </div>
        </div>
        <div class="col">
            <div class="form-check">
                {{ form.diet_no_fish }} <label class="form-check-label" for="{{ form.diet_no_fish.id_for_label }}">{% trans "No fish" %}</label>
            </div>
        </div>
        <div class="col">
            <div class="form-check">
                {{ form.diet_no_fruits }} <label class="form-check-label" for="{{ form.diet_no_fruits.id_for_label }}">{% trans "No fruits" %}</label>
            </div>
        </div>
    </div>
    {{ form.diet_other }}
    {% if form.diet_other.errors %}
        <div class="text-danger">{{ form.diet_other.errors }}</div>
    {% endif %}
</div>
```

The four templates are:
- `SkaRe/templates/SkaRe/registration/register_individual_participant.html`
- `SkaRe/templates/SkaRe/registration/edit_individual_participant.html`
- `SkaRe/templates/SkaRe/registration/register_organizer.html`
- `SkaRe/templates/SkaRe/registration/edit_organizer.html`

Note: in the edit templates, the form variable may be named `participant_form` or `organizer_form` instead of `form` — check each template before editing and use the correct variable name.

- [ ] **Step 10: Update list templates**

**`list_all.html`**: find `p.dietary_restrictions|default:"-"|truncatewords:10` (there are 3 occurrences, one per person type section). Replace each with `p.dietary_summary|default:"-"|truncatewords:10`.

**`list_individual_participants.html`**: find the block `{% if participant.dietary_restrictions %}...{{ participant.dietary_restrictions }}...{% endif %}`. Replace with `{% if participant.dietary_summary %}...{{ participant.dietary_summary }}...{% endif %}`.

**`list_organizers.html`**: same substitution using `organizer.dietary_summary` instead of `organizer.dietary_restrictions`.

- [ ] **Step 11: Run full test suite**

```bash
uv run python manage.py test SkaRe --verbosity=0 2>&1 | tail -5
```

Expected: all tests pass.

- [ ] **Step 12: Commit**

```bash
git add SkaRe/models/registration.py \
        SkaRe/migrations/0025_dietary_restructure.py \
        SkaRe/forms/registration.py \
        SkaRe/tests/test_registration_models.py \
        SkaRe/templates/SkaRe/registration/
git commit -m "feat: replace dietary_restrictions TextField with structured boolean fields on Person (migration 0025)"
```

---

## Task 3: Attendance model

**Files:**
- Modify: `SkaRe/models/registration.py`
- Create: `SkaRe/models/attendance.py`
- Modify: `SkaRe/models/__init__.py`
- Create: `SkaRe/migrations/0026_attendance.py` (auto)
- Create: `SkaRe/tests/test_attendance_models.py`

- [ ] **Step 1: Write failing tests**

Create `SkaRe/tests/test_attendance_models.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from SkaRe.models import RegularParticipant, Unit, Entity, AttendanceLog
from datetime import date


def _make_unit(user):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='u@example.com',
        contact_phone='123456789',
    )
    return Unit.objects.create(entity=entity, contact_person_name='Leader')


def _make_person(unit):
    return RegularParticipant.objects.create(
        unit=unit,
        first_name='Jan',
        last_name='Novak',
        date_of_birth=date(2000, 1, 1),
    )


class PersonAttendanceFieldsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.unit = _make_unit(self.user)
        self.person = _make_person(self.unit)

    def test_attendance_status_defaults_to_expected(self):
        from SkaRe.models import Person
        self.assertEqual(self.person.attendance_status, Person.AttendanceStatus.EXPECTED)

    def test_arrived_at_is_null_by_default(self):
        self.assertIsNone(self.person.arrived_at)

    def test_departed_at_is_null_by_default(self):
        self.assertIsNone(self.person.departed_at)

    def test_attendance_status_can_be_set_to_arrived(self):
        from SkaRe.models import Person
        self.person.attendance_status = Person.AttendanceStatus.ARRIVED
        self.person.arrived_at = timezone.now()
        self.person.save()
        self.person.refresh_from_db()
        self.assertEqual(self.person.attendance_status, 'arrived')
        self.assertIsNotNone(self.person.arrived_at)


class AttendanceLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.staff = User.objects.create_user(username='staff', password='pw')
        self.unit = _make_unit(self.user)
        self.person = _make_person(self.unit)

    def test_can_create_log_entry(self):
        from SkaRe.models import Person
        log = AttendanceLog.objects.create(
            person=self.person,
            status=Person.AttendanceStatus.ARRIVED,
            changed_by=self.staff,
        )
        self.assertEqual(log.status, 'arrived')
        self.assertEqual(log.person, self.person)

    def test_note_defaults_to_empty(self):
        from SkaRe.models import Person
        log = AttendanceLog.objects.create(
            person=self.person,
            status=Person.AttendanceStatus.EXPECTED,
            changed_by=None,
        )
        self.assertEqual(log.note, '')

    def test_changed_at_is_set_automatically(self):
        from SkaRe.models import Person
        log = AttendanceLog.objects.create(
            person=self.person,
            status=Person.AttendanceStatus.ARRIVED,
            changed_by=self.staff,
        )
        self.assertIsNotNone(log.changed_at)

    def test_person_has_attendance_logs_reverse_relation(self):
        from SkaRe.models import Person
        AttendanceLog.objects.create(
            person=self.person,
            status=Person.AttendanceStatus.ARRIVED,
            changed_by=self.staff,
        )
        self.assertEqual(self.person.attendance_logs.count(), 1)
```

Run (expected FAIL — AttendanceLog doesn't exist yet):

```bash
uv run python manage.py test SkaRe.tests.test_attendance_models --verbosity=0 2>&1 | tail -5
```

- [ ] **Step 2: Add AttendanceStatus + attendance fields to Person**

In `SkaRe/models/registration.py`, inside the `Person` class, add the `AttendanceStatus` inner class and attendance fields. Place them after the existing `visible_to` field and before `calculate_category`:

```python
class AttendanceStatus(models.TextChoices):
    EXPECTED   = 'expected',   _('Expected')
    ARRIVED    = 'arrived',    _('Arrived')
    DEPARTED   = 'departed',   _('Departed')
    NOT_COMING = 'not_coming', _('Not coming')

attendance_status = models.CharField(
    max_length=20,
    choices=AttendanceStatus.choices,
    default=AttendanceStatus.EXPECTED,
    verbose_name=_('Attendance status'),
)
arrived_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Arrived at'))
departed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Departed at'))
```

- [ ] **Step 3: Create models/attendance.py**

Create `SkaRe/models/attendance.py`:

```python
from django.db import models
from django.contrib.auth.models import User
from .registration import Person


class AttendanceLog(models.Model):
    """Records each change to a person's attendance status."""

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='attendance_logs',
    )
    status = models.CharField(
        max_length=20,
        choices=Person.AttendanceStatus.choices,
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.person} → {self.status} at {self.changed_at}'
```

- [ ] **Step 4: Update models/__init__.py**

Add `AttendanceLog` to the imports in `SkaRe/models/__init__.py`:

```python
from .registration import (
    validate_date_of_birth,
    EventSettings,
    Person,
    Entity,
    Unit,
    RegularParticipant,
    IndividualParticipant,
    Organizer,
)
from .boats import BoatClass, Boat, Crew, CrewMember
from .attendance import AttendanceLog
```

- [ ] **Step 5: Generate migration 0026**

```bash
uv run python manage.py makemigrations SkaRe --name attendance
```

Verify the generated migration:
- Adds `attendance_status`, `arrived_at`, `departed_at` to `SkaRe_person`
- Creates the `SkaRe_attendancelog` table
- Depends on `0025_dietary_restructure`

- [ ] **Step 6: Run tests**

```bash
uv run python manage.py test SkaRe --verbosity=0 2>&1 | tail -5
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/models/registration.py \
        SkaRe/models/attendance.py \
        SkaRe/models/__init__.py \
        SkaRe/migrations/0026_attendance.py \
        SkaRe/tests/test_attendance_models.py
git commit -m "feat: add attendance status fields to Person and AttendanceLog model (migration 0026)"
```

---

## Task 4: Sail Ticket models

**Files:**
- Create: `SkaRe/models/tickets.py`
- Modify: `SkaRe/models/__init__.py`
- Create: `SkaRe/migrations/0027_sail_tickets.py` (auto)
- Create: `SkaRe/tests/test_ticket_models.py`

- [ ] **Step 1: Write failing tests**

Create `SkaRe/tests/test_ticket_models.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from SkaRe.models import SailTicket, SailTicketLog, Boat, BoatClass


def _make_boat(user):
    bc = BoatClass.objects.create(name='P550', category=BoatClass.Category.SAIL, order=1)
    return Boat.objects.create(
        created_by=user,
        boat_class=bc,
        name='Albatros',
        contact_person='Jan',
        contact_phone='123456789',
    )


class SailTicketTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.boat = _make_boat(self.user)

    def test_status_defaults_to_ashore(self):
        ticket = SailTicket.objects.create(
            code='P550-001',
            color=SailTicket.Color.P550,
        )
        self.assertEqual(ticket.status, SailTicket.Status.ASHORE)

    def test_pending_pairing_defaults_to_false(self):
        ticket = SailTicket.objects.create(code='P550-002', color=SailTicket.Color.P550)
        self.assertFalse(ticket.pending_pairing)

    def test_rfid_uid_blank_by_default(self):
        ticket = SailTicket.objects.create(code='P550-003', color=SailTicket.Color.P550)
        self.assertEqual(ticket.rfid_uid, '')

    def test_boat_can_be_assigned(self):
        ticket = SailTicket.objects.create(
            code='P550-004',
            color=SailTicket.Color.P550,
            boat=self.boat,
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.boat, self.boat)

    def test_boat_fk_nulls_on_boat_deletion(self):
        ticket = SailTicket.objects.create(
            code='P550-005',
            color=SailTicket.Color.P550,
            boat=self.boat,
        )
        self.boat.delete()
        ticket.refresh_from_db()
        self.assertIsNone(ticket.boat)

    def test_code_is_unique(self):
        from django.db import IntegrityError
        SailTicket.objects.create(code='UNIQUE-001', color=SailTicket.Color.SPARE)
        with self.assertRaises(IntegrityError):
            SailTicket.objects.create(code='UNIQUE-001', color=SailTicket.Color.SPARE)


class SailTicketLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.ticket = SailTicket.objects.create(code='SAIL-001', color=SailTicket.Color.SAIL)

    def test_can_create_log_entry(self):
        log = SailTicketLog.objects.create(
            ticket=self.ticket,
            status=SailTicket.Status.ON_WATER,
            changed_by=self.user,
        )
        self.assertEqual(log.status, 'on_water')

    def test_note_defaults_to_empty(self):
        log = SailTicketLog.objects.create(
            ticket=self.ticket,
            status=SailTicket.Status.ASHORE,
            changed_by=None,
        )
        self.assertEqual(log.note, '')

    def test_ticket_has_logs_reverse_relation(self):
        SailTicketLog.objects.create(
            ticket=self.ticket,
            status=SailTicket.Status.ON_WATER,
            changed_by=self.user,
        )
        self.assertEqual(self.ticket.logs.count(), 1)
```

Run (expected FAIL — SailTicket doesn't exist yet):

```bash
uv run python manage.py test SkaRe.tests.test_ticket_models --verbosity=0 2>&1 | tail -5
```

- [ ] **Step 2: Create models/tickets.py**

Create `SkaRe/models/tickets.py`:

```python
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .boats import Boat


class SailTicket(models.Model):
    """A physical sail ticket assigned to a boat for on-water tracking."""

    class Color(models.TextChoices):
        P550  = 'p550',  _('P550')
        SAIL  = 'sail',  _('Sailboat')
        OTHER = 'other', _('Other boat')
        SPARE = 'spare', _('Spare')

    class Status(models.TextChoices):
        ASHORE   = 'ashore',   _('Ashore')
        ON_WATER = 'on_water', _('On water')
        LOST     = 'lost',     _('Lost')

    code = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=10, choices=Color.choices)
    rfid_uid = models.CharField(max_length=100, blank=True)
    boat = models.ForeignKey(
        Boat,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sail_tickets',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ASHORE,
    )
    pending_pairing = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} ({self.color})'


class SailTicketLog(models.Model):
    """Immutable log of every status change for a SailTicket."""

    ticket = models.ForeignKey(
        SailTicket,
        on_delete=models.CASCADE,
        related_name='logs',
    )
    status = models.CharField(max_length=20, choices=SailTicket.Status.choices)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.ticket.code} → {self.status} at {self.changed_at}'
```

- [ ] **Step 3: Update models/__init__.py**

Add `SailTicket` and `SailTicketLog` to the imports:

```python
from .registration import (
    validate_date_of_birth,
    EventSettings,
    Person,
    Entity,
    Unit,
    RegularParticipant,
    IndividualParticipant,
    Organizer,
)
from .boats import BoatClass, Boat, Crew, CrewMember
from .attendance import AttendanceLog
from .tickets import SailTicket, SailTicketLog
```

- [ ] **Step 4: Generate migration 0027**

```bash
uv run python manage.py makemigrations SkaRe --name sail_tickets
```

Verify the generated migration creates `SkaRe_sailticket` and `SkaRe_sailticketlog` tables and depends on `0026_attendance`.

- [ ] **Step 5: Run tests**

```bash
uv run python manage.py test SkaRe --verbosity=0 2>&1 | tail -5
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add SkaRe/models/tickets.py \
        SkaRe/models/__init__.py \
        SkaRe/migrations/0027_sail_tickets.py \
        SkaRe/tests/test_ticket_models.py
git commit -m "feat: add SailTicket and SailTicketLog models (migration 0027)"
```

---

## Task 5: Bug fixes — stable participant IDs (#34), password UX (#41), evidence ID optional (#44)

**Files:**
- Modify: `SkaRe/views/registration.py`
- Modify: `SkaRe/forms/registration.py`
- Modify: `SkaRe/templates/SkaRe/registration/register_unit.html`
- Modify: `SkaRe/templates/SkaRe/registration/edit_unit.html`

### Fix #34 — Stable RegularParticipant IDs

The formset must update existing participants in place rather than deleting and recreating them. The root fix is ensuring that `formset.save()` is called (not just `save(commit=False)`) and that `save_m2m()` is handled. The current code uses `save(commit=False)` and manually saves instances, which correctly preserves PKs for existing instances. However, the `participant_count` message is misleading — it counts only changed/new participants, not total. The real issue is that unchanged existing participants (those not in `instances`) do not have `unit` reassigned. For a first save after unit creation this doesn't matter, but for edits it could if somehow instance.unit is None. Verify and add a test.

- [ ] **Step 1: Write the regression test for stable IDs**

Append to `SkaRe/tests/test_registration_views.py` (create the file if it doesn't exist — read it first if it does):

```python
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from SkaRe.models import Entity, Unit, RegularParticipant, EventSettings
from django.utils import timezone
from datetime import timedelta, date


class StableParticipantIdTest(TestCase):
    """Issue #34: Saving a unit must not delete and recreate participants."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='owner', password='pw')
        self.client.login(username='owner', password='pw')

        # Open editing
        settings = EventSettings.get_solo()
        settings.editing_deadline = timezone.now() + timedelta(hours=1)
        settings.save()

        # Create a unit with two participants
        entity = Entity.objects.create(
            created_by=self.user,
            contact_email='t@example.com',
            contact_phone='123456789',
        )
        self.unit = Unit.objects.create(entity=entity, contact_person_name='Leader')
        self.p1 = RegularParticipant.objects.create(
            unit=self.unit,
            first_name='Alice',
            last_name='Smith',
            date_of_birth=date(2000, 1, 1),
        )
        self.p2 = RegularParticipant.objects.create(
            unit=self.unit,
            first_name='Bob',
            last_name='Jones',
            date_of_birth=date(2001, 6, 15),
        )
        self.original_p1_pk = self.p1.pk
        self.original_p2_pk = self.p2.pk

    def test_participant_ids_unchanged_after_edit(self):
        url = reverse('SkaRe:edit_unit', kwargs={'pk': self.unit.entity.pk})
        data = {
            # Entity fields
            'scout_unit_name': 'Test Unit',
            'scout_unit_evidence_id': '523.10',
            'contact_email': 't@example.com',
            'contact_phone': '123456789',
            # Unit fields
            'contact_person_name': 'Leader',
            'backup_contact_phone': '',
            'boats_p550': '0', 'boats_sail': '0', 'boats_paddle': '0', 'boats_motor': '0',
            'scarf_count': '0', 'hat_count': '0', 'small_hat_count': '0',
            'accommodation_expectations': '', 'estimated_accommodation_area': '',
            # Formset management
            'participants-TOTAL_FORMS': '2',
            'participants-INITIAL_FORMS': '2',
            'participants-MIN_NUM_FORMS': '0',
            'participants-MAX_NUM_FORMS': '1000',
            # Existing participant 0
            f'participants-0-id': str(self.p1.pk),
            f'participants-0-first_name': 'Alice',
            f'participants-0-last_name': 'Smith',
            f'participants-0-date_of_birth': '2000-01-01',
            f'participants-0-nickname': '',
            f'participants-0-health_restrictions': '',
            f'participants-0-diet_vegan': '',
            f'participants-0-diet_vegetarian': '',
            f'participants-0-diet_gluten_free': '',
            f'participants-0-diet_lactose_free': '',
            f'participants-0-diet_no_eggs': '',
            f'participants-0-diet_no_peanuts': '',
            f'participants-0-diet_no_tree_nuts': '',
            f'participants-0-diet_no_soy': '',
            f'participants-0-diet_no_fish': '',
            f'participants-0-diet_no_fruits': '',
            f'participants-0-diet_other': '',
            f'participants-0-relevant_information': '',
            f'participants-0-DELETE': '',
            # Existing participant 1
            f'participants-1-id': str(self.p2.pk),
            f'participants-1-first_name': 'Bob',
            f'participants-1-last_name': 'Jones',
            f'participants-1-date_of_birth': '2001-06-15',
            f'participants-1-nickname': '',
            f'participants-1-health_restrictions': '',
            f'participants-1-diet_vegan': '',
            f'participants-1-diet_vegetarian': '',
            f'participants-1-diet_gluten_free': '',
            f'participants-1-diet_lactose_free': '',
            f'participants-1-diet_no_eggs': '',
            f'participants-1-diet_no_peanuts': '',
            f'participants-1-diet_no_tree_nuts': '',
            f'participants-1-diet_no_soy': '',
            f'participants-1-diet_no_fish': '',
            f'participants-1-diet_no_fruits': '',
            f'participants-1-diet_other': '',
            f'participants-1-relevant_information': '',
            f'participants-1-DELETE': '',
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('SkaRe:list_units'))

        # PKs must be unchanged
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.pk, self.original_p1_pk)
        self.assertEqual(self.p2.pk, self.original_p2_pk)

        # Count must still be 2
        self.assertEqual(RegularParticipant.objects.filter(unit=self.unit).count(), 2)
```

Run (some fields may not exist until dietary restructure is done — run after Task 2):

```bash
uv run python manage.py test SkaRe.tests.test_registration_views.StableParticipantIdTest --verbosity=0 2>&1 | tail -5
```

Expected: passes (the current formset code already handles this correctly with `queryset=existing_participants`). If it fails, the fix is in Step 2.

- [ ] **Step 2: Fix if test fails**

If `test_participant_ids_unchanged_after_edit` fails: in `SkaRe/views/registration.py`, in the `edit_unit` view, the POST branch calls `participant_formset.save(commit=False)` then manually saves instances. Replace lines 321–334 with:

```python
# save() with commit=False returns new/modified instances.
# Existing unchanged instances keep their PKs automatically via the queryset.
new_and_changed = participant_formset.save(commit=False)
for instance in new_and_changed:
    instance.unit = unit
    instance.save()
participant_formset.save_m2m()

for form in participant_formset.deleted_forms:
    if form.instance and form.instance.pk:
        form.instance.delete()

total = RegularParticipant.objects.filter(unit=unit).count()
messages.success(request, _('Unit "{unit_name}" updated successfully with {count} participant(s)!').format(
    unit_name=unit.entity.scout_unit_name,
    count=total
))
```

### Fix #44 — Evidence ID optional for non-Junák

- [ ] **Step 3: Make evidence ID optional in UnitRegistrationForm**

In `SkaRe/forms/registration.py`, in the `UnitRegistrationForm` class, find the `scout_unit_evidence_id` field definition (around line 104) and change `required=True` to `required=False`, and add a help_text:

```python
scout_unit_evidence_id = forms.CharField(
    max_length=50,
    required=False,
    widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g., 523.10')}),
    label=_("Evidence ID"),
    help_text=_("Junák unit ID (e.g. 523.10). Non-Junák units can leave this blank or use their own identifier."),
)
```

- [ ] **Step 4: Update evidence ID label in register_unit.html and edit_unit.html**

In both `register_unit.html` and `edit_unit.html`, find the evidence ID field rendering. It likely has a label showing "Evidence ID" with a `*` required marker. Since the field is now optional, verify the `*` asterisk is NOT shown (Django renders `required` fields with a CSS class that some templates use to show `*`). If the template explicitly adds `*`, remove it.

Also add the help text display below the field input if it's not already rendered. Search for `scout_unit_evidence_id` in both templates and add after the input:

```html
{% if form.scout_unit_evidence_id.help_text %}
    <div class="form-text text-muted small">{{ form.scout_unit_evidence_id.help_text }}</div>
{% endif %}
```

(In `register_unit.html` the form variable is `form`. In `edit_unit.html` the entity form variable is `entity_form` — check the template and use the correct variable name.)

### Fix #41 — Password validation UX

- [ ] **Step 5: Add help text to password fields in UserRegistrationForm**

In `SkaRe/forms/registration.py`, in `UserRegistrationForm.__init__`, after the existing `self.fields['password2'].widget.attrs.update(...)` line, add:

```python
self.fields['password1'].help_text = _(
    'Password must be at least 8 characters. '
    'Cannot be entirely numeric or too similar to your username.'
)
self.fields['password2'].help_text = _('Enter the same password again to confirm.')
```

- [ ] **Step 6: Run full test suite**

```bash
uv run python manage.py test SkaRe --verbosity=0 2>&1 | tail -5
```

Expected: all tests pass.

- [ ] **Step 7: Run Django system check**

```bash
uv run python manage.py check
```

Expected: "System check identified no issues."

- [ ] **Step 8: Check migration chain**

```bash
uv run python manage.py showmigrations SkaRe
```

Expected: all migrations show `[X]` (0001 through 0027).

- [ ] **Step 9: Commit**

```bash
git add SkaRe/views/registration.py \
        SkaRe/forms/registration.py \
        SkaRe/templates/SkaRe/registration/register_unit.html \
        SkaRe/templates/SkaRe/registration/edit_unit.html \
        SkaRe/tests/test_registration_views.py
git commit -m "fix: stable RegularParticipant IDs on unit edit (#34), evidence ID optional (#44), password help text (#41)"
```

---

## Self-Review

**Spec coverage check:**

- ✅ Section 2: RaceManagement group — Task 1, Step 2 (migration 0024)
- ✅ Section 2: `Entity.can_be_edited()` InfoDesk bypass — Task 1, Steps 3–4
- ✅ Section 2: `@infodesk_required` decorator — Task 1, Steps 3–4
- ✅ Section 3a: Dietary restructure (10 booleans + diet_other, data migration, remove old field) — Task 2
- ✅ Section 3b: AttendanceStatus, arrived_at, departed_at on Person, AttendanceLog model — Task 3
- ✅ Section 3c: SailTicket + SailTicketLog models — Task 4
- ✅ Section 3d: Stable RegularParticipant IDs — Task 5, Steps 1–2
- ✅ Section 3e: Evidence ID optional UX — Task 5, Steps 3–4
- ✅ Section 6 #34: Stable participant IDs — Task 5
- ✅ Section 6 #41: Password validation messaging — Task 5, Step 5
- ✅ Section 6 #44: Evidence ID optional — Task 5, Steps 3–4

**Not in this plan (intentionally deferred to Plan B):**
- Section 4: All InfoDesk views (dashboard, attendance, ticket management, exports)
- Section 5 items covered by Plan B migrations (none — all migrations 0024–0027 are in this plan)

**Type consistency check:**
- `Person.AttendanceStatus.choices` used in both `Person` field and `AttendanceLog.status` — consistent
- `SailTicket.Status.choices` used in both `SailTicket.status` and `SailTicketLog.status` — consistent
- `infodesk_required` defined in `permissions.py`, imported in test as `from SkaRe.permissions import infodesk_required` — consistent
- `dietary_summary()` method returns `str`; template uses `.dietary_summary|default:"-"` (calls without parentheses) — Django templates auto-call callables, so `p.dietary_summary` in templates correctly calls the method

**Placeholder scan:** No TBD, TODO, or incomplete steps found.
