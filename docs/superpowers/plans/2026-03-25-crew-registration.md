# Crew Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement crew registration for the race: a `Crew`/`CrewMember` data model, boat/participant lending, crew deadline, and CSV export.

**Architecture:** `Person` is already a concrete MTI model — no conversion needed. `CrewRegistrationForm` is a plain `Form` (not `ModelForm`) that captures boat + category + helmsman + up to 4 crew members and saves them as one `Crew` + up to 5 `CrewMember` rows inside `transaction.atomic()`. Lending uses a `visible_to` M2M field on both `Person` and `Boat`, managed via dedicated lend views that follow the existing `manage_editors` pattern.

**Tech Stack:** Django 6.0, Python 3.12, Bootstrap 5, Django i18n (`gettext_lazy` / `{% trans %}`), SQLite

---

## File Map

**Modified:**
- `SkaRe/models.py` — add `Person.visible_to`, `Boat.willing_to_lend`, `Boat.visible_to`, `EventSettings.crew_registration_deadline`, new `Crew`/`CrewMember` models
- `SkaRe/forms.py` — add `CrewRegistrationForm`; add `willing_to_lend` to `BoatForm`
- `SkaRe/views.py` — add crew views, lend views, CSV export, `_visible_persons`/`_visible_boats` helpers
- `SkaRe/urls.py` — add crew, lend, and export URL patterns
- `SkaRe/admin.py` — add `CrewAdmin`, `CrewMemberInline`; extend `BoatAdmin`
- `SkaRe/templates/SkaRe/boats/list.html` — add "Willing to lend" column
- `SkaRe/templates/SkaRe/boats/form.html` — add `willing_to_lend` checkbox
- `SkaRe/templates/SkaRe/home.html` — add crew buttons

**Created:**
- `SkaRe/migrations/0019_person_visible_to.py`
- `SkaRe/migrations/0020_boat_lending_fields.py`
- `SkaRe/migrations/0021_crew_registration_deadline.py`
- `SkaRe/migrations/0022_crew_crewmember.py`
- `SkaRe/templates/SkaRe/boats/lend.html`
- `SkaRe/templates/SkaRe/persons/lend.html`
- `SkaRe/templates/SkaRe/crews/register.html`
- `SkaRe/templates/SkaRe/crews/list.html`
- `SkaRe/templates/SkaRe/crews/detail.html`
- `SkaRe/templates/SkaRe/crews/edit.html`
- `SkaRe/templates/SkaRe/crews/confirm_delete.html`
- `SkaRe/tests/test_crew_models.py`
- `SkaRe/tests/test_crew_forms.py`
- `SkaRe/tests/test_crew_views.py`

---

### Task 1: Add `visible_to` to `Person` and `crew_registration_deadline` to `EventSettings`

**Files:**
- Modify: `SkaRe/models.py`
- Create: `SkaRe/tests/test_crew_models.py`

- [ ] **Step 1: Write failing tests**

Create `SkaRe/tests/test_crew_models.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from SkaRe.models import Person, EventSettings, Unit, Entity, RegularParticipant


def _make_user(username):
    return User.objects.create_user(username=username, password='pw')


def _make_entity(user):
    return Entity.objects.create(
        created_by=user,
        contact_email='test@test.com',
        contact_phone='123456789',
    )


def _make_unit(user):
    entity = _make_entity(user)
    return Unit.objects.create(entity=entity, contact_person_name='Test')


def _make_person(unit, first_name='Jan', last_name='Novák'):
    from datetime import date
    return RegularParticipant.objects.create(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date(2000, 1, 1),
        unit=unit,
    )


class PersonVisibleToTest(TestCase):
    def setUp(self):
        self.owner = _make_user('owner')
        self.borrower = _make_user('borrower')
        self.unit = _make_unit(self.owner)
        self.person = _make_person(self.unit)

    def test_visible_to_field_exists(self):
        self.person.visible_to.add(self.borrower)
        self.assertIn(self.borrower, self.person.visible_to.all())

    def test_visible_to_empty_by_default(self):
        self.assertEqual(self.person.visible_to.count(), 0)

    def test_borrowed_persons_reverse_relation(self):
        self.person.visible_to.add(self.borrower)
        self.assertIn(self.person.person_ptr, self.borrower.borrowed_persons.all())


class CrewRegistrationDeadlineTest(TestCase):
    def test_is_crew_registration_open_when_deadline_null(self):
        settings = EventSettings.get_solo()
        settings.crew_registration_deadline = None
        settings.save()
        self.assertTrue(EventSettings.is_crew_registration_open())

    def test_get_crew_registration_deadline_returns_none_when_null(self):
        settings = EventSettings.get_solo()
        settings.crew_registration_deadline = None
        settings.save()
        self.assertIsNone(EventSettings.get_crew_registration_deadline())

    def test_is_crew_registration_open_before_deadline(self):
        from django.utils import timezone
        from datetime import timedelta
        settings = EventSettings.get_solo()
        settings.crew_registration_deadline = timezone.now() + timedelta(days=1)
        settings.save()
        self.assertTrue(EventSettings.is_crew_registration_open())

    def test_is_crew_registration_closed_after_deadline(self):
        from django.utils import timezone
        from datetime import timedelta
        settings = EventSettings.get_solo()
        settings.crew_registration_deadline = timezone.now() - timedelta(days=1)
        settings.save()
        self.assertFalse(EventSettings.is_crew_registration_open())
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd /path/to/project && .venv/bin/python manage.py test SkaRe.tests.test_crew_models -v 2
```

Expected: `AttributeError: type object 'Person' has no attribute 'visible_to'` and similar errors.

- [ ] **Step 3: Add `visible_to` to `Person` and deadline to `EventSettings` in `models.py`**

In `SkaRe/models.py`, add to the `Person` class (after `relevant_information` field, before `calculate_category`):

```python
    visible_to = models.ManyToManyField(
        User,
        blank=True,
        related_name='borrowed_persons',
        verbose_name=_('Visible to'),
        help_text=_('Users who can see this person when registering a crew'),
    )
```

Add to the `EventSettings` class (after `editing_deadline` field):

```python
    crew_registration_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Deadline for creating and editing crew registrations"),
        verbose_name=_("Crew registration deadline"),
    )
```

Add these two methods to `EventSettings` (after `get_editing_deadline`):

```python
    @classmethod
    def is_crew_registration_open(cls):
        """Check if crew registration is still open"""
        try:
            settings = cls.get_solo()
            if settings and settings.crew_registration_deadline:
                return timezone.now() < settings.crew_registration_deadline
            return True  # No deadline set — open
        except Exception:
            return True

    @classmethod
    def get_crew_registration_deadline(cls):
        """Get the crew registration deadline"""
        try:
            settings = cls.get_solo()
            return settings.crew_registration_deadline if settings else None
        except Exception:
            return None
```

- [ ] **Step 4: Generate migrations**

```bash
.venv/bin/python manage.py makemigrations SkaRe --name person_visible_to
```

This creates two migrations (one for Person.visible_to, one for EventSettings). If Django creates a single migration, rename it; if separate, that's fine. Verify with:

```bash
.venv/bin/python manage.py showmigrations SkaRe
```

Expected: new `0019_...` entry (or two: `0019_` and `0020_`).

- [ ] **Step 5: Apply migrations**

```bash
.venv/bin/python manage.py migrate
```

- [ ] **Step 6: Run tests — expect pass**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_models -v 2
```

Expected: all 7 tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/models.py SkaRe/migrations/0019_* SkaRe/tests/test_crew_models.py
git commit -m "feat: add Person.visible_to and EventSettings.crew_registration_deadline"
```

---

### Task 2: Add lending fields to `Boat`

**Files:**
- Modify: `SkaRe/models.py`
- Modify: `SkaRe/tests/test_boat_models.py`

- [ ] **Step 1: Write failing tests**

Append to `SkaRe/tests/test_boat_models.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_boat_models.BoatLendingFieldsTest -v 2
```

Expected: `AttributeError: type object 'Boat' has no attribute 'willing_to_lend'`.

- [ ] **Step 3: Add fields to `Boat` in `models.py`**

In `SkaRe/models.py`, add to the `Boat` class after `engine_power_hp`:

```python
    willing_to_lend = models.BooleanField(
        default=False,
        verbose_name=_('Willing to lend'),
        help_text=_('Check if you are willing to lend this boat for the race'),
    )
    visible_to = models.ManyToManyField(
        User,
        blank=True,
        related_name='borrowed_boats',
        verbose_name=_('Visible to'),
        help_text=_('Users who can see and select this boat when registering a crew'),
    )
```

- [ ] **Step 4: Generate and apply migration**

```bash
.venv/bin/python manage.py makemigrations SkaRe --name boat_lending_fields
.venv/bin/python manage.py migrate
```

