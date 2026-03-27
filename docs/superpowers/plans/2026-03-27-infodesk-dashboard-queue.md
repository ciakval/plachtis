# InfoDesk — Dashboard & Registration Queue

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the InfoDesk dashboard and registration validation queue views, wiring up the URL structure shared by all InfoDesk plans.

**Architecture:** Two new view files (`views/infodesk.py`, `views/tickets.py`, `views/attendance.py`, `views/exports.py`) — all stubbed here; only `infodesk.py` is implemented. URL routing covers all four domains so Plans B/C/D just add implementations. All views behind `@infodesk_required`.

**Tech Stack:** Django 6.0, Python 3.12, Bootstrap 5.3.0, `uv run python manage.py ...` for all commands.

**Starting state:** 196 tests passing. All InfoDesk URLs currently 404.

**Spec:** `docs/superpowers/specs/2026-03-26-plachtis-overhaul-design.md` — Section 4 (dashboard + registration queue subsections).

---

## File Map

| File | Action | Purpose |
|------|---------|---------|
| `SkaRe/views/infodesk.py` | Create | Dashboard + registration queue views |
| `SkaRe/views/attendance.py` | Create | Stub (implemented in Plan B) |
| `SkaRe/views/tickets.py` | Create | Stub (implemented in Plan C) |
| `SkaRe/views/exports.py` | Create | Stub (implemented in Plan D) |
| `SkaRe/views/__init__.py` | Modify | Re-export all InfoDesk views |
| `SkaRe/urls.py` | Modify | Add all /infodesk/ URL patterns (full structure) |
| `SkaRe/templates/SkaRe/infodesk/dashboard.html` | Create | Dashboard template |
| `SkaRe/templates/SkaRe/infodesk/registrations.html` | Create | Registration queue template |
| `SkaRe/tests/test_infodesk_views.py` | Create | Dashboard + queue view tests |

---

## Task 1: Stub view files + URL routing

**Files:**
- Create: `SkaRe/views/infodesk.py`
- Create: `SkaRe/views/attendance.py`
- Create: `SkaRe/views/tickets.py`
- Create: `SkaRe/views/exports.py`
- Modify: `SkaRe/views/__init__.py`
- Modify: `SkaRe/urls.py`

- [ ] **Step 1: Create stub view files**

Create `SkaRe/views/infodesk.py`:

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from ..permissions import infodesk_required
from ..models import Entity, Unit, IndividualParticipant, Organizer, Person, SailTicket


@infodesk_required
def infodesk_dashboard(request):
    from django.db.models import Count, Q
    unconfirmed_count = Entity.objects.filter(confirmed=False).count()
    arrived_count = Person.objects.filter(attendance_status=Person.AttendanceStatus.ARRIVED).count()
    expected_count = Person.objects.filter(attendance_status=Person.AttendanceStatus.EXPECTED).count()
    not_coming_count = Person.objects.filter(attendance_status=Person.AttendanceStatus.NOT_COMING).count()
    on_water_count = SailTicket.objects.filter(status=SailTicket.Status.ON_WATER).count()
    return render(request, 'SkaRe/infodesk/dashboard.html', {
        'unconfirmed_count': unconfirmed_count,
        'arrived_count': arrived_count,
        'expected_count': expected_count,
        'not_coming_count': not_coming_count,
        'on_water_count': on_water_count,
    })


def _entity_row(entity):
    """Return (name, type_label) for an Entity."""
    if hasattr(entity, 'unit_profile'):
        return entity.scout_unit_name or f'Unit #{entity.pk}', _('Unit')
    elif hasattr(entity, 'individual_participant_profile'):
        return str(entity.individual_participant_profile), _('Individual')
    elif hasattr(entity, 'organizer_profile'):
        return str(entity.organizer_profile), _('Organizer')
    return f'Entity #{entity.pk}', _('Unknown')


@infodesk_required
def infodesk_registrations(request):
    entities = Entity.objects.select_related(
        'unit_profile',
        'individual_participant_profile',
        'organizer_profile',
    ).order_by('created_at')

    rows = []
    for entity in entities:
        name, type_label = _entity_row(entity)
        rows.append({'entity': entity, 'name': name, 'type': type_label})

    return render(request, 'SkaRe/infodesk/registrations.html', {'rows': rows})


