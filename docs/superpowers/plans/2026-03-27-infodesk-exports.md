# InfoDesk — Exports (Kitchen & Medical)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the InfoDesk exports page with kitchen and medical reports, each available as a CSV download and a browser print view.

**Architecture:** All views in `SkaRe/views/exports.py`. Both reports filter to `attendance_status = ARRIVED`. Kitchen: grouped by entity, dietary restrictions per person. Medical: persons with non-empty `health_restrictions`, sorted by entity. Templates in `SkaRe/templates/SkaRe/exports/`.

**Tech Stack:** Django 6.0, Python 3.12, Bootstrap 5.3.0, `uv run python manage.py ...` for all commands.

**Starting state:** Plans A, B, C complete. Exports stub views return 200. 196+ tests passing.

**Spec:** `docs/superpowers/specs/2026-03-26-plachtis-overhaul-design.md` — Section 4 (Exports subsection).

---

## File Map

| File | Action | Purpose |
|------|---------|---------|
| `SkaRe/views/exports.py` | Replace stubs | All export views |
| `SkaRe/templates/SkaRe/exports/index.html` | Create | Exports landing page |
| `SkaRe/templates/SkaRe/exports/kitchen_print.html` | Create | Kitchen print view |
| `SkaRe/templates/SkaRe/exports/medical_print.html` | Create | Medical print view |
| `SkaRe/tests/test_exports.py` | Create | Export view tests |

---

## Task 1: Implement export views

**Files:**
- Replace: `SkaRe/views/exports.py`

- [ ] **Step 1: Write failing tests**

Create `SkaRe/tests/test_exports.py`:

```python
import csv
import io
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from SkaRe.models import (
    Entity, Unit, RegularParticipant, IndividualParticipant, Organizer, Person,
)


def _make_infodesk():
    user = User.objects.create_user(username='desk', password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


def _make_unit(user, name='Bobři'):
    entity = Entity.objects.create(
        created_by=user, contact_email='u@example.com',
        contact_phone='+420777111222', scout_unit_name=name,
    )
    return Unit.objects.create(entity=entity, contact_person_name='Leader')


def _make_participant(unit, arrived=False, diet_vegan=False, health=''):
    p = RegularParticipant.objects.create(
        unit=unit, first_name='Jan', last_name='Novák',
        date_of_birth=date(2000, 1, 1),
        diet_vegan=diet_vegan,
        health_restrictions=health,
    )
    if arrived:
        p.attendance_status = Person.AttendanceStatus.ARRIVED
        p.save()
    return p


def _make_individual(user, arrived=False, health=''):
    entity = Entity.objects.create(
        created_by=user, contact_email='i@example.com',
        contact_phone='+420777333444',
    )
    p = IndividualParticipant.objects.create(
        entity=entity, first_name='Marie', last_name='Nováková',
        date_of_birth=date(1990, 5, 10), health_restrictions=health,
    )
    if arrived:
        p.attendance_status = Person.AttendanceStatus.ARRIVED
        p.save()
    return p


class ExportsIndexTest(TestCase):
    def setUp(self):
        self.client = Client()
        _make_infodesk()
        self.client.login(username='desk', password='pw')

    def test_index_returns_200(self):
        url = reverse('SkaRe:exports_index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_index_has_kitchen_link(self):
        response = self.client.get(reverse('SkaRe:exports_index'))
        self.assertContains(response, reverse('SkaRe:exports_kitchen_csv'))

    def test_index_has_medical_link(self):
        response = self.client.get(reverse('SkaRe:exports_index'))
        self.assertContains(response, reverse('SkaRe:exports_medical_csv'))


class KitchenCsvTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_csv_only_includes_arrived_people(self):
        unit = _make_unit(self.owner)
        arrived = _make_participant(unit, arrived=True)
        not_arrived = _make_participant(unit, arrived=False)
        response = self.client.get(reverse('SkaRe:exports_kitchen_csv'))
        content = response.content.decode('utf-8-sig')
        self.assertIn(arrived.last_name, content)
        self.assertNotIn('Jan Novák\n', content)  # not arrived has no distinct name but count differs
        # More specific: count rows (header + 1 arrived person)
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        self.assertEqual(len(rows), 2)  # header + 1

    def test_csv_content_type_is_csv(self):
        response = self.client.get(reverse('SkaRe:exports_kitchen_csv'))
        self.assertIn('text/csv', response['Content-Type'])

    def test_csv_includes_dietary_columns(self):
        unit = _make_unit(self.owner)
        _make_participant(unit, arrived=True, diet_vegan=True)
        response = self.client.get(reverse('SkaRe:exports_kitchen_csv'))
        content = response.content.decode('utf-8-sig')
        self.assertIn('Vegan', content)

    def test_csv_has_bom_for_excel(self):
        response = self.client.get(reverse('SkaRe:exports_kitchen_csv'))
        self.assertTrue(response.content.startswith(b'\xef\xbb\xbf'))


class KitchenPrintTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_print_view_returns_200(self):
        response = self.client.get(reverse('SkaRe:exports_kitchen_print'))
        self.assertEqual(response.status_code, 200)

    def test_print_view_shows_arrived_people(self):
        unit = _make_unit(self.owner, 'Racci')
        _make_participant(unit, arrived=True)
        response = self.client.get(reverse('SkaRe:exports_kitchen_print'))
        self.assertContains(response, 'Racci')

    def test_print_view_excludes_not_arrived(self):
        unit = _make_unit(self.owner, 'Racci')
        _make_participant(unit, arrived=False)
        response = self.client.get(reverse('SkaRe:exports_kitchen_print'))
        self.assertNotContains(response, 'Racci')


class MedicalCsvTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_csv_only_includes_arrived_people_with_health_restrictions(self):
        unit = _make_unit(self.owner)
        arrived_sick = _make_participant(unit, arrived=True, health='peanut allergy')
        arrived_healthy = _make_participant(unit, arrived=True, health='')
        not_arrived_sick = _make_participant(unit, arrived=False, health='asthma')
        response = self.client.get(reverse('SkaRe:exports_medical_csv'))
        content = response.content.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        self.assertEqual(len(rows), 2)  # header + 1 arrived sick person

    def test_medical_csv_contains_health_info(self):
        unit = _make_unit(self.owner)
        _make_participant(unit, arrived=True, health='carries EpiPen')
        response = self.client.get(reverse('SkaRe:exports_medical_csv'))
        content = response.content.decode('utf-8-sig')
        self.assertIn('carries EpiPen', content)

    def test_medical_csv_content_type(self):
        response = self.client.get(reverse('SkaRe:exports_medical_csv'))
        self.assertIn('text/csv', response['Content-Type'])


class MedicalPrintTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_print_view_returns_200(self):
        response = self.client.get(reverse('SkaRe:exports_medical_print'))
        self.assertEqual(response.status_code, 200)

    def test_print_view_shows_health_info(self):
        unit = _make_unit(self.owner, 'Bobři')
        _make_participant(unit, arrived=True, health='severe nut allergy')
        response = self.client.get(reverse('SkaRe:exports_medical_print'))
        self.assertContains(response, 'severe nut allergy')

    def test_print_view_excludes_arrived_with_no_health_restrictions(self):
        unit = _make_unit(self.owner, 'Bobři')
        _make_participant(unit, arrived=True, health='')
        response = self.client.get(reverse('SkaRe:exports_medical_print'))
        self.assertNotContains(response, 'Novák')
```

- [ ] **Step 2: Run — expect FAIL**

```bash
uv run python manage.py test SkaRe.tests.test_exports --verbosity=0 2>&1 | tail -5
```

Expected: FAIL (stub views return plain HttpResponse, not rendered templates/CSV).

- [ ] **Step 3: Implement SkaRe/views/exports.py**

Replace `SkaRe/views/exports.py` with:

```python
import csv
from datetime import date
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Prefetch
from django.utils.translation import gettext as _
from ..permissions import infodesk_required
from ..models import (
    Person, RegularParticipant, IndividualParticipant, Organizer,
    Unit, Entity,
)

DIET_FIELDS = [
    ('diet_vegan', _('Vegan')),
    ('diet_vegetarian', _('Vegetarian')),
    ('diet_gluten_free', _('Gluten-free')),
    ('diet_lactose_free', _('Lactose/dairy-free')),
    ('diet_no_eggs', _('No eggs')),
    ('diet_no_peanuts', _('No peanuts')),
    ('diet_no_tree_nuts', _('No tree nuts')),
    ('diet_no_soy', _('No soy')),
    ('diet_no_fish', _('No fish')),
    ('diet_no_fruits', _('No fruits')),
]


def _age(date_of_birth):
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def _arrived_unit_participants():
    """Return RegularParticipants with attendance_status=ARRIVED, grouped by unit."""
    return (
        RegularParticipant.objects.filter(
            attendance_status=Person.AttendanceStatus.ARRIVED
        ).select_related('unit__entity').order_by(
            'unit__entity__scout_unit_name', 'last_name', 'first_name'
        )
    )


def _arrived_individuals():
    return (
        IndividualParticipant.objects.filter(
            attendance_status=Person.AttendanceStatus.ARRIVED
        ).select_related('entity').order_by('last_name', 'first_name')
    )


def _arrived_organizers():
    return (
        Organizer.objects.filter(
            attendance_status=Person.AttendanceStatus.ARRIVED
        ).select_related('entity').order_by('last_name', 'first_name')
    )


@infodesk_required
def exports_index(request):
    return render(request, 'SkaRe/exports/index.html')


@infodesk_required
def exports_kitchen_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="kitchen_report.csv"'
    response.write('\ufeff')  # UTF-8 BOM for Excel

    writer = csv.writer(response)
    diet_labels = [label for _, label in DIET_FIELDS]
    writer.writerow([
        _('Name'), _('Type'), _('Unit/Group'),
        *diet_labels,
        _('Other dietary restrictions'),
    ])

    for p in _arrived_unit_participants():
        diet_values = [getattr(p, field) for field, _ in DIET_FIELDS]
        writer.writerow([
            str(p), _('Unit member'), p.unit.entity.scout_unit_name,
            *diet_values, p.diet_other,
        ])

    for p in _arrived_individuals():
        diet_values = [getattr(p, field) for field, _ in DIET_FIELDS]
        writer.writerow([
            str(p), _('Individual'), _('Individual participant'),
            *diet_values, p.diet_other,
        ])

    for p in _arrived_organizers():
        diet_values = [getattr(p, field) for field, _ in DIET_FIELDS]
        writer.writerow([
            str(p), _('Organizer'), _('Organizer'),
            *diet_values, p.diet_other,
        ])

    return response


@infodesk_required
def exports_kitchen_print(request):
    # Build grouped data for the print view
    unit_participants = _arrived_unit_participants()
    units_map = {}
    for p in unit_participants:
        uid = p.unit.pk
        if uid not in units_map:
            units_map[uid] = {
                'unit': p.unit,
                'with_restrictions': [],
                'clean_count': 0,
            }
        if p.dietary_summary():
            units_map[uid]['with_restrictions'].append(p)
        else:
            units_map[uid]['clean_count'] += 1

    individuals = list(_arrived_individuals())
    organizers = list(_arrived_organizers())

    total = (
        sum(len(d['with_restrictions']) + d['clean_count'] for d in units_map.values())
        + len(individuals)
        + len(organizers)
    )

    return render(request, 'SkaRe/exports/kitchen_print.html', {
        'units_data': list(units_map.values()),
        'individuals': individuals,
        'organizers': organizers,
        'organizers_with_restrictions': [o for o in organizers if o.dietary_summary()],
        'organizers_clean_count': sum(1 for o in organizers if not o.dietary_summary()),
        'total': total,
    })


@infodesk_required
def exports_medical_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="medical_report.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        _('Name'), _('Date of birth'), _('Age'), _('Type'), _('Unit/Group'),
        _('Contact phone'), _('Health restrictions'),
    ])

    for p in _arrived_unit_participants():
        if not p.health_restrictions:
            continue
        writer.writerow([
            str(p), p.date_of_birth, _age(p.date_of_birth),
            _('Unit member'), p.unit.entity.scout_unit_name,
            p.unit.entity.contact_phone, p.health_restrictions,
        ])

    for p in _arrived_individuals():
        if not p.health_restrictions:
            continue
        writer.writerow([
            str(p), p.date_of_birth, _age(p.date_of_birth),
            _('Individual'), _('Individual participant'),
            p.entity.contact_phone, p.health_restrictions,
        ])

    for p in _arrived_organizers():
        if not p.health_restrictions:
            continue
        writer.writerow([
            str(p), p.date_of_birth, _age(p.date_of_birth),
            _('Organizer'), _('Organizer'),
            p.entity.contact_phone, p.health_restrictions,
        ])

    return response


@infodesk_required
def exports_medical_print(request):
    unit_participants = [
        p for p in _arrived_unit_participants() if p.health_restrictions
    ]
    individuals = [p for p in _arrived_individuals() if p.health_restrictions]
    organizers = [p for p in _arrived_organizers() if p.health_restrictions]

    return render(request, 'SkaRe/exports/medical_print.html', {
        'unit_participants': unit_participants,
        'individuals': individuals,
        'organizers': organizers,
    })
```