- [ ] **Step 5: Run tests — expect pass**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_boat_models -v 2
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add SkaRe/models.py SkaRe/migrations/0020_* SkaRe/tests/test_boat_models.py
git commit -m "feat: add Boat.willing_to_lend and Boat.visible_to"
```

*(Adjust migration number if Task 1 generated two migrations and numbering shifted.)*

---

### Task 3: Add `Crew` and `CrewMember` models

**Files:**
- Modify: `SkaRe/models.py`
- Modify: `SkaRe/tests/test_crew_models.py`

- [ ] **Step 1: Write failing tests**

Append to `SkaRe/tests/test_crew_models.py`:

```python
from SkaRe.models import Crew, CrewMember, Boat, BoatClass


class CrewModelTest(TestCase):
    def setUp(self):
        self.user = _make_user('crew_owner')
        self.unit = _make_unit(self.user)
        self.person = _make_person(self.unit)
        from datetime import date
        self.person2 = _make_person(self.unit, first_name='Petr', last_name='Dvořák')
        bc = BoatClass.objects.create(name='P550', category=BoatClass.Category.SAIL, order=1)
        self.boat = Boat.objects.create(
            created_by=self.user, boat_class=bc,
            name='ALBATROS', contact_person='J', contact_phone='123456789',
        )

    def test_create_crew(self):
        crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        self.assertEqual(crew.category, 'S')
        self.assertEqual(crew.boat, self.boat)

    def test_unique_boat_category(self):
        from django.db import IntegrityError
        Crew.objects.create(boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user)
        with self.assertRaises(IntegrityError):
            Crew.objects.create(boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user)

    def test_crew_str(self):
        crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        self.assertIn('ALBATROS', str(crew))
        self.assertIn('S', str(crew))

    def test_crew_member_helmsman(self):
        crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        member = CrewMember.objects.create(
            crew=crew,
            role=CrewMember.ROLE_HELMSMAN,
            participant=self.person.person_ptr,
        )
        self.assertEqual(member.role, CrewMember.ROLE_HELMSMAN)

    def test_crew_member_crew_role(self):
        crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        CrewMember.objects.create(
            crew=crew, role=CrewMember.ROLE_HELMSMAN, participant=self.person.person_ptr
        )
        member2 = CrewMember.objects.create(
            crew=crew, role=CrewMember.ROLE_CREW, participant=self.person2.person_ptr
        )
        self.assertEqual(crew.members.count(), 2)
        self.assertEqual(member2.role, CrewMember.ROLE_CREW)

    def test_crew_members_deleted_with_crew(self):
        crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        CrewMember.objects.create(
            crew=crew, role=CrewMember.ROLE_HELMSMAN, participant=self.person.person_ptr
        )
        crew_id = crew.id
        crew.delete()
        self.assertFalse(CrewMember.objects.filter(crew_id=crew_id).exists())
```

- [ ] **Step 2: Run tests — expect failure**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_models.CrewModelTest -v 2
```

Expected: `ImportError: cannot import name 'Crew' from 'SkaRe.models'`.

- [ ] **Step 3: Add `Crew` and `CrewMember` to `models.py`**

Append to `SkaRe/models.py` (after the `Boat` class):

```python
class Crew(models.Model):
    CATEGORY_Q  = 'Q'
    CATEGORY_S  = 'S'
    CATEGORY_R  = 'R'
    CATEGORY_D  = 'D'
    CATEGORY_SN = 'SN'
    CATEGORY_DN = 'DN'
    CATEGORY_OZ = 'OZ'
    CATEGORY_OD = 'OD'
    CATEGORY_MS = 'MS'

    CATEGORY_CHOICES = [
        (CATEGORY_Q,  _('Q – Žabičky a vlčata')),
        (CATEGORY_S,  _('S – Skautky a skauti')),
        (CATEGORY_R,  _('R – Rangers a roveři')),
        (CATEGORY_D,  _('D – Dospělí')),
        (CATEGORY_SN, _('SN – Skautští námořníci')),
        (CATEGORY_DN, _('DN – Dospělí námořníci')),
        (CATEGORY_OZ, _('OŽ – Open Žáci')),
        (CATEGORY_OD, _('OD – Open Dospělí')),
        (CATEGORY_MS, _('MS – Modrá stuha')),
    ]

    boat = models.ForeignKey(
        Boat,
        on_delete=models.PROTECT,
        verbose_name=_('Boat'),
    )
    category = models.CharField(
        max_length=3,
        choices=CATEGORY_CHOICES,
        verbose_name=_('Category'),
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_('Created by'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('boat', 'category')
        verbose_name = _('Crew')
        verbose_name_plural = _('Crews')

    def __str__(self):
        return f"{self.boat} – {self.get_category_display()}"

    def can_be_edited(self, user):
        return self.created_by == user or user.groups.filter(name='InfoDesk').exists()


class CrewMember(models.Model):
    ROLE_HELMSMAN = 'helmsman'
    ROLE_CREW     = 'crew'
    ROLE_CHOICES  = [
        (ROLE_HELMSMAN, _('Helmsman')),
        (ROLE_CREW,     _('Crew member')),
    ]

    crew = models.ForeignKey(
        Crew,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name=_('Crew'),
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name=_('Role'),
    )
    participant = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        verbose_name=_('Participant'),
    )

    class Meta:
        verbose_name = _('Crew member')
        verbose_name_plural = _('Crew members')

    def __str__(self):
        return f"{self.get_role_display()}: {self.participant}"
```

- [ ] **Step 4: Generate and apply migration**

```bash
.venv/bin/python manage.py makemigrations SkaRe --name crew_crewmember
.venv/bin/python manage.py migrate
```

- [ ] **Step 5: Run tests — expect pass**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_models -v 2
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add SkaRe/models.py SkaRe/migrations/0022_* SkaRe/tests/test_crew_models.py
git commit -m "feat: add Crew and CrewMember models"
```

*(Adjust migration number if earlier tasks generated different counts.)*

---

### Task 4: Add `willing_to_lend` to `BoatForm` and update boat templates

**Files:**
- Modify: `SkaRe/forms.py`
- Modify: `SkaRe/templates/SkaRe/boats/form.html`
- Modify: `SkaRe/templates/SkaRe/boats/list.html`
- Modify: `SkaRe/tests/test_boat_forms.py`

- [ ] **Step 1: Write failing test**

Open `SkaRe/tests/test_boat_forms.py` and append:

```python
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
```

- [ ] **Step 2: Run test — expect failure**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_boat_forms.BoatFormWillingToLendTest -v 2
```

Expected: `AssertionError: 'willing_to_lend' not found in form.fields`.

- [ ] **Step 3: Add `willing_to_lend` to `BoatForm` in `forms.py`**

In `SkaRe/forms.py`, find the `BoatForm` Meta `fields` list and add `'willing_to_lend'`:

```python
class BoatForm(forms.ModelForm):
    class Meta:
        model = Boat
        fields = [
            'boat_class', 'class_supplement', 'sail_number', 'name', 'description',
            'sail_area', 'hull_color', 'sail_color',
            'harbor_number', 'harbor_name', 'contact_person', 'contact_phone',
            'vessel_registry_number', 'engine_power_hp',
            'willing_to_lend',
        ]
```

*(If fields are already declared differently, just append `'willing_to_lend'` to the list.)*

- [ ] **Step 4: Add `willing_to_lend` checkbox to `boats/form.html`**

Open `SkaRe/templates/SkaRe/boats/form.html`. Inside the "Vlastník / správce" card section, after the existing fields, add:

```html
<div class="mb-3">
    <div class="form-check">
        {{ form.willing_to_lend }}
        <label class="form-check-label" for="{{ form.willing_to_lend.id_for_label }}">
            {% trans "I am willing to lend this boat for the race" %}
        </label>
    </div>
</div>
```

- [ ] **Step 5: Add "Willing to lend" column to `boats/list.html`**

In `SkaRe/templates/SkaRe/boats/list.html`, in the `<thead>` `<tr>`, add after the "Contact Person" `<th>`:

```html
<th>{% trans "Willing to lend" %}</th>
```

In the `<tbody>` `{% for boat in boats %}` row, add after `{{ boat.contact_person }}` `<td>`:

```html
<td>
    {% if boat.willing_to_lend %}
        <i class="bi bi-check-circle-fill text-success" title="{% trans 'Willing to lend' %}"></i>
    {% endif %}
</td>
```

- [ ] **Step 6: Run tests — expect pass**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_boat_forms -v 2
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/forms.py SkaRe/templates/SkaRe/boats/form.html SkaRe/templates/SkaRe/boats/list.html SkaRe/tests/test_boat_forms.py
git commit -m "feat: add willing_to_lend to boat form and list"
```

---

### Task 5: Boat lending view and template

**Files:**
- Modify: `SkaRe/views.py`
- Modify: `SkaRe/urls.py`
- Create: `SkaRe/templates/SkaRe/boats/lend.html`
- Create: `SkaRe/tests/test_crew_views.py`

- [ ] **Step 1: Write failing test**

Create `SkaRe/tests/test_crew_views.py`:

```python
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from SkaRe.models import BoatClass, Boat, Entity, Unit