@infodesk_required
def infodesk_confirm_entity(request, entity_id):
    if request.method != 'POST':
        return redirect('SkaRe:infodesk_registrations')
    entity = get_object_or_404(Entity, pk=entity_id)
    entity.confirmed = True
    entity.save(update_fields=['confirmed'])
    messages.success(request, _('Registration confirmed.'))
    return redirect('SkaRe:infodesk_registrations')


@infodesk_required
def infodesk_reject_entity(request, entity_id):
    if request.method != 'POST':
        return redirect('SkaRe:infodesk_registrations')
    entity = get_object_or_404(Entity, pk=entity_id)
    entity.confirmed = False
    entity.save(update_fields=['confirmed'])
    messages.success(request, _('Registration rejected.'))
    return redirect('SkaRe:infodesk_registrations')


@infodesk_required
def infodesk_bulk_confirm(request):
    if request.method != 'POST':
        return redirect('SkaRe:infodesk_registrations')
    ids = request.POST.getlist('entity_ids')
    if ids:
        Entity.objects.filter(pk__in=ids).update(confirmed=True)
        messages.success(request, _('%(n)d registrations confirmed.') % {'n': len(ids)})
    return redirect('SkaRe:infodesk_registrations')
```

Create `SkaRe/views/attendance.py`:

```python
from django.http import HttpResponse
from ..permissions import infodesk_required


@infodesk_required
def attendance_units_list(request):
    return HttpResponse('TODO: Plan B', status=200)


@infodesk_required
def attendance_unit_detail(request, unit_id):
    return HttpResponse('TODO: Plan B', status=200)


@infodesk_required
def attendance_individuals_list(request):
    return HttpResponse('TODO: Plan B', status=200)


@infodesk_required
def attendance_organizers_list(request):
    return HttpResponse('TODO: Plan B', status=200)


@infodesk_required
def attendance_set_status(request, person_id):
    return HttpResponse('TODO: Plan B', status=200)


@infodesk_required
def attendance_unit_mark_all_arrived(request, unit_id):
    return HttpResponse('TODO: Plan B', status=200)
```

Create `SkaRe/views/tickets.py`:

```python
from django.http import HttpResponse
from ..permissions import infodesk_required


@infodesk_required
def ticket_list(request):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_detail(request, ticket_id):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_set_status(request, ticket_id):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_pair_rfid(request, ticket_id):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_lookup(request):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_create_bulk(request):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_on_water(request):
    return HttpResponse('TODO: Plan C', status=200)


@infodesk_required
def ticket_export_csv(request):
    return HttpResponse('TODO: Plan C', status=200)
```

Create `SkaRe/views/exports.py`:

```python
from django.http import HttpResponse
from ..permissions import infodesk_required


@infodesk_required
def exports_index(request):
    return HttpResponse('TODO: Plan D', status=200)


@infodesk_required
def exports_kitchen_csv(request):
    return HttpResponse('TODO: Plan D', status=200)


@infodesk_required
def exports_kitchen_print(request):
    return HttpResponse('TODO: Plan D', status=200)


@infodesk_required
def exports_medical_csv(request):
    return HttpResponse('TODO: Plan D', status=200)


@infodesk_required
def exports_medical_print(request):
    return HttpResponse('TODO: Plan D', status=200)