- [ ] **Step 4: Run — expect FAIL on template tests**

```bash
uv run python manage.py test SkaRe.tests.test_exports --verbosity=0 2>&1 | tail -5
```

Expected: CSV tests PASS (no templates needed), print view tests FAIL (TemplateDoesNotExist).

---

## Task 2: Export templates

**Files:**
- Create: `SkaRe/templates/SkaRe/exports/index.html`
- Create: `SkaRe/templates/SkaRe/exports/kitchen_print.html`
- Create: `SkaRe/templates/SkaRe/exports/medical_print.html`

- [ ] **Step 1: Create exports/index.html**

Create `SkaRe/templates/SkaRe/exports/index.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Exports" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-3"><i class="bi bi-file-earmark-text"></i> {% trans "Reports &amp; Exports" %}</h1>
<p>
  <a href="{% url 'SkaRe:infodesk_dashboard' %}" class="btn btn-outline-secondary btn-sm">
    <i class="bi bi-arrow-left"></i> {% trans "Dashboard" %}
  </a>
</p>
<p class="text-muted">{% trans "All reports include only people with attendance status: Arrived." %}</p>

<div class="row">
  <div class="col-md-5">
    <div class="card mb-4">
      <div class="card-header fw-bold"><i class="bi bi-egg-fried"></i> {% trans "Kitchen report" %}</div>
      <div class="card-body">
        <p class="card-text text-muted">{% trans "People present grouped by unit, with dietary restrictions." %}</p>
        <a href="{% url 'SkaRe:exports_kitchen_csv' %}" class="btn btn-outline-dark btn-sm me-2">
          <i class="bi bi-download"></i> {% trans "Download CSV" %}
        </a>
        <a href="{% url 'SkaRe:exports_kitchen_print' %}" class="btn btn-primary btn-sm" target="_blank">
          <i class="bi bi-printer"></i> {% trans "Print view" %}
        </a>
      </div>
    </div>
  </div>
  <div class="col-md-5">
    <div class="card mb-4">
      <div class="card-header fw-bold"><i class="bi bi-heart-pulse"></i> {% trans "Medical report" %}</div>
      <div class="card-body">
        <p class="card-text text-muted">{% trans "People present with health restrictions, sorted by unit." %}</p>
        <a href="{% url 'SkaRe:exports_medical_csv' %}" class="btn btn-outline-dark btn-sm me-2">
          <i class="bi bi-download"></i> {% trans "Download CSV" %}
        </a>
        <a href="{% url 'SkaRe:exports_medical_print' %}" class="btn btn-primary btn-sm" target="_blank">
          <i class="bi bi-printer"></i> {% trans "Print view" %}
        </a>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Create exports/kitchen_print.html**

Create `SkaRe/templates/SkaRe/exports/kitchen_print.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Kitchen Report" %} - SkaRe{% endblock %}

{% block extra_css %}
<style>
@media print {
  nav, .btn, .no-print { display: none !important; }
  body { font-size: 11pt; }
  h2 { font-size: 13pt; }
}
</style>
{% endblock %}

{% block content %}
<div class="mb-3 no-print">
  <a href="{% url 'SkaRe:exports_index' %}" class="btn btn-outline-secondary btn-sm me-2">
    <i class="bi bi-arrow-left"></i> {% trans "Back" %}
  </a>
  <button onclick="window.print()" class="btn btn-primary btn-sm">
    <i class="bi bi-printer"></i> {% trans "Print" %}
  </button>
</div>

<h1>{% trans "Kitchen Report" %}</h1>

{% for data in units_data %}
<div class="mb-3">
  <h2>{% trans "Unit" %} &ldquo;{{ data.unit.entity.scout_unit_name }}&rdquo; &mdash;
    {{ data.with_restrictions|length|add:data.clean_count }} {% trans "people present" %}
    {% if data.with_restrictions %}({{ data.with_restrictions|length }} {% trans "with dietary restrictions" %}){% else %}({% trans "no dietary restrictions" %}){% endif %}
  </h2>
  {% if data.with_restrictions %}
  <ul>
    {% for p in data.with_restrictions %}
    <li>{{ p }}: {{ p.dietary_summary }}</li>
    {% endfor %}
  </ul>
  {% endif %}
  {% if data.clean_count > 0 %}
  <p>{{ data.clean_count }} {% trans "people: no dietary restrictions" %}</p>
  {% endif %}
</div>
{% endfor %}