def _make_user(username):
    return User.objects.create_user(username=username, password='pw')


def _make_entity(user):
    return Entity.objects.create(
        created_by=user, contact_email='a@a.com', contact_phone='123456789'
    )


def _make_unit(user):
    return Unit.objects.create(entity=_make_entity(user), contact_person_name='Test')


def _make_boat(user, **kw):
    bc = BoatClass.objects.get_or_create(name='P550', category=BoatClass.Category.SAIL, order=1)[0]
    return Boat.objects.create(
        created_by=user, boat_class=bc, name='ALBATROS',
        contact_person='J', contact_phone='123456789', **kw
    )


class BoatLendViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = _make_user('owner')
        self.stranger = _make_user('stranger')
        self.borrower = _make_user('borrower')
        self.boat = _make_boat(self.owner)

    def test_lend_page_requires_login(self):
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response['Location'])

    def test_lend_page_accessible_by_owner(self):
        self.client.login(username='owner', password='pw')
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_lend_page_forbidden_for_stranger(self):
        self.client.login(username='stranger', password='pw')
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_add_user_to_visible_to(self):
        self.client.login(username='owner', password='pw')
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        response = self.client.post(url, {'action': 'add', 'username': 'borrower'})
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.borrower, self.boat.visible_to.all())

    def test_remove_user_from_visible_to(self):
        self.boat.visible_to.add(self.borrower)
        self.client.login(username='owner', password='pw')
        url = reverse('SkaRe:boat_lend', kwargs={'boat_id': self.boat.pk})
        self.client.post(url, {'action': 'remove', 'user_id': self.borrower.pk})
        self.assertNotIn(self.borrower, self.boat.visible_to.all())
```

- [ ] **Step 2: Run tests — expect failure**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_views.BoatLendViewTest -v 2
```

Expected: `NoReverseMatch` for `boat_lend`.

- [ ] **Step 3: Add `boat_lend` view to `views.py`**

In `SkaRe/views.py`, add import for `Crew`, `CrewMember`, `Person` at the top with existing model imports:

```python
from .models import (
    Entity, Unit, RegularParticipant, EventSettings,
    IndividualParticipant, Organizer, BoatClass, Boat,
    Person, Crew, CrewMember,
)
```

Add these two helper functions near the top of views (after the constants):

```python
def _visible_persons(user):
    """Return all Persons visible to a user for crew registration."""
    from django.db.models import Q
    return Person.objects.filter(
        Q(regularparticipant__unit__entity__created_by=user) |
        Q(regularparticipant__unit__entity__editors=user) |
        Q(individualparticipant__entity__created_by=user) |
        Q(individualparticipant__entity__editors=user) |
        Q(organizer__entity__created_by=user) |
        Q(organizer__entity__editors=user) |
        Q(visible_to=user)
    ).distinct()


def _visible_boats(user):
    """Return all Boats visible to a user for crew registration."""
    return Boat.objects.filter(
        Q(created_by=user) | Q(visible_to=user)
    ).distinct()
```

Add the `boat_lend` view:

```python
@login_required
def boat_lend(request, boat_id):
    """Manage which users can see and use this boat in crew registration."""
    boat = get_object_or_404(Boat, id=boat_id)

    if not boat.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to manage lending for this boat.'))
        return redirect('SkaRe:boat_detail', boat_id=boat_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            username = request.POST.get('username', '').strip()
            try:
                user_to_add = User.objects.get(username=username)
                if user_to_add == request.user:
                    messages.warning(request, _('You cannot lend to yourself.'))
                elif boat.visible_to.filter(id=user_to_add.id).exists():
                    messages.warning(request, _('User "{username}" already has access.').format(username=username))
                else:
                    boat.visible_to.add(user_to_add)
                    messages.success(request, _('User "{username}" can now see this boat.').format(username=username))
            except User.DoesNotExist:
                messages.error(request, _('User "{username}" not found.').format(username=username))
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            try:
                user_to_remove = User.objects.get(id=user_id)
                boat.visible_to.remove(user_to_remove)
                messages.success(request, _('Access removed for user "{username}".').format(username=user_to_remove.username))
            except User.DoesNotExist:
                pass
        return redirect('SkaRe:boat_lend', boat_id=boat_id)

    return render(request, 'SkaRe/boats/lend.html', {
        'boat': boat,
        'lent_to': boat.visible_to.all(),
    })
```

- [ ] **Step 4: Add URL to `urls.py`**

In `SkaRe/urls.py`, add after `boats/<int:boat_id>/delete/`:

```python
path('boats/<int:boat_id>/lend/', views.boat_lend, name='boat_lend'),
```

- [ ] **Step 5: Create `boats/lend.html` template**

Create `SkaRe/templates/SkaRe/boats/lend.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Lend Boat" %} - SkaRe{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8 offset-md-2">
        <h1 class="mb-4">
            <i class="bi bi-people-fill"></i> {% trans "Lend Boat" %}
        </h1>

        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">{{ boat }}</h5>
            </div>
            <div class="card-body">
                <p class="text-muted">
                    <i class="bi bi-info-circle"></i>
                    {% trans "Users listed here can see and use this boat when registering a crew." %}
                </p>

                <h6 class="mb-3">{% trans "Currently lent to" %}</h6>

                {% if lent_to %}
                    <ul class="list-group mb-4">
                        {% for u in lent_to %}
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <i class="bi bi-person"></i>
                                    <strong>{{ u.username }}</strong>
                                    {% if u.first_name or u.last_name %}
                                        <span class="text-muted">({{ u.first_name }} {{ u.last_name }})</span>
                                    {% endif %}
                                </div>
                                <form method="post" style="display:inline;">
                                    {% csrf_token %}
                                    <input type="hidden" name="action" value="remove">
                                    <input type="hidden" name="user_id" value="{{ u.id }}">
                                    <button type="submit" class="btn btn-sm btn-outline-danger"
                                            onclick="return confirm('{% trans "Remove access for this user?" %}');">
                                        <i class="bi bi-x-circle"></i> {% trans "Remove" %}
                                    </button>
                                </form>
                            </li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <div class="alert alert-info mb-4">
                        <i class="bi bi-info-circle"></i> {% trans "This boat has not been lent to anyone yet." %}
                    </div>
                {% endif %}

                <h6 class="mb-3">{% trans "Add user" %}</h6>
                <form method="post" class="row g-3">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="add">
                    <div class="col-md-8">
                        <input type="text" name="username" class="form-control"
                               placeholder="{% trans 'Enter username' %}" required>
                        <div class="form-text">{% trans "Enter the exact username of the user you want to grant access." %}</div>
                    </div>
                    <div class="col-md-4">
                        <button type="submit" class="btn btn-success w-100">
                            <i class="bi bi-plus-circle"></i> {% trans "Grant access" %}
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <a href="{% url 'SkaRe:boat_detail' boat_id=boat.pk %}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> {% trans "Back to boat" %}
        </a>
    </div>
</div>
{% endblock %}
```

Also add a "Lend" button to `boats/detail.html`. Open that file and find the edit/delete buttons, then add:

```html
{% if boat.created_by == request.user or request.user.groups.filter(name='InfoDesk').exists %}
    <a href="{% url 'SkaRe:boat_lend' boat_id=boat.pk %}" class="btn btn-outline-secondary">
        <i class="bi bi-people"></i> {% trans "Manage lending" %}
    </a>
{% endif %}
```

- [ ] **Step 6: Run tests — expect pass**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_views.BoatLendViewTest -v 2
```

Expected: all 5 tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/views.py SkaRe/urls.py SkaRe/templates/SkaRe/boats/lend.html SkaRe/templates/SkaRe/boats/detail.html SkaRe/tests/test_crew_views.py
git commit -m "feat: add boat lending view and template"
```

---

### Task 6: Person lending view and template

**Files:**
- Modify: `SkaRe/views.py`
- Modify: `SkaRe/urls.py`
- Create: `SkaRe/templates/SkaRe/persons/lend.html`
- Modify: `SkaRe/tests/test_crew_views.py`

- [ ] **Step 1: Write failing tests**

Append to `SkaRe/tests/test_crew_views.py`:

```python
from SkaRe.models import RegularParticipant
from datetime import date


def _make_person(unit, first='Jan', last='Novák'):
    return RegularParticipant.objects.create(
        first_name=first, last_name=last,
        date_of_birth=date(2000, 1, 1),
        unit=unit,
    )


class PersonLendViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = _make_user('person_owner')
        self.stranger = _make_user('person_stranger')
        self.borrower = _make_user('person_borrower')
        self.unit = _make_unit(self.owner)
        self.person = _make_person(self.unit)

    def test_lend_page_requires_login(self):
        url = reverse('SkaRe:person_lend', kwargs={'person_id': self.person.pk})
        response = self.client.get(url)
        self.assertRedirects(response, f'/user/login/?next={url}', fetch_redirect_response=False)

    def test_lend_page_accessible_by_unit_owner(self):
        self.client.login(username='person_owner', password='pw')
        url = reverse('SkaRe:person_lend', kwargs={'person_id': self.person.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_lend_page_forbidden_for_stranger(self):
        self.client.login(username='person_stranger', password='pw')
        url = reverse('SkaRe:person_lend', kwargs={'person_id': self.person.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_add_user_to_visible_to(self):
        self.client.login(username='person_owner', password='pw')
        url = reverse('SkaRe:person_lend', kwargs={'person_id': self.person.pk})
        self.client.post(url, {'action': 'add', 'username': 'person_borrower'})
        person_base = Person.objects.get(pk=self.person.pk)
        self.assertIn(self.borrower, person_base.visible_to.all())

    def test_remove_user_from_visible_to(self):
        person_base = Person.objects.get(pk=self.person.pk)
        person_base.visible_to.add(self.borrower)
        self.client.login(username='person_owner', password='pw')
        url = reverse('SkaRe:person_lend', kwargs={'person_id': self.person.pk})
        self.client.post(url, {'action': 'remove', 'user_id': self.borrower.pk})
        person_base.refresh_from_db()
        self.assertNotIn(self.borrower, person_base.visible_to.all())
```

- [ ] **Step 2: Run tests — expect failure**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_views.PersonLendViewTest -v 2
```

Expected: `NoReverseMatch` for `person_lend`.

- [ ] **Step 3: Add `person_lend` view to `views.py`**

The permission logic: unit owner/editors for `RegularParticipant`, entity owner/editors for others.

```python
@login_required
def person_lend(request, person_id):
    """Manage which users can see and use this person in crew registration."""
    person = get_object_or_404(Person, id=person_id)

    # Determine if request.user can manage lending for this person
    can_manage = False
    if hasattr(person, 'regularparticipant'):
        entity = person.regularparticipant.unit.entity
        can_manage = entity.created_by == request.user or entity.editors.filter(id=request.user.id).exists()
    elif hasattr(person, 'individualparticipant'):
        entity = person.individualparticipant.entity
        can_manage = entity.created_by == request.user or entity.editors.filter(id=request.user.id).exists()
    elif hasattr(person, 'organizer'):
        entity = person.organizer.entity
        can_manage = entity.created_by == request.user or entity.editors.filter(id=request.user.id).exists()

    if not can_manage:
        messages.error(request, _('You do not have permission to manage lending for this person.'))
        return redirect('SkaRe:home')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            username = request.POST.get('username', '').strip()
            try:
                user_to_add = User.objects.get(username=username)
                if person.visible_to.filter(id=user_to_add.id).exists():
                    messages.warning(request, _('User "{username}" already has access.').format(username=username))
                else:
                    person.visible_to.add(user_to_add)
                    messages.success(request, _('User "{username}" can now see this person.').format(username=username))
            except User.DoesNotExist:
                messages.error(request, _('User "{username}" not found.').format(username=username))
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            try:
                user_to_remove = User.objects.get(id=user_id)
                person.visible_to.remove(user_to_remove)
                messages.success(request, _('Access removed for user "{username}".').format(username=user_to_remove.username))
            except User.DoesNotExist:
                pass
        return redirect('SkaRe:person_lend', person_id=person_id)

    return render(request, 'SkaRe/persons/lend.html', {
        'person': person,
        'lent_to': person.visible_to.all(),
    })
```

- [ ] **Step 4: Add URL to `urls.py`**

```python
path('persons/<int:person_id>/lend/', views.person_lend, name='person_lend'),
```

- [ ] **Step 5: Create `persons/lend.html` template**

Create directory and file `SkaRe/templates/SkaRe/persons/lend.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Lend Person" %} - SkaRe{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8 offset-md-2">
        <h1 class="mb-4">
            <i class="bi bi-people-fill"></i> {% trans "Lend Participant" %}
        </h1>

        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">{{ person }}</h5>
            </div>
            <div class="card-body">
                <p class="text-muted">
                    <i class="bi bi-info-circle"></i>
                    {% trans "Users listed here can see and include this participant in a crew registration." %}
                </p>

                <h6 class="mb-3">{% trans "Currently lent to" %}</h6>

                {% if lent_to %}
                    <ul class="list-group mb-4">
                        {% for u in lent_to %}
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <i class="bi bi-person"></i>
                                    <strong>{{ u.username }}</strong>
                                    {% if u.first_name or u.last_name %}
                                        <span class="text-muted">({{ u.first_name }} {{ u.last_name }})</span>
                                    {% endif %}
                                </div>
                                <form method="post" style="display:inline;">
                                    {% csrf_token %}
                                    <input type="hidden" name="action" value="remove">
                                    <input type="hidden" name="user_id" value="{{ u.id }}">
                                    <button type="submit" class="btn btn-sm btn-outline-danger"
                                            onclick="return confirm('{% trans "Remove access for this user?" %}');">
                                        <i class="bi bi-x-circle"></i> {% trans "Remove" %}
                                    </button>
                                </form>
                            </li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <div class="alert alert-info mb-4">
                        <i class="bi bi-info-circle"></i> {% trans "This participant has not been lent to anyone yet." %}
                    </div>
                {% endif %}

                <h6 class="mb-3">{% trans "Add user" %}</h6>
                <form method="post" class="row g-3">
                    {% csrf_token %}
                    <input type="hidden" name="action" value="add">
                    <div class="col-md-8">
                        <input type="text" name="username" class="form-control"
                               placeholder="{% trans 'Enter username' %}" required>
                        <div class="form-text">{% trans "Enter the exact username of the user you want to grant access." %}</div>
                    </div>
                    <div class="col-md-4">
                        <button type="submit" class="btn btn-success w-100">
                            <i class="bi bi-plus-circle"></i> {% trans "Grant access" %}
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <a href="{% url 'SkaRe:home' %}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> {% trans "Back" %}
        </a>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Run tests — expect pass**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_views -v 2
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/views.py SkaRe/urls.py SkaRe/templates/SkaRe/persons/ SkaRe/tests/test_crew_views.py
git commit -m "feat: add person lending view and template"
```

---

### Task 7: `CrewRegistrationForm`

**Files:**
- Modify: `SkaRe/forms.py`
- Create: `SkaRe/tests/test_crew_forms.py`

- [ ] **Step 1: Write failing tests**

Create `SkaRe/tests/test_crew_forms.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from datetime import date
from SkaRe.models import BoatClass, Boat, Entity, Unit, RegularParticipant, Crew, Person


def _make_user(username):
    return User.objects.create_user(username=username, password='pw')


def _make_entity(user):
    return Entity.objects.create(
        created_by=user, contact_email='a@a.com', contact_phone='123456789'
    )


def _make_unit(user):
    return Unit.objects.create(entity=_make_entity(user), contact_person_name='Test')


def _make_person(unit, first='Jan', last='Novák'):
    return RegularParticipant.objects.create(
        first_name=first, last_name=last, date_of_birth=date(2000, 1, 1), unit=unit
    )


def _make_boat(user):
    bc = BoatClass.objects.get_or_create(name='P550', category=BoatClass.Category.SAIL, order=1)[0]
    return Boat.objects.create(
        created_by=user, boat_class=bc, name='ALBATROS',
        contact_person='J', contact_phone='123456789'
    )