```

- [ ] **Step 2: Update views/__init__.py**

Replace the entire contents of `SkaRe/views/__init__.py` with:

```python
from .registration import (
    home,
    user_login,
    user_logout,
    forgot_password,
    user_register,
    register_unit,
    list_units,
    edit_unit,
    register_individual_participant,
    list_individual_participants,
    edit_individual_participant,
    register_organizer,
    list_organizers,
    edit_organizer,
    list_all,
    list_merchandise,
    manage_entities,
    manage_unit_editors,
    manage_individual_participant_editors,
    manage_organizer_editors,
)
from .boats import (
    _fetch_sheet_csv,
    _get_registry_rows,
    boat_list,
    boat_detail,
    boat_register,
    boat_edit,
    boat_delete,
    boat_lend,
    boat_sail_lookup,
    boat_my_unit,
)
from .crews import (
    crew_register,
    crew_list,
    crew_detail,
    crew_edit,
    crew_delete,
    crew_export_csv,
    person_lend,
)
from .infodesk import (
    infodesk_dashboard,
    infodesk_registrations,
    infodesk_confirm_entity,
    infodesk_reject_entity,
    infodesk_bulk_confirm,
)
from .attendance import (
    attendance_units_list,
    attendance_unit_detail,
    attendance_individuals_list,
    attendance_organizers_list,
    attendance_set_status,
    attendance_unit_mark_all_arrived,
)
from .tickets import (
    ticket_list,
    ticket_detail,
    ticket_set_status,
    ticket_pair_rfid,
    ticket_lookup,
    ticket_create_bulk,
    ticket_on_water,
    ticket_export_csv,
)
from .exports import (
    exports_index,
    exports_kitchen_csv,
    exports_kitchen_print,
    exports_medical_csv,
    exports_medical_print,
)
```

- [ ] **Step 3: Add URL patterns to SkaRe/urls.py**

Append the following to `SkaRe/urls.py` (inside `urlpatterns`):

```python
    # InfoDesk
    path('infodesk/', views.infodesk_dashboard, name='infodesk_dashboard'),
    path('infodesk/registrations/', views.infodesk_registrations, name='infodesk_registrations'),
    path('infodesk/registrations/<int:entity_id>/confirm/', views.infodesk_confirm_entity, name='infodesk_confirm_entity'),
    path('infodesk/registrations/<int:entity_id>/reject/', views.infodesk_reject_entity, name='infodesk_reject_entity'),
    path('infodesk/registrations/bulk-confirm/', views.infodesk_bulk_confirm, name='infodesk_bulk_confirm'),
    # Attendance
    path('infodesk/attendance/units/', views.attendance_units_list, name='attendance_units_list'),
    path('infodesk/attendance/units/<int:unit_id>/', views.attendance_unit_detail, name='attendance_unit_detail'),
    path('infodesk/attendance/units/<int:unit_id>/mark-all-arrived/', views.attendance_unit_mark_all_arrived, name='attendance_unit_mark_all_arrived'),
    path('infodesk/attendance/individuals/', views.attendance_individuals_list, name='attendance_individuals_list'),
    path('infodesk/attendance/organizers/', views.attendance_organizers_list, name='attendance_organizers_list'),
    path('infodesk/attendance/persons/<int:person_id>/set-status/', views.attendance_set_status, name='attendance_set_status'),
    # Tickets
    path('infodesk/tickets/', views.ticket_list, name='ticket_list'),
    path('infodesk/tickets/lookup/', views.ticket_lookup, name='ticket_lookup'),
    path('infodesk/tickets/create-bulk/', views.ticket_create_bulk, name='ticket_create_bulk'),
    path('infodesk/tickets/on-water/', views.ticket_on_water, name='ticket_on_water'),
    path('infodesk/tickets/export/csv/', views.ticket_export_csv, name='ticket_export_csv'),
    path('infodesk/tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('infodesk/tickets/<int:ticket_id>/set-status/', views.ticket_set_status, name='ticket_set_status'),
    path('infodesk/tickets/<int:ticket_id>/pair-rfid/', views.ticket_pair_rfid, name='ticket_pair_rfid'),
    # Exports
    path('infodesk/exports/', views.exports_index, name='exports_index'),
    path('infodesk/exports/kitchen/csv/', views.exports_kitchen_csv, name='exports_kitchen_csv'),
    path('infodesk/exports/kitchen/print/', views.exports_kitchen_print, name='exports_kitchen_print'),
    path('infodesk/exports/medical/csv/', views.exports_medical_csv, name='exports_medical_csv'),
    path('infodesk/exports/medical/print/', views.exports_medical_print, name='exports_medical_print'),
```

- [ ] **Step 4: Verify routing**

```bash
uv run python manage.py check 2>&1 | tail -3
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Commit stubs + routing**

```bash
git add SkaRe/views/infodesk.py SkaRe/views/attendance.py SkaRe/views/tickets.py SkaRe/views/exports.py SkaRe/views/__init__.py SkaRe/urls.py
git commit -m "feat: add InfoDesk view stubs and URL routing"
```

---

## Task 2: Access control tests

**Files:**
- Create: `SkaRe/tests/test_infodesk_views.py`

- [ ] **Step 1: Write failing tests**

Create `SkaRe/tests/test_infodesk_views.py`:

```python
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group


def _make_infodesk_user():
    user = User.objects.create_user(username='desk', password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


def _make_regular_user():
    return User.objects.create_user(username='reg', password='pw')


INFODESK_URLS = [
    ('infodesk_dashboard', {}),
    ('infodesk_registrations', {}),
    ('attendance_units_list', {}),
    ('attendance_individuals_list', {}),
    ('attendance_organizers_list', {}),
    ('ticket_list', {}),
    ('ticket_lookup', {}),
    ('ticket_on_water', {}),
    ('exports_index', {}),
]


class InfodeskAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.infodesk = _make_infodesk_user()
        self.regular = _make_regular_user()

    def test_anonymous_redirected_to_login(self):
        for name, kwargs in INFODESK_URLS:
            with self.subTest(url=name):
                url = reverse(f'SkaRe:{name}', kwargs=kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302, msg=name)
                self.assertIn('login', response['Location'], msg=name)

    def test_regular_user_gets_403(self):
        self.client.login(username='reg', password='pw')
        for name, kwargs in INFODESK_URLS:
            with self.subTest(url=name):
                url = reverse(f'SkaRe:{name}', kwargs=kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403, msg=name)

    def test_infodesk_user_gets_200(self):
        self.client.login(username='desk', password='pw')
        for name, kwargs in INFODESK_URLS:
            with self.subTest(url=name):
                url = reverse(f'SkaRe:{name}', kwargs=kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, msg=name)
```

- [ ] **Step 2: Run — expect FAIL (no templates yet)**

```bash
uv run python manage.py test SkaRe.tests.test_infodesk_views --verbosity=0 2>&1 | tail -5
```

Expected: FAIL (TemplateDoesNotExist for stub views once templates created, or 200 for HttpResponse stubs — attendance/tickets/exports stubs already return 200 so those should PASS, dashboard/registrations will FAIL on missing template).

---

## Task 3: Dashboard template

**Files:**
- Create: `SkaRe/templates/SkaRe/infodesk/dashboard.html`

- [ ] **Step 1: Create template directory and dashboard template**

Create `SkaRe/templates/SkaRe/infodesk/dashboard.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "InfoDesk" %} - SkaRe{% endblock %}

{% block content %}
<div class="row">
  <div class="col-md-12">
    <h1 class="mb-4"><i class="bi bi-headset"></i> {% trans "InfoDesk Dashboard" %}</h1>

    <div class="row mb-4">
      <div class="col-md-3">
        <div class="card text-bg-warning">
          <div class="card-body text-center">
            <h2 class="card-title display-4">{{ unconfirmed_count }}</h2>
            <p class="card-text">{% trans "Unconfirmed registrations" %}</p>
            <a href="{% url 'SkaRe:infodesk_registrations' %}" class="btn btn-dark btn-sm">{% trans "View queue" %}</a>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-bg-success">
          <div class="card-body text-center">
            <h2 class="card-title display-4">{{ arrived_count }}</h2>
            <p class="card-text">{% trans "Arrived" %}</p>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-bg-secondary">
          <div class="card-body text-center">
            <h2 class="card-title display-4">{{ expected_count }}</h2>
            <p class="card-text">{% trans "Expected" %}</p>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-bg-primary">
          <div class="card-body text-center">
            <h2 class="card-title display-4">{{ on_water_count }}</h2>
            <p class="card-text">{% trans "Boats on water" %}</p>
            <a href="{% url 'SkaRe:ticket_on_water' %}" class="btn btn-light btn-sm">{% trans "Safety view" %}</a>
          </div>
        </div>
      </div>
    </div>

    <div class="row">
      <div class="col-md-4">
        <div class="card mb-3">
          <div class="card-header"><i class="bi bi-people-fill"></i> {% trans "Attendance" %}</div>
          <div class="list-group list-group-flush">
            <a href="{% url 'SkaRe:attendance_units_list' %}" class="list-group-item list-group-item-action">{% trans "Units" %}</a>
            <a href="{% url 'SkaRe:attendance_individuals_list' %}" class="list-group-item list-group-item-action">{% trans "Individuals" %}</a>
            <a href="{% url 'SkaRe:attendance_organizers_list' %}" class="list-group-item list-group-item-action">{% trans "Organizers" %}</a>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card mb-3">
          <div class="card-header"><i class="bi bi-ticket-perforated"></i> {% trans "Sail Tickets" %}</div>
          <div class="list-group list-group-flush">
            <a href="{% url 'SkaRe:ticket_list' %}" class="list-group-item list-group-item-action">{% trans "All tickets" %}</a>
            <a href="{% url 'SkaRe:ticket_lookup' %}" class="list-group-item list-group-item-action">{% trans "Quick lookup" %}</a>
            <a href="{% url 'SkaRe:ticket_create_bulk' %}" class="list-group-item list-group-item-action">{% trans "Bulk create" %}</a>
            <a href="{% url 'SkaRe:ticket_on_water' %}" class="list-group-item list-group-item-action">{% trans "On water (safety)" %}</a>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card mb-3">
          <div class="card-header"><i class="bi bi-file-earmark-text"></i> {% trans "Exports" %}</div>
          <div class="list-group list-group-flush">
            <a href="{% url 'SkaRe:exports_index' %}" class="list-group-item list-group-item-action">{% trans "Kitchen &amp; medical reports" %}</a>
            <a href="{% url 'SkaRe:ticket_export_csv' %}" class="list-group-item list-group-item-action">{% trans "Ticket CSV (printing)" %}</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Run dashboard tests**

```bash
uv run python manage.py test SkaRe.tests.test_infodesk_views.InfodeskAccessTest.test_infodesk_user_gets_200 --verbosity=0 2>&1 | tail -5
```

Expected: PASS (still fails for registrations — that template is next).

---

## Task 4: Registration queue template + tests

**Files:**
- Create: `SkaRe/templates/SkaRe/infodesk/registrations.html`
- Modify: `SkaRe/tests/test_infodesk_views.py`

- [ ] **Step 1: Create registrations template**

Create `SkaRe/templates/SkaRe/infodesk/registrations.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Registration Queue" %} - SkaRe{% endblock %}

{% block content %}
<div class="row">
  <div class="col-md-12">
    <h1 class="mb-3"><i class="bi bi-clipboard-check"></i> {% trans "Registration Queue" %}</h1>
    <p>
      <a href="{% url 'SkaRe:infodesk_dashboard' %}" class="btn btn-outline-secondary btn-sm">
        <i class="bi bi-arrow-left"></i> {% trans "Dashboard" %}
      </a>
    </p>

    {% if messages %}
      {% for msg in messages %}
        <div class="alert alert-{{ msg.tags|default:'info' }} alert-dismissible fade show">
          {{ msg }} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
      {% endfor %}
    {% endif %}

    <form method="post" action="{% url 'SkaRe:infodesk_bulk_confirm' %}">
      {% csrf_token %}
      <div class="mb-2">
        <button type="submit" class="btn btn-success btn-sm">
          <i class="bi bi-check-all"></i> {% trans "Confirm selected" %}
        </button>
      </div>
      <table class="table table-striped table-hover align-middle">
        <thead class="table-dark">
          <tr>
            <th><input type="checkbox" id="select-all"></th>
            <th>{% trans "Name" %}</th>
            <th>{% trans "Type" %}</th>
            <th>{% trans "Status" %}</th>
            <th>{% trans "Created" %}</th>
            <th>{% trans "Actions" %}</th>
          </tr>
        </thead>
        <tbody>
          {% for row in rows %}
          <tr>
            <td>
              {% if not row.entity.confirmed %}
                <input type="checkbox" name="entity_ids" value="{{ row.entity.pk }}">
              {% endif %}
            </td>
            <td>{{ row.name }}</td>
            <td>{{ row.type }}</td>
            <td>
              {% if row.entity.confirmed %}
                <span class="badge bg-success">{% trans "Confirmed" %}</span>
              {% else %}
                <span class="badge bg-warning text-dark">{% trans "Unconfirmed" %}</span>
              {% endif %}
            </td>
            <td>{{ row.entity.created_at|date:"d.m.Y H:i" }}</td>
            <td>
              {% if not row.entity.confirmed %}
                <form method="post" action="{% url 'SkaRe:infodesk_confirm_entity' row.entity.pk %}" class="d-inline">
                  {% csrf_token %}
                  <button type="submit" class="btn btn-success btn-sm">
                    <i class="bi bi-check"></i> {% trans "Confirm" %}
                  </button>
                </form>
              {% else %}
                <form method="post" action="{% url 'SkaRe:infodesk_reject_entity' row.entity.pk %}" class="d-inline">
                  {% csrf_token %}
                  <button type="submit" class="btn btn-outline-danger btn-sm">
                    <i class="bi bi-x"></i> {% trans "Reject" %}
                  </button>
                </form>
              {% endif %}
            </td>
          </tr>
          {% empty %}
          <tr><td colspan="6" class="text-center text-muted">{% trans "No registrations yet." %}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </form>
  </div>
</div>

<script>
document.getElementById('select-all').addEventListener('change', function() {
  document.querySelectorAll('input[name="entity_ids"]').forEach(cb => cb.checked = this.checked);
});
</script>
{% endblock %}
```

- [ ] **Step 2: Add queue-specific tests to test_infodesk_views.py**

Append to `SkaRe/tests/test_infodesk_views.py`:

```python
from datetime import date
from SkaRe.models import Entity, Unit, IndividualParticipant, RegularParticipant


def _make_unit_entity(user, confirmed=False, name='Test Unit'):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='t@example.com',
        contact_phone='123456789',
        scout_unit_name=name,
        confirmed=confirmed,
    )
    Unit.objects.create(entity=entity, contact_person_name='Leader')
    return entity


class RegistrationQueueTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.infodesk = _make_infodesk_user()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_queue_shows_all_entities(self):
        _make_unit_entity(self.owner, confirmed=False, name='Alpha')
        _make_unit_entity(self.owner, confirmed=True, name='Beta')
        url = reverse('SkaRe:infodesk_registrations')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alpha')
        self.assertContains(response, 'Beta')

    def test_confirm_entity_sets_confirmed_true(self):
        entity = _make_unit_entity(self.owner, confirmed=False)
        url = reverse('SkaRe:infodesk_confirm_entity', kwargs={'entity_id': entity.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))
        entity.refresh_from_db()
        self.assertTrue(entity.confirmed)

    def test_reject_entity_sets_confirmed_false(self):
        entity = _make_unit_entity(self.owner, confirmed=True)
        url = reverse('SkaRe:infodesk_reject_entity', kwargs={'entity_id': entity.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))
        entity.refresh_from_db()
        self.assertFalse(entity.confirmed)

    def test_bulk_confirm_sets_multiple_confirmed(self):
        e1 = _make_unit_entity(self.owner, confirmed=False, name='A')
        e2 = _make_unit_entity(self.owner, confirmed=False, name='B')
        url = reverse('SkaRe:infodesk_bulk_confirm')
        response = self.client.post(url, {'entity_ids': [e1.pk, e2.pk]})
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))
        e1.refresh_from_db()
        e2.refresh_from_db()
        self.assertTrue(e1.confirmed)
        self.assertTrue(e2.confirmed)

    def test_confirm_returns_405_on_get(self):
        entity = _make_unit_entity(self.owner)
        url = reverse('SkaRe:infodesk_confirm_entity', kwargs={'entity_id': entity.pk})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('SkaRe:infodesk_registrations'))
```

- [ ] **Step 3: Run all infodesk tests**

```bash
uv run python manage.py test SkaRe.tests.test_infodesk_views --verbosity=0 2>&1 | tail -5
```

Expected: All PASS.

- [ ] **Step 4: Run full suite**

```bash
uv run python manage.py test SkaRe --verbosity=0 2>&1 | tail -3
```

Expected: OK (no regressions).

- [ ] **Step 5: Commit**

```bash
git add SkaRe/templates/SkaRe/infodesk/ SkaRe/tests/test_infodesk_views.py
git commit -m "feat: InfoDesk dashboard and registration queue"
```