{% for p in individuals %}
<div class="mb-2">
  <h2>{% trans "Individual" %} &ldquo;{{ p }}&rdquo; &mdash; 1 {% trans "person present" %}
    {% if p.dietary_summary %}({{ p.dietary_summary }}){% else %}({% trans "no restrictions" %}){% endif %}
  </h2>
</div>
{% endfor %}

{% if organizers %}
<div class="mb-3">
  <h2>{% trans "Organizers" %} &mdash; {{ organizers|length }} {% trans "people present" %}
    {% if organizers_with_restrictions %}({{ organizers_with_restrictions|length }} {% trans "with dietary restrictions" %}){% else %}({% trans "no dietary restrictions" %}){% endif %}
  </h2>
  {% if organizers_with_restrictions %}
  <ul>
    {% for p in organizers_with_restrictions %}<li>{{ p }}: {{ p.dietary_summary }}</li>{% endfor %}
  </ul>
  {% endif %}
  {% if organizers_clean_count > 0 %}
  <p>{{ organizers_clean_count }} {% trans "people: no dietary restrictions" %}</p>
  {% endif %}
</div>
{% endif %}

<hr>
<strong>{% trans "TOTAL" %}: {{ total }} {% trans "people present" %}</strong>
{% endblock %}
```

- [ ] **Step 3: Create exports/medical_print.html**

Create `SkaRe/templates/SkaRe/exports/medical_print.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Medical Report" %} - SkaRe{% endblock %}

{% block extra_css %}
<style>
@media print {
  nav, .btn, .no-print { display: none !important; }
  body { font-size: 11pt; }
  .person-card { page-break-inside: avoid; border-bottom: 1px solid #ccc; padding: 6pt 0; }
}
</style>
{% endblock %}

{% block content %}
<div class="mb-3 no-print">
  <a href="{% url 'SkaRe:exports_index' %}" class="btn btn-outline-secondary btn-sm me-2">
    <i class="bi bi-arrow-left"></i> {% trans "Back" %}
  </a>
  <button onclick="window.print()" class="btn btn-primary btn-sm">
    <i class="bi bi-printer"></i> {% trans "Print" %}
  </button>
</div>

<h1>{% trans "Medical Report" %}</h1>
<p class="text-muted no-print">{% trans "People present with health restrictions." %}</p>

{% if unit_participants %}
<h2>{% trans "Unit members" %}</h2>
{% for p in unit_participants %}
<div class="person-card mb-2">
  <strong>{{ p }}</strong>, {{ p.date_of_birth|date:"Y" }} &mdash; {{ p.health_restrictions }}<br>
  <small class="text-muted">
    {% trans "Unit" %}: {{ p.unit.entity.scout_unit_name }} |
    {% trans "Contact" %}: {{ p.unit.entity.contact_phone }}
  </small>
</div>
{% endfor %}
{% endif %}

{% if individuals %}
<h2>{% trans "Individual participants" %}</h2>
{% for p in individuals %}
<div class="person-card mb-2">
  <strong>{{ p }}</strong>, {{ p.date_of_birth|date:"Y" }} &mdash; {{ p.health_restrictions }}<br>
  <small class="text-muted">
    {% trans "Individual participant" %} |
    {% trans "Contact" %}: {{ p.entity.contact_phone }}
  </small>
</div>
{% endfor %}
{% endif %}

{% if organizers %}
<h2>{% trans "Organizers" %}</h2>
{% for p in organizers %}
<div class="person-card mb-2">
  <strong>{{ p }}</strong>, {{ p.date_of_birth|date:"Y" }} &mdash; {{ p.health_restrictions }}<br>
  <small class="text-muted">
    {% trans "Organizer" %} |
    {% trans "Contact" %}: {{ p.entity.contact_phone }}
  </small>
</div>
{% endfor %}
{% endif %}

{% if not unit_participants and not individuals and not organizers %}
<p class="text-muted">{% trans "No people with health restrictions present." %}</p>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Run all export tests**

```bash
uv run python manage.py test SkaRe.tests.test_exports --verbosity=0 2>&1 | tail -5
```

Expected: All PASS.

- [ ] **Step 5: Run full suite**

```bash
uv run python manage.py test SkaRe --verbosity=0 2>&1 | tail -3
```

Expected: OK.

- [ ] **Step 6: Commit**

```bash
git add SkaRe/views/exports.py SkaRe/templates/SkaRe/exports/ SkaRe/tests/test_exports.py
git commit -m "feat: InfoDesk exports — kitchen and medical reports (CSV + print)"
```