class CrewRegistrationFormTest(TestCase):
    def setUp(self):
        from SkaRe.forms import CrewRegistrationForm
        self.Form = CrewRegistrationForm
        self.user = _make_user('formowner')
        self.unit = _make_unit(self.user)
        self.helmsman = _make_person(self.unit, 'Helm', 'Man')
        self.crew1 = _make_person(self.unit, 'Crew', 'One')
        self.boat = _make_boat(self.user)

    def _valid_data(self, **overrides):
        data = {
            'boat': self.boat.pk,
            'category': Crew.CATEGORY_S,
            'helmsman': self.helmsman.pk,
        }
        data.update(overrides)
        return data

    def test_valid_form_with_helmsman_only(self):
        form = self.Form(user=self.user, data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_form_with_one_crew_member(self):
        form = self.Form(user=self.user, data=self._valid_data(crew_member_1=self.crew1.pk))
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_when_helmsman_missing(self):
        data = self._valid_data()
        del data['helmsman']
        form = self.Form(user=self.user, data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_when_helmsman_same_as_crew_member(self):
        form = self.Form(
            user=self.user,
            data=self._valid_data(crew_member_1=self.helmsman.pk),
        )
        self.assertFalse(form.is_valid())

    def test_only_visible_boats_in_queryset(self):
        other_user = _make_user('boatstranger')
        other_boat = _make_boat(other_user)
        form = self.Form(user=self.user, data=self._valid_data())
        boat_pks = list(form.fields['boat'].queryset.values_list('pk', flat=True))
        self.assertIn(self.boat.pk, boat_pks)
        self.assertNotIn(other_boat.pk, boat_pks)

    def test_only_visible_persons_in_helmsman_queryset(self):
        other_user = _make_user('personstranger')
        other_unit = _make_unit(other_user)
        other_person = _make_person(other_unit, 'Other', 'Person')
        form = self.Form(user=self.user, data=self._valid_data())
        person_pks = list(form.fields['helmsman'].queryset.values_list('pk', flat=True))
        self.assertIn(self.helmsman.pk, person_pks)
        self.assertNotIn(other_person.pk, person_pks)

    def test_borrowed_person_in_queryset(self):
        other_user = _make_user('lender')
        other_unit = _make_unit(other_user)
        lent_person = _make_person(other_unit, 'Lent', 'Person')
        Person.objects.get(pk=lent_person.pk).visible_to.add(self.user)
        form = self.Form(user=self.user, data=self._valid_data())
        person_pks = list(form.fields['helmsman'].queryset.values_list('pk', flat=True))
        self.assertIn(lent_person.pk, person_pks)
```

- [ ] **Step 2: Run tests — expect failure**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_forms -v 2
```

Expected: `ImportError: cannot import name 'CrewRegistrationForm'`.

- [ ] **Step 3: Add `CrewRegistrationForm` to `forms.py`**

In `SkaRe/forms.py`, add imports at the top:

```python
from .models import Unit, RegularParticipant, IndividualParticipant, Organizer, BoatClass, Boat, Person, Crew
```

Then add the form class:

```python
class CrewRegistrationForm(forms.Form):
    boat = forms.ModelChoiceField(
        queryset=Boat.objects.none(),
        label=_('Boat'),
        empty_label=_('— select a boat —'),
    )
    category = forms.ChoiceField(
        choices=[('', _('— select a category —'))] + Crew.CATEGORY_CHOICES,
        label=_('Category'),
    )
    helmsman = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        label=_('Helmsman'),
        empty_label=_('— select a person —'),
    )
    crew_member_1 = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        required=False,
        label=_('Crew member 1'),
        empty_label=_('—'),
    )
    crew_member_2 = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        required=False,
        label=_('Crew member 2'),
        empty_label=_('—'),
    )
    crew_member_3 = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        required=False,
        label=_('Crew member 3'),
        empty_label=_('—'),
    )
    crew_member_4 = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        required=False,
        label=_('Crew member 4'),
        empty_label=_('—'),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        visible_boats = Boat.objects.filter(
            Q(created_by=user) | Q(visible_to=user)
        ).distinct()
        visible_persons = Person.objects.filter(
            Q(regularparticipant__unit__entity__created_by=user) |
            Q(regularparticipant__unit__entity__editors=user) |
            Q(individualparticipant__entity__created_by=user) |
            Q(individualparticipant__entity__editors=user) |
            Q(organizer__entity__created_by=user) |
            Q(organizer__entity__editors=user) |
            Q(visible_to=user)
        ).distinct()
        self.fields['boat'].queryset = visible_boats
        for field in ['helmsman', 'crew_member_1', 'crew_member_2', 'crew_member_3', 'crew_member_4']:
            self.fields[field].queryset = visible_persons

    def clean(self):
        cleaned_data = super().clean()
        participants = [
            cleaned_data.get('helmsman'),
            cleaned_data.get('crew_member_1'),
            cleaned_data.get('crew_member_2'),
            cleaned_data.get('crew_member_3'),
            cleaned_data.get('crew_member_4'),
        ]
        non_null = [p for p in participants if p is not None]
        if len(non_null) != len({p.pk for p in non_null}):
            raise forms.ValidationError(
                _('A participant cannot appear more than once in a crew.')
            )
        return cleaned_data
```

- [ ] **Step 4: Run tests — expect pass**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_forms -v 2
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add SkaRe/forms.py SkaRe/tests/test_crew_forms.py
git commit -m "feat: add CrewRegistrationForm"
```

---

### Task 8: Crew register, list, and detail views + templates

**Files:**
- Modify: `SkaRe/views.py`
- Modify: `SkaRe/urls.py`
- Create: `SkaRe/templates/SkaRe/crews/register.html`
- Create: `SkaRe/templates/SkaRe/crews/list.html`
- Create: `SkaRe/templates/SkaRe/crews/detail.html`
- Modify: `SkaRe/tests/test_crew_views.py`

- [ ] **Step 1: Write failing tests**

Append to `SkaRe/tests/test_crew_views.py`:

```python
from SkaRe.models import Crew, CrewMember, Person


class CrewRegisterViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = _make_user('crewreg')
        self.unit = _make_unit(self.user)
        self.helmsman = _make_person(self.unit)
        self.boat = _make_boat(self.user)

    def test_register_requires_login(self):
        url = reverse('SkaRe:crew_register')
        self.assertRedirects(
            self.client.get(url),
            f'/user/login/?next={url}',
            fetch_redirect_response=False,
        )

    def test_register_get_renders_form(self):
        self.client.login(username='crewreg', password='pw')
        response = self.client.get(reverse('SkaRe:crew_register'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_register_creates_crew_and_members(self):
        self.client.login(username='crewreg', password='pw')
        response = self.client.post(reverse('SkaRe:crew_register'), {
            'boat': self.boat.pk,
            'category': Crew.CATEGORY_S,
            'helmsman': self.helmsman.pk,
        })
        self.assertEqual(Crew.objects.count(), 1)
        crew = Crew.objects.first()
        self.assertEqual(crew.members.count(), 1)
        self.assertEqual(crew.members.first().role, CrewMember.ROLE_HELMSMAN)
        self.assertRedirects(
            response,
            reverse('SkaRe:crew_detail', kwargs={'crew_id': crew.pk}),
            fetch_redirect_response=False,
        )

    def test_duplicate_boat_category_shows_error(self):
        self.client.login(username='crewreg', password='pw')
        Crew.objects.create(boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user)
        response = self.client.post(reverse('SkaRe:crew_register'), {
            'boat': self.boat.pk,
            'category': Crew.CATEGORY_S,
            'helmsman': self.helmsman.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Crew.objects.count(), 1)  # no new crew created


class CrewListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = _make_user('crewlist')

    def test_list_requires_login(self):
        url = reverse('SkaRe:crew_list')
        self.assertRedirects(
            self.client.get(url),
            f'/user/login/?next={url}',
            fetch_redirect_response=False,
        )

    def test_list_shows_only_user_crews(self):
        unit = _make_unit(self.user)
        helmsman = _make_person(unit)
        boat = _make_boat(self.user)
        other_user = _make_user('crewother')
        Crew.objects.create(boat=boat, category=Crew.CATEGORY_S, created_by=self.user)
        other_boat = _make_boat(other_user)
        Crew.objects.create(boat=other_boat, category=Crew.CATEGORY_S, created_by=other_user)
        self.client.login(username='crewlist', password='pw')
        response = self.client.get(reverse('SkaRe:crew_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['crews']), 1)
```

- [ ] **Step 2: Run tests — expect failure**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_views.CrewRegisterViewTest SkaRe.tests.test_crew_views.CrewListViewTest -v 2
```

Expected: `NoReverseMatch` for `crew_register`.

- [ ] **Step 3: Add crew register, list, detail views to `views.py`**

Add to `SkaRe/views.py`:

```python
@login_required
def crew_register(request):
    """Register a new crew."""
    is_infodesk = request.user.groups.filter(name='InfoDesk').exists()
    if not EventSettings.is_crew_registration_open() and not is_infodesk:
        messages.error(request, _('Crew registration is closed.'))
        return redirect('SkaRe:home')

    form = CrewRegistrationForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        boat = form.cleaned_data['boat']
        category = form.cleaned_data['category']
        if Crew.objects.filter(boat=boat, category=category).exists():
            form.add_error(None, _('A crew for this boat and category already exists.'))
        else:
            with transaction.atomic():
                crew = Crew.objects.create(
                    boat=boat, category=category, created_by=request.user
                )
                CrewMember.objects.create(
                    crew=crew,
                    role=CrewMember.ROLE_HELMSMAN,
                    participant=form.cleaned_data['helmsman'],
                )
                for i in range(1, 5):
                    person = form.cleaned_data.get(f'crew_member_{i}')
                    if person:
                        CrewMember.objects.create(
                            crew=crew, role=CrewMember.ROLE_CREW, participant=person
                        )
            messages.success(request, _('Crew registered successfully.'))
            return redirect('SkaRe:crew_detail', crew_id=crew.id)

    return render(request, 'SkaRe/crews/register.html', {'form': form})


@login_required
def crew_list(request):
    """List crews created by the current user."""
    crews = Crew.objects.filter(created_by=request.user).select_related('boat', 'boat__boat_class').prefetch_related('members')
    return render(request, 'SkaRe/crews/list.html', {'crews': crews})


@login_required
def crew_detail(request, crew_id):
    """View crew details."""
    crew = get_object_or_404(Crew, id=crew_id)
    members = crew.members.select_related('participant').order_by('-role')
    return render(request, 'SkaRe/crews/detail.html', {'crew': crew, 'members': members})
```

In `SkaRe/views.py` imports, add `CrewRegistrationForm` to the forms import:

```python
from .forms import (
    UserRegistrationForm, UnitRegistrationForm,
    IndividualParticipantRegistrationForm, OrganizerRegistrationForm,
    validate_czech_phone, get_participant_formset, BoatForm, CrewRegistrationForm,
)
```

- [ ] **Step 4: Add URLs**

In `SkaRe/urls.py`, add:

```python
path('crews/', views.crew_list, name='crew_list'),
path('crews/register/', views.crew_register, name='crew_register'),
path('crews/<int:crew_id>/', views.crew_detail, name='crew_detail'),
```

- [ ] **Step 5: Create crew templates**

Add Bootstrap `form-select` class to all select widgets in `CrewRegistrationForm.__init__` (add at the end of `__init__`):

```python
for fname in ['boat', 'helmsman', 'crew_member_1', 'crew_member_2', 'crew_member_3', 'crew_member_4']:
    self.fields[fname].widget.attrs.update({'class': 'form-select'})
self.fields['category'].widget.attrs.update({'class': 'form-select'})
```

Create `SkaRe/templates/SkaRe/crews/register.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Register Crew" %} - SkaRe{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8 offset-md-2">
        <h1 class="mb-4"><i class="bi bi-people-fill"></i> {% trans "Register Crew" %}</h1>

        {% if form.non_field_errors %}
            <div class="alert alert-danger">{{ form.non_field_errors }}</div>
        {% endif %}

        <form method="post" novalidate>
            {% csrf_token %}

            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">{% trans "Crew" %}</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="{{ form.boat.id_for_label }}" class="form-label">{{ form.boat.label }} <span class="text-danger">*</span></label>
                            {{ form.boat }}
                            {% if form.boat.errors %}<div class="text-danger small">{{ form.boat.errors }}</div>{% endif %}
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="{{ form.category.id_for_label }}" class="form-label">{{ form.category.label }} <span class="text-danger">*</span></label>
                            {{ form.category }}
                            {% if form.category.errors %}<div class="text-danger small">{{ form.category.errors }}</div>{% endif %}
                        </div>
                    </div>
                </div>
            </div>

            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">{% trans "Crew Members" %}</h5>
                </div>
                <div class="card-body">
                    {% for field_name, label in crew_fields %}
                        <div class="row mb-2 align-items-center">
                            <div class="col-md-3"><span class="form-control-plaintext fw-semibold">{{ label }}</span></div>
                            <div class="col-md-9">
                                {% if field_name == 'helmsman' %}
                                    {{ form.helmsman }}
                                    {% if form.helmsman.errors %}<div class="text-danger small">{{ form.helmsman.errors }}</div>{% endif %}
                                {% elif field_name == 'crew_member_1' %}{{ form.crew_member_1 }}
                                {% elif field_name == 'crew_member_2' %}{{ form.crew_member_2 }}
                                {% elif field_name == 'crew_member_3' %}{{ form.crew_member_3 }}
                                {% elif field_name == 'crew_member_4' %}{{ form.crew_member_4 }}
                                {% endif %}
                            </div>
                        </div>
                    {% endfor %}
                    <div class="form-text">{% trans "Helmsman required; up to 4 crew members." %}</div>
                </div>
            </div>

            <div class="d-flex gap-2">
                <button type="submit" class="btn btn-primary">
                    <i class="bi bi-check-circle"></i> {% trans "Register Crew" %}
                </button>
                <a href="{% url 'SkaRe:crew_list' %}" class="btn btn-secondary">{% trans "Cancel" %}</a>
            </div>
        </form>
    </div>
</div>
{% endblock %}
```

Create `SkaRe/templates/SkaRe/crews/list.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "My Crews" %} - SkaRe{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1 class="mb-0"><i class="bi bi-people-fill"></i> {% trans "My Crews" %}</h1>
            <a href="{% url 'SkaRe:crew_register' %}" class="btn btn-success">
                <i class="bi bi-plus-circle"></i> {% trans "Register a Crew" %}
            </a>
        </div>

        {% if crews %}
            <div class="card">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>{% trans "Boat" %}</th>
                                    <th>{% trans "Category" %}</th>
                                    <th>{% trans "Members" %}</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for crew in crews %}
                                <tr>
                                    <td><a href="{% url 'SkaRe:crew_detail' crew_id=crew.pk %}">{{ crew.boat }}</a></td>
                                    <td>{{ crew.get_category_display }}</td>
                                    <td>{{ crew.members.count }}</td>
                                    <td>
                                        <a href="{% url 'SkaRe:crew_edit' crew_id=crew.pk %}" class="btn btn-sm btn-outline-primary">{% trans "Edit" %}</a>
                                        <a href="{% url 'SkaRe:crew_delete' crew_id=crew.pk %}" class="btn btn-sm btn-outline-danger">{% trans "Delete" %}</a>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        {% else %}
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i>
                {% trans "You have not registered any crews yet." %}
                <a href="{% url 'SkaRe:crew_register' %}" class="btn btn-sm btn-success ms-2">{% trans "Register a Crew" %}</a>
            </div>
        {% endif %}
    </div>
</div>
{% endblock %}
```

Create `SkaRe/templates/SkaRe/crews/detail.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Crew" %} – {{ crew }} - SkaRe{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8 offset-md-2">
        <h1 class="mb-4"><i class="bi bi-people-fill"></i> {{ crew }}</h1>

        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">{% trans "Crew details" %}</h5>
            </div>
            <div class="card-body">
                <dl class="row mb-0">
                    <dt class="col-sm-4">{% trans "Boat" %}</dt>
                    <dd class="col-sm-8"><a href="{% url 'SkaRe:boat_detail' boat_id=crew.boat.pk %}">{{ crew.boat }}</a></dd>
                    <dt class="col-sm-4">{% trans "Category" %}</dt>
                    <dd class="col-sm-8">{{ crew.get_category_display }}</dd>
                </dl>
            </div>
        </div>

        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">{% trans "Members" %}</h5>
            </div>
            <div class="card-body p-0">
                <table class="table mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>{% trans "Role" %}</th>
                            <th>{% trans "Name" %}</th>
                            <th>{% trans "Date of birth" %}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for member in members %}
                        <tr>
                            <td>{{ member.get_role_display }}</td>
                            <td>{{ member.participant }}</td>
                            <td>{{ member.participant.date_of_birth }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        {% if crew.created_by == request.user or request.user.groups.filter(name='InfoDesk').exists %}
            <div class="d-flex gap-2 mb-3">
                <a href="{% url 'SkaRe:crew_edit' crew_id=crew.pk %}" class="btn btn-primary">{% trans "Edit" %}</a>
                <a href="{% url 'SkaRe:crew_delete' crew_id=crew.pk %}" class="btn btn-danger">{% trans "Delete" %}</a>
            </div>
        {% endif %}

        <a href="{% url 'SkaRe:crew_list' %}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> {% trans "Back to my crews" %}
        </a>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Run tests — expect pass**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_views.CrewRegisterViewTest SkaRe.tests.test_crew_views.CrewListViewTest -v 2
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/views.py SkaRe/urls.py SkaRe/templates/SkaRe/crews/ SkaRe/tests/test_crew_views.py
git commit -m "feat: add crew register, list, and detail views"
```

---

### Task 9: Crew edit and delete views + templates

**Files:**
- Modify: `SkaRe/views.py`
- Modify: `SkaRe/urls.py`
- Create: `SkaRe/templates/SkaRe/crews/edit.html`
- Create: `SkaRe/templates/SkaRe/crews/confirm_delete.html`
- Modify: `SkaRe/tests/test_crew_views.py`

- [ ] **Step 1: Write failing tests**

Append to `SkaRe/tests/test_crew_views.py`:

```python
class CrewEditDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = _make_user('editowner')
        self.stranger = _make_user('editstranger')
        self.unit = _make_unit(self.user)
        self.helmsman = _make_person(self.unit)
        self.new_helm = _make_person(self.unit, 'New', 'Helm')
        self.boat = _make_boat(self.user)
        self.crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        CrewMember.objects.create(
            crew=self.crew, role=CrewMember.ROLE_HELMSMAN,
            participant=Person.objects.get(pk=self.helmsman.pk)
        )

    def test_edit_requires_login(self):
        url = reverse('SkaRe:crew_edit', kwargs={'crew_id': self.crew.pk})
        self.assertRedirects(self.client.get(url), f'/user/login/?next={url}', fetch_redirect_response=False)

    def test_edit_forbidden_for_stranger(self):
        self.client.login(username='editstranger', password='pw')
        response = self.client.get(reverse('SkaRe:crew_edit', kwargs={'crew_id': self.crew.pk}))
        self.assertEqual(response.status_code, 302)

    def test_edit_get_renders_form(self):
        self.client.login(username='editowner', password='pw')
        response = self.client.get(reverse('SkaRe:crew_edit', kwargs={'crew_id': self.crew.pk}))
        self.assertEqual(response.status_code, 200)

    def test_edit_post_updates_crew(self):
        self.client.login(username='editowner', password='pw')
        response = self.client.post(
            reverse('SkaRe:crew_edit', kwargs={'crew_id': self.crew.pk}),
            {
                'boat': self.boat.pk,
                'category': Crew.CATEGORY_R,
                'helmsman': self.new_helm.pk,
            }
        )
        self.crew.refresh_from_db()
        self.assertEqual(self.crew.category, Crew.CATEGORY_R)
        self.assertRedirects(
            response,
            reverse('SkaRe:crew_detail', kwargs={'crew_id': self.crew.pk}),
            fetch_redirect_response=False,
        )

    def test_delete_requires_login(self):
        url = reverse('SkaRe:crew_delete', kwargs={'crew_id': self.crew.pk})
        self.assertRedirects(self.client.get(url), f'/user/login/?next={url}', fetch_redirect_response=False)

    def test_delete_removes_crew(self):
        self.client.login(username='editowner', password='pw')
        self.client.post(reverse('SkaRe:crew_delete', kwargs={'crew_id': self.crew.pk}))
        self.assertFalse(Crew.objects.filter(pk=self.crew.pk).exists())

    def test_delete_forbidden_for_stranger(self):
        self.client.login(username='editstranger', password='pw')
        self.client.post(reverse('SkaRe:crew_delete', kwargs={'crew_id': self.crew.pk}))
        self.assertTrue(Crew.objects.filter(pk=self.crew.pk).exists())
```

- [ ] **Step 2: Run tests — expect failure**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_views.CrewEditDeleteViewTest -v 2
```

Expected: `NoReverseMatch` for `crew_edit`.

- [ ] **Step 3: Add edit and delete views to `views.py`**

```python
@login_required
def crew_edit(request, crew_id):
    """Edit an existing crew."""
    crew = get_object_or_404(Crew, id=crew_id)
    if not crew.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to edit this crew.'))
        return redirect('SkaRe:crew_list')

    is_infodesk = request.user.groups.filter(name='InfoDesk').exists()
    if not EventSettings.is_crew_registration_open() and not is_infodesk:
        messages.error(request, _('Crew registration is closed.'))
        return redirect('SkaRe:crew_detail', crew_id=crew_id)

    # Build initial data from existing crew
    helmsman_member = crew.members.filter(role=CrewMember.ROLE_HELMSMAN).first()
    crew_members = list(crew.members.filter(role=CrewMember.ROLE_CREW).values_list('participant_id', flat=True))

    initial = {
        'boat': crew.boat_id,
        'category': crew.category,
        'helmsman': helmsman_member.participant_id if helmsman_member else None,
    }
    for i, pid in enumerate(crew_members[:4], start=1):
        initial[f'crew_member_{i}'] = pid

    form = CrewRegistrationForm(user=request.user, data=request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        boat = form.cleaned_data['boat']
        category = form.cleaned_data['category']
        # Check uniqueness excluding current crew
        if Crew.objects.filter(boat=boat, category=category).exclude(pk=crew_id).exists():
            form.add_error(None, _('A crew for this boat and category already exists.'))
        else:
            with transaction.atomic():
                crew.boat = boat
                crew.category = category
                crew.save()
                crew.members.all().delete()
                CrewMember.objects.create(
                    crew=crew, role=CrewMember.ROLE_HELMSMAN,
                    participant=form.cleaned_data['helmsman'],
                )
                for i in range(1, 5):
                    person = form.cleaned_data.get(f'crew_member_{i}')
                    if person:
                        CrewMember.objects.create(crew=crew, role=CrewMember.ROLE_CREW, participant=person)
            messages.success(request, _('Crew updated successfully.'))
            return redirect('SkaRe:crew_detail', crew_id=crew.id)

    crew_fields = [
        ('helmsman', _('Helmsman')),
        ('crew_member_1', _('Crew member 1')),
        ('crew_member_2', _('Crew member 2')),
        ('crew_member_3', _('Crew member 3')),
        ('crew_member_4', _('Crew member 4')),
    ]
    return render(request, 'SkaRe/crews/edit.html', {'form': form, 'crew': crew, 'crew_fields': crew_fields})


@login_required
def crew_delete(request, crew_id):
    """Delete a crew."""
    crew = get_object_or_404(Crew, id=crew_id)
    if not crew.can_be_edited(request.user):
        messages.error(request, _('You do not have permission to delete this crew.'))
        return redirect('SkaRe:crew_list')

    if request.method == 'POST':
        crew.delete()
        messages.success(request, _('Crew deleted.'))
        return redirect('SkaRe:crew_list')

    return render(request, 'SkaRe/crews/confirm_delete.html', {'crew': crew})
```

Also update `crew_register` to pass `crew_fields` to template context (replace the `return render(...)` at the end):

```python
    crew_fields = [
        ('helmsman', _('Helmsman')),
        ('crew_member_1', _('Crew member 1')),
        ('crew_member_2', _('Crew member 2')),
        ('crew_member_3', _('Crew member 3')),
        ('crew_member_4', _('Crew member 4')),
    ]
    return render(request, 'SkaRe/crews/register.html', {'form': form, 'crew_fields': crew_fields})
```

- [ ] **Step 4: Add URLs**

```python
path('crews/<int:crew_id>/edit/', views.crew_edit, name='crew_edit'),
path('crews/<int:crew_id>/delete/', views.crew_delete, name='crew_delete'),
```

- [ ] **Step 5: Create edit and confirm_delete templates**

Create `SkaRe/templates/SkaRe/crews/edit.html` (same structure as `register.html`, pre-filled):

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Edit Crew" %} - SkaRe{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8 offset-md-2">
        <h1 class="mb-4"><i class="bi bi-pencil-fill"></i> {% trans "Edit Crew" %}</h1>

        {% if form.non_field_errors %}
            <div class="alert alert-danger">{{ form.non_field_errors }}</div>
        {% endif %}

        <form method="post" novalidate>
            {% csrf_token %}

            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">{% trans "Crew" %}</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="{{ form.boat.id_for_label }}" class="form-label">{{ form.boat.label }} <span class="text-danger">*</span></label>
                            {{ form.boat }}
                            {% if form.boat.errors %}<div class="text-danger small">{{ form.boat.errors }}</div>{% endif %}
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="{{ form.category.id_for_label }}" class="form-label">{{ form.category.label }} <span class="text-danger">*</span></label>
                            {{ form.category }}
                            {% if form.category.errors %}<div class="text-danger small">{{ form.category.errors }}</div>{% endif %}
                        </div>
                    </div>
                </div>
            </div>

            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">{% trans "Crew Members" %}</h5>
                </div>
                <div class="card-body">
                    {% for field_name, label in crew_fields %}
                        <div class="row mb-2 align-items-center">
                            <div class="col-md-3"><span class="form-control-plaintext fw-semibold">{{ label }}</span></div>
                            <div class="col-md-9">
                                {% if field_name == 'helmsman' %}{{ form.helmsman }}{% if form.helmsman.errors %}<div class="text-danger small">{{ form.helmsman.errors }}</div>{% endif %}
                                {% elif field_name == 'crew_member_1' %}{{ form.crew_member_1 }}
                                {% elif field_name == 'crew_member_2' %}{{ form.crew_member_2 }}
                                {% elif field_name == 'crew_member_3' %}{{ form.crew_member_3 }}
                                {% elif field_name == 'crew_member_4' %}{{ form.crew_member_4 }}
                                {% endif %}
                            </div>
                        </div>
                    {% endfor %}
                    <div class="form-text">{% trans "Helmsman required; up to 4 crew members." %}</div>
                </div>
            </div>

            <div class="d-flex gap-2">
                <button type="submit" class="btn btn-primary"><i class="bi bi-check-circle"></i> {% trans "Save changes" %}</button>
                <a href="{% url 'SkaRe:crew_detail' crew_id=crew.pk %}" class="btn btn-secondary">{% trans "Cancel" %}</a>
            </div>
        </form>
    </div>
</div>
{% endblock %}
```

Create `SkaRe/templates/SkaRe/crews/confirm_delete.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Delete Crew" %} - SkaRe{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-6 offset-md-3">
        <div class="card border-danger">
            <div class="card-header bg-danger text-white">
                <h5 class="mb-0"><i class="bi bi-exclamation-triangle"></i> {% trans "Delete Crew" %}</h5>
            </div>
            <div class="card-body">
                <p>{% blocktrans with crew=crew %}Are you sure you want to delete crew <strong>{{ crew }}</strong>? This action cannot be undone.{% endblocktrans %}</p>
                <form method="post">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-danger">{% trans "Yes, delete" %}</button>
                    <a href="{% url 'SkaRe:crew_detail' crew_id=crew.pk %}" class="btn btn-secondary ms-2">{% trans "Cancel" %}</a>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Run tests — expect pass**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_views -v 2
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/views.py SkaRe/urls.py SkaRe/templates/SkaRe/crews/ SkaRe/tests/test_crew_views.py
git commit -m "feat: add crew edit and delete views"
```

---

### Task 10: Home page crew buttons

**Files:**
- Modify: `SkaRe/templates/SkaRe/home.html`

- [ ] **Step 1: Read `home.html` to find the authenticated section**

Open `SkaRe/templates/SkaRe/home.html` and find the `{% if user.is_authenticated %}` block. Locate where the "Register" buttons and "My Registrations" buttons are.

- [ ] **Step 2: Add crew buttons**

In the "Register" section, add alongside the existing boat button:

```html
<a class="btn btn-primary btn-lg me-2 mb-2" href="{% url 'SkaRe:crew_register' %}" role="button">
    <i class="bi bi-people-fill"></i> {% trans "Register a Crew" %}
</a>
```

In the "My Registrations" section, add alongside the existing boat button:

```html
<a class="btn btn-info btn-lg me-2 mb-2" href="{% url 'SkaRe:crew_list' %}" role="button">
    <i class="bi bi-people-fill"></i> {% trans "My Crews" %}
</a>
```

- [ ] **Step 3: Smoke test manually**

```bash
.venv/bin/python manage.py runserver
```

Open `http://localhost:8000/`, log in, verify the two new buttons appear and their links work.

- [ ] **Step 4: Commit**

```bash
git add SkaRe/templates/SkaRe/home.html
git commit -m "feat: add crew buttons to home page"
```

---

### Task 11: CSV export

**Files:**
- Modify: `SkaRe/views.py`
- Modify: `SkaRe/urls.py`
- Modify: `SkaRe/tests/test_crew_views.py`

- [ ] **Step 1: Write failing test**

Append to `SkaRe/tests/test_crew_views.py`:

```python
class CrewExportCsvTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(username='csvstaff', password='pw', is_staff=True)
        self.regular = _make_user('csvregular')
        self.user = _make_user('csvowner')
        self.unit = _make_unit(self.user)
        self.helmsman = _make_person(self.unit)
        self.boat = _make_boat(self.user)
        self.crew = Crew.objects.create(
            boat=self.boat, category=Crew.CATEGORY_S, created_by=self.user
        )
        CrewMember.objects.create(
            crew=self.crew, role=CrewMember.ROLE_HELMSMAN,
            participant=Person.objects.get(pk=self.helmsman.pk),
        )

    def test_export_requires_staff(self):
        self.client.login(username='csvregular', password='pw')
        response = self.client.get(reverse('SkaRe:crew_export_csv'))
        self.assertEqual(response.status_code, 302)

    def test_export_returns_csv_for_staff(self):
        self.client.login(username='csvstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_export_contains_helmsman_row(self):
        self.client.login(username='csvstaff', password='pw')
        response = self.client.get(reverse('SkaRe:crew_export_csv'))
        content = response.content.decode('utf-8-sig')
        self.assertIn('Jan', content)
        self.assertIn(Crew.CATEGORY_S, content)
```

- [ ] **Step 2: Run tests — expect failure**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_views.CrewExportCsvTest -v 2
```

Expected: `NoReverseMatch` for `crew_export_csv`.

- [ ] **Step 3: Add CSV export view to `views.py`**

Add import at top of views.py (already imported `csv` — check):

```python
from django.http import HttpResponse
```

Add view:

```python
@login_required
def crew_export_csv(request):
    """Staff-only CSV export of all crews and their members."""
    if not request.user.is_staff:
        messages.error(request, _('Staff access required.'))
        return redirect('SkaRe:home')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="crews.csv"'
    # BOM for Excel UTF-8 compatibility
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'crew_id', 'category', 'boat_sail_number', 'boat_name',
        'boat_class', 'sail_area', 'role',
        'first_name', 'last_name', 'date_of_birth', 'scout_category',
        'participant_type', 'unit_name',
    ])

    members = (
        CrewMember.objects
        .select_related('crew', 'crew__boat', 'crew__boat__boat_class', 'participant')
        .order_by('crew__id', '-role')
    )

    for m in members:
        crew = m.crew
        person = m.participant
        participant_type = ''
        unit_name = ''
        if hasattr(person, 'regularparticipant'):
            participant_type = 'RegularParticipant'
            unit_name = person.regularparticipant.unit.entity.scout_unit_name
        elif hasattr(person, 'individualparticipant'):
            participant_type = 'IndividualParticipant'
        elif hasattr(person, 'organizer'):
            participant_type = 'Organizer'

        writer.writerow([
            crew.id,
            crew.category,
            crew.boat.sail_number,
            crew.boat.name,
            crew.boat.boat_class.name if crew.boat.boat_class else '',
            crew.boat.sail_area or '',
            m.role,
            person.first_name,
            person.last_name,
            person.date_of_birth,
            person.category or '',
            participant_type,
            unit_name,
        ])

    return response
```

- [ ] **Step 4: Add URL**

```python
path('crews/export/csv/', views.crew_export_csv, name='crew_export_csv'),
```

> **Important:** Place this URL **before** `crews/<int:crew_id>/` to avoid `export` being matched as a `crew_id`.

- [ ] **Step 5: Run tests — expect pass**

```bash
.venv/bin/python manage.py test SkaRe.tests.test_crew_views.CrewExportCsvTest -v 2
```

Expected: all 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add SkaRe/views.py SkaRe/urls.py SkaRe/tests/test_crew_views.py
git commit -m "feat: add crew CSV export"
```

---

### Task 12: Admin registration

**Files:**
- Modify: `SkaRe/admin.py`

- [ ] **Step 1: Open `SkaRe/admin.py` and add Crew admin**

Add imports at the top alongside existing imports:

```python
from .models import (
    Unit, RegularParticipant, IndividualParticipant, Organizer,
    BoatClass, Boat, EventSettings, Crew, CrewMember,
)
```

Add `CrewMemberInline` and `CrewAdmin`:

```python
class CrewMemberInline(admin.TabularInline):
    model = CrewMember
    extra = 0
    fields = ('role', 'participant')
    readonly_fields = ()


@admin.register(Crew)
class CrewAdmin(admin.ModelAdmin):
    list_display = ('id', 'boat', 'category', 'created_by', 'member_count', 'created_at')
    list_filter = ('category',)
    search_fields = ('boat__name', 'boat__sail_number', 'created_by__username')
    inlines = [CrewMemberInline]

    @admin.display(description='Members')
    def member_count(self, obj):
        return obj.members.count()
```

Find the existing `BoatAdmin` class and add `willing_to_lend` to its `list_display` and fieldsets. Locate the line:

```python
list_display = (...)
```

and add `'willing_to_lend'` to the tuple. If there's a `fieldsets` definition, add `'willing_to_lend'` to the appropriate section; otherwise Django will include it automatically.

- [ ] **Step 2: Smoke test the admin**

```bash
.venv/bin/python manage.py runserver
```

Open `http://localhost:8000/admin/`, log in as a superuser, verify:
- "Crews" appears in the sidebar
- Boat list shows "Willing to lend" column
- Crew admin shows inline members

- [ ] **Step 3: Commit**

```bash
git add SkaRe/admin.py
git commit -m "feat: register Crew in admin; add willing_to_lend to BoatAdmin"
```

---

### Task 13: Full test suite verification

- [ ] **Step 1: Run all tests**

```bash
.venv/bin/python manage.py test SkaRe -v 2
```

Expected: all tests pass, zero failures.

- [ ] **Step 2: Check for migration consistency**

```bash
.venv/bin/python manage.py migrate --check
```

Expected: no pending migrations.

- [ ] **Step 3: Final commit if any fixes were needed**

If any test failures required fixes, commit them:

```bash
git add -p
git commit -m "fix: resolve test failures from crew registration feature"
```
