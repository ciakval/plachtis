# InfoDesk — Attendance Views

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stub attendance views with full implementations: unit list with arrival summaries, unit detail with per-participant status actions, bulk mark-all-arrived, and individual/organizer attendance lists.

**Architecture:** All views in `SkaRe/views/attendance.py`. A shared POST endpoint `attendance_set_status` handles status changes for any person type. `AttendanceLog` entries created on every status change. All templates in `SkaRe/templates/SkaRe/attendance/`.

**Tech Stack:** Django 6.0, Python 3.12, Bootstrap 5.3.0, `uv run python manage.py ...` for all commands.

**Starting state:** Plan A complete. Attendance stub views return 200. 196+ tests passing.

**Spec:** `docs/superpowers/specs/2026-03-26-plachtis-overhaul-design.md` — Section 4 (attendance subsections).

---

## File Map

| File | Action | Purpose |
|------|---------|---------|
| `SkaRe/views/attendance.py` | Replace stubs with full impl | All attendance views |
| `SkaRe/templates/SkaRe/attendance/units_list.html` | Create | Unit list with arrival summary |
| `SkaRe/templates/SkaRe/attendance/unit_detail.html` | Create | Per-participant status table |
| `SkaRe/templates/SkaRe/attendance/individuals_list.html` | Create | Individual participant attendance |
| `SkaRe/templates/SkaRe/attendance/organizers_list.html` | Create | Organizer attendance |
| `SkaRe/tests/test_attendance_views.py` | Create | View + action tests |

---

## Task 1: Implement attendance views

**Files:**
- Replace: `SkaRe/views/attendance.py`

- [ ] **Step 1: Write failing tests**

Create `SkaRe/tests/test_attendance_views.py`:

```python
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.utils import timezone
from SkaRe.models import (
    Entity, Unit, RegularParticipant, IndividualParticipant,
    Organizer, Person, AttendanceLog,
)


def _make_infodesk():
    user = User.objects.create_user(username='desk', password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


def _make_unit(user, name='Bobři'):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='u@example.com',
        contact_phone='123456789',
        scout_unit_name=name,
    )
    return Unit.objects.create(entity=entity, contact_person_name='Leader')


def _make_participant(unit, first='Jan', last='Novák'):
    return RegularParticipant.objects.create(
        unit=unit,
        first_name=first,
        last_name=last,
        date_of_birth=date(2000, 1, 1),
    )


def _make_individual(user):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='i@example.com',
        contact_phone='123456789',
    )
    return IndividualParticipant.objects.create(
        entity=entity,
        first_name='Marie',
        last_name='Nováková',
        date_of_birth=date(1990, 5, 10),
    )


def _make_organizer(user):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='o@example.com',
        contact_phone='123456789',
    )
    return Organizer.objects.create(
        entity=entity,
        first_name='Petr',
        last_name='Dvořák',
        date_of_birth=date(1985, 3, 20),
    )


class AttendanceUnitsListTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_units_list_shows_unit_names(self):
        _make_unit(self.owner, 'Racci')
        url = reverse('SkaRe:attendance_units_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Racci')

    def test_units_list_shows_arrival_counts(self):
        unit = _make_unit(self.owner, 'Racci')
        p1 = _make_participant(unit, 'Alice', 'Smith')
        p2 = _make_participant(unit, 'Bob', 'Jones')
        p1.attendance_status = Person.AttendanceStatus.ARRIVED
        p1.save()
        url = reverse('SkaRe:attendance_units_list')
        response = self.client.get(url)
        self.assertContains(response, '1')   # 1 arrived
        self.assertContains(response, '2')   # 2 total


class AttendanceUnitDetailTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.unit = _make_unit(self.owner)
        self.p1 = _make_participant(self.unit, 'Alice', 'Smith')

    def test_unit_detail_shows_participant_names(self):
        url = reverse('SkaRe:attendance_unit_detail', kwargs={'unit_id': self.unit.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice')

    def test_unit_detail_404_for_missing_unit(self):
        url = reverse('SkaRe:attendance_unit_detail', kwargs={'unit_id': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class AttendanceSetStatusTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.unit = _make_unit(self.owner)
        self.person = _make_participant(self.unit)

    def _post(self, person, new_status, next_url=None):
        url = reverse('SkaRe:attendance_set_status', kwargs={'person_id': person.pk})
        data = {'new_status': new_status}
        if next_url:
            data['next'] = next_url
        return self.client.post(url, data)

    def test_set_arrived_updates_status(self):
        self._post(self.person, 'arrived')
        self.person.refresh_from_db()
        self.assertEqual(self.person.attendance_status, 'arrived')

    def test_set_arrived_sets_arrived_at(self):
        self._post(self.person, 'arrived')
        self.person.refresh_from_db()
        self.assertIsNotNone(self.person.arrived_at)

    def test_set_departed_sets_departed_at(self):
        self._post(self.person, 'departed')
        self.person.refresh_from_db()
        self.assertIsNotNone(self.person.departed_at)

    def test_set_not_coming_clears_timestamps(self):
        self.person.arrived_at = timezone.now()
        self.person.save()
        self._post(self.person, 'not_coming')
        self.person.refresh_from_db()
        self.assertEqual(self.person.attendance_status, 'not_coming')

    def test_creates_attendance_log_entry(self):
        self._post(self.person, 'arrived')
        self.assertEqual(AttendanceLog.objects.filter(person=self.person).count(), 1)
        log = AttendanceLog.objects.get(person=self.person)
        self.assertEqual(log.status, 'arrived')
        self.assertEqual(log.changed_by, self.desk)

    def test_invalid_status_returns_400(self):
        response = self._post(self.person, 'flying')
        self.assertEqual(response.status_code, 400)

    def test_redirects_to_next_url(self):
        next_url = reverse('SkaRe:attendance_unit_detail', kwargs={'unit_id': self.unit.pk})
        response = self._post(self.person, 'arrived', next_url=next_url)
        self.assertRedirects(response, next_url)

    def test_get_method_not_allowed(self):
        url = reverse('SkaRe:attendance_set_status', kwargs={'person_id': self.person.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class AttendanceMarkAllArrivedTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')
        self.unit = _make_unit(self.owner)
        self.p1 = _make_participant(self.unit, 'Alice', 'Smith')
        self.p2 = _make_participant(self.unit, 'Bob', 'Jones')

    def test_marks_all_expected_as_arrived(self):
        url = reverse('SkaRe:attendance_unit_mark_all_arrived', kwargs={'unit_id': self.unit.pk})
        self.client.post(url)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.attendance_status, 'arrived')
        self.assertEqual(self.p2.attendance_status, 'arrived')

    def test_skips_already_departed(self):
        self.p2.attendance_status = Person.AttendanceStatus.DEPARTED
        self.p2.save()
        url = reverse('SkaRe:attendance_unit_mark_all_arrived', kwargs={'unit_id': self.unit.pk})
        self.client.post(url)
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.attendance_status, 'departed')

    def test_creates_log_entries(self):
        url = reverse('SkaRe:attendance_unit_mark_all_arrived', kwargs={'unit_id': self.unit.pk})
        self.client.post(url)
        self.assertEqual(AttendanceLog.objects.count(), 2)


class AttendanceIndividualsListTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_shows_individual_names(self):
        _make_individual(self.owner)
        url = reverse('SkaRe:attendance_individuals_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nováková')


class AttendanceOrganizersListTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_shows_organizer_names(self):
        _make_organizer(self.owner)
        url = reverse('SkaRe:attendance_organizers_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dvořák')
```

- [ ] **Step 2: Run — expect FAIL**

```bash
uv run python manage.py test SkaRe.tests.test_attendance_views --verbosity=0 2>&1 | tail -5
```

Expected: FAIL (stub views return plain HttpResponse, no templates).

- [ ] **Step 3: Implement attendance views**

Replace `SkaRe/views/attendance.py` with:

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed
from django.utils import timezone
from django.utils.translation import gettext as _
from ..permissions import infodesk_required
from ..models import Unit, IndividualParticipant, Organizer, Person, AttendanceLog

VALID_STATUSES = {s.value for s in Person.AttendanceStatus}


@infodesk_required
def attendance_units_list(request):
    units = Unit.objects.select_related('entity').annotate(
        total=Count('regular_participants'),
        arrived=Count('regular_participants', filter=Q(
            regular_participants__attendance_status=Person.AttendanceStatus.ARRIVED
        )),
    ).order_by('entity__scout_unit_name')
    return render(request, 'SkaRe/attendance/units_list.html', {'units': units})


@infodesk_required
def attendance_unit_detail(request, unit_id):
    unit = get_object_or_404(Unit.objects.select_related('entity'), pk=unit_id)
    participants = unit.regular_participants.order_by('last_name', 'first_name')
    return render(request, 'SkaRe/attendance/unit_detail.html', {
        'unit': unit,
        'participants': participants,
        'statuses': Person.AttendanceStatus,
    })


@infodesk_required
def attendance_individuals_list(request):
    individuals = IndividualParticipant.objects.select_related('entity').order_by('last_name', 'first_name')
    return render(request, 'SkaRe/attendance/individuals_list.html', {
        'individuals': individuals,
        'statuses': Person.AttendanceStatus,
    })


@infodesk_required
def attendance_organizers_list(request):
    organizers = Organizer.objects.select_related('entity').order_by('last_name', 'first_name')
    return render(request, 'SkaRe/attendance/organizers_list.html', {
        'organizers': organizers,
        'statuses': Person.AttendanceStatus,
    })


@infodesk_required
def attendance_set_status(request, person_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    person = get_object_or_404(Person, pk=person_id)
    new_status = request.POST.get('new_status', '')
    if new_status not in VALID_STATUSES:
        return HttpResponseBadRequest('Invalid status')

    now = timezone.now()
    person.attendance_status = new_status
    if new_status == Person.AttendanceStatus.ARRIVED:
        person.arrived_at = now
    elif new_status == Person.AttendanceStatus.DEPARTED:
        person.departed_at = now
    person.save(update_fields=['attendance_status', 'arrived_at', 'departed_at'])

    AttendanceLog.objects.create(
        person=person,
        status=new_status,
        changed_by=request.user,
    )

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if next_url:
        return redirect(next_url)
    return redirect('SkaRe:infodesk_dashboard')


@infodesk_required
def attendance_unit_mark_all_arrived(request, unit_id):
    if request.method != 'POST':
        return redirect('SkaRe:attendance_unit_detail', unit_id=unit_id)
    unit = get_object_or_404(Unit, pk=unit_id)
    now = timezone.now()
    to_mark = unit.regular_participants.filter(
        attendance_status=Person.AttendanceStatus.EXPECTED
    )
    with transaction.atomic():
        logs = []
        for person in to_mark:
            person.attendance_status = Person.AttendanceStatus.ARRIVED
            person.arrived_at = now
            person.save(update_fields=['attendance_status', 'arrived_at'])
            logs.append(AttendanceLog(
                person=person,
                status=Person.AttendanceStatus.ARRIVED,
                changed_by=request.user,
            ))
        AttendanceLog.objects.bulk_create(logs)
    messages.success(request, _('%(n)d participants marked as arrived.') % {'n': len(logs)})
    return redirect('SkaRe:attendance_unit_detail', unit_id=unit_id)
```

- [ ] **Step 4: Run tests — expect FAIL (no templates yet)**

```bash
uv run python manage.py test SkaRe.tests.test_attendance_views --verbosity=0 2>&1 | tail -5
```

Expected: Some pass (set_status tests that don't need templates), template tests fail.

---

## Task 2: Attendance templates

**Files:**
- Create: `SkaRe/templates/SkaRe/attendance/units_list.html`
- Create: `SkaRe/templates/SkaRe/attendance/unit_detail.html`
- Create: `SkaRe/templates/SkaRe/attendance/individuals_list.html`
- Create: `SkaRe/templates/SkaRe/attendance/organizers_list.html`

- [ ] **Step 1: Create units_list.html**

Create `SkaRe/templates/SkaRe/attendance/units_list.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Attendance — Units" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-3"><i class="bi bi-people-fill"></i> {% trans "Attendance — Units" %}</h1>
<p>
  <a href="{% url 'SkaRe:infodesk_dashboard' %}" class="btn btn-outline-secondary btn-sm">
    <i class="bi bi-arrow-left"></i> {% trans "Dashboard" %}
  </a>
</p>
<table class="table table-hover align-middle">
  <thead class="table-dark">
    <tr>
      <th>{% trans "Unit" %}</th>
      <th>{% trans "Arrived / Total" %}</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {% for unit in units %}
    <tr>
      <td>{{ unit.entity.scout_unit_name }}</td>
      <td>
        <span class="badge bg-success">{{ unit.arrived }}</span> /
        <span class="badge bg-secondary">{{ unit.total }}</span>
      </td>
      <td>
        <a href="{% url 'SkaRe:attendance_unit_detail' unit.pk %}" class="btn btn-primary btn-sm">
          {% trans "Detail" %}
        </a>
      </td>
    </tr>
    {% empty %}
    <tr><td colspan="3" class="text-muted text-center">{% trans "No units registered." %}</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 2: Create unit_detail.html**

Create `SkaRe/templates/SkaRe/attendance/unit_detail.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{{ unit.entity.scout_unit_name }} - {% trans "Attendance" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-2">{{ unit.entity.scout_unit_name }}</h1>
<p class="text-muted mb-3">{% trans "Contact" %}: {{ unit.entity.contact_phone }}</p>

<div class="mb-3 d-flex gap-2">
  <a href="{% url 'SkaRe:attendance_units_list' %}" class="btn btn-outline-secondary btn-sm">
    <i class="bi bi-arrow-left"></i> {% trans "Units" %}
  </a>
  <form method="post" action="{% url 'SkaRe:attendance_unit_mark_all_arrived' unit.pk %}">
    {% csrf_token %}
    <button type="submit" class="btn btn-success btn-sm">
      <i class="bi bi-check-all"></i> {% trans "Mark all as arrived" %}
    </button>
  </form>
</div>

{% if messages %}
  {% for msg in messages %}
    <div class="alert alert-info alert-dismissible fade show">
      {{ msg }} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
  {% endfor %}
{% endif %}

<table class="table table-hover align-middle">
  <thead class="table-dark">
    <tr>
      <th>{% trans "Name" %}</th>
      <th>{% trans "Status" %}</th>
      <th>{% trans "Arrived at" %}</th>
      <th>{% trans "Actions" %}</th>
    </tr>
  </thead>
  <tbody>
    {% for p in participants %}
    <tr>
      <td>{{ p }}</td>
      <td>
        {% if p.attendance_status == 'arrived' %}
          <span class="badge bg-success">{% trans "Arrived" %}</span>
        {% elif p.attendance_status == 'departed' %}
          <span class="badge bg-secondary">{% trans "Departed" %}</span>
        {% elif p.attendance_status == 'not_coming' %}
          <span class="badge bg-danger">{% trans "Not coming" %}</span>
        {% else %}
          <span class="badge bg-warning text-dark">{% trans "Expected" %}</span>
        {% endif %}
      </td>
      <td>{{ p.arrived_at|date:"d.m.Y H:i"|default:"—" }}</td>
      <td>
        {% with next_url=request.path %}
        {% if p.attendance_status != 'arrived' %}
        <form method="post" action="{% url 'SkaRe:attendance_set_status' p.pk %}" class="d-inline">
          {% csrf_token %}<input type="hidden" name="new_status" value="arrived"><input type="hidden" name="next" value="{{ next_url }}">
          <button type="submit" class="btn btn-success btn-sm">{% trans "Arrived" %}</button>
        </form>
        {% endif %}
        {% if p.attendance_status == 'arrived' %}
        <form method="post" action="{% url 'SkaRe:attendance_set_status' p.pk %}" class="d-inline">
          {% csrf_token %}<input type="hidden" name="new_status" value="departed"><input type="hidden" name="next" value="{{ next_url }}">
          <button type="submit" class="btn btn-secondary btn-sm">{% trans "Departed" %}</button>
        </form>
        {% endif %}
        {% if p.attendance_status != 'not_coming' %}
        <form method="post" action="{% url 'SkaRe:attendance_set_status' p.pk %}" class="d-inline">
          {% csrf_token %}<input type="hidden" name="new_status" value="not_coming"><input type="hidden" name="next" value="{{ next_url }}">
          <button type="submit" class="btn btn-outline-danger btn-sm">{% trans "Not coming" %}</button>
        </form>
        {% endif %}
        {% endwith %}
      </td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="text-muted text-center">{% trans "No participants." %}</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 3: Create individuals_list.html**

Create `SkaRe/templates/SkaRe/attendance/individuals_list.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Attendance — Individuals" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-3"><i class="bi bi-person-fill"></i> {% trans "Attendance — Individual Participants" %}</h1>
<p>
  <a href="{% url 'SkaRe:infodesk_dashboard' %}" class="btn btn-outline-secondary btn-sm">
    <i class="bi bi-arrow-left"></i> {% trans "Dashboard" %}
  </a>
</p>
<table class="table table-hover align-middle">
  <thead class="table-dark">
    <tr>
      <th>{% trans "Name" %}</th>
      <th>{% trans "Status" %}</th>
      <th>{% trans "Arrived at" %}</th>
      <th>{% trans "Actions" %}</th>
    </tr>
  </thead>
  <tbody>
    {% for p in individuals %}
    <tr>
      <td>{{ p }}</td>
      <td>
        {% if p.attendance_status == 'arrived' %}<span class="badge bg-success">{% trans "Arrived" %}</span>
        {% elif p.attendance_status == 'departed' %}<span class="badge bg-secondary">{% trans "Departed" %}</span>
        {% elif p.attendance_status == 'not_coming' %}<span class="badge bg-danger">{% trans "Not coming" %}</span>
        {% else %}<span class="badge bg-warning text-dark">{% trans "Expected" %}</span>{% endif %}
      </td>
      <td>{{ p.arrived_at|date:"d.m.Y H:i"|default:"—" }}</td>
      <td>
        {% with next_url=request.path %}
        {% if p.attendance_status != 'arrived' %}
        <form method="post" action="{% url 'SkaRe:attendance_set_status' p.pk %}" class="d-inline">
          {% csrf_token %}<input type="hidden" name="new_status" value="arrived"><input type="hidden" name="next" value="{{ next_url }}">
          <button type="submit" class="btn btn-success btn-sm">{% trans "Arrived" %}</button>
        </form>
        {% endif %}
        {% if p.attendance_status == 'arrived' %}
        <form method="post" action="{% url 'SkaRe:attendance_set_status' p.pk %}" class="d-inline">
          {% csrf_token %}<input type="hidden" name="new_status" value="departed"><input type="hidden" name="next" value="{{ next_url }}">
          <button type="submit" class="btn btn-secondary btn-sm">{% trans "Departed" %}</button>
        </form>
        {% endif %}
        {% if p.attendance_status != 'not_coming' %}
        <form method="post" action="{% url 'SkaRe:attendance_set_status' p.pk %}" class="d-inline">
          {% csrf_token %}<input type="hidden" name="new_status" value="not_coming"><input type="hidden" name="next" value="{{ next_url }}">
          <button type="submit" class="btn btn-outline-danger btn-sm">{% trans "Not coming" %}</button>
        </form>
        {% endif %}
        {% endwith %}
      </td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="text-muted text-center">{% trans "No individual participants." %}</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 4: Create organizers_list.html**

Create `SkaRe/templates/SkaRe/attendance/organizers_list.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Attendance — Organizers" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-3"><i class="bi bi-person-badge"></i> {% trans "Attendance — Organizers" %}</h1>
<p>
  <a href="{% url 'SkaRe:infodesk_dashboard' %}" class="btn btn-outline-secondary btn-sm">
    <i class="bi bi-arrow-left"></i> {% trans "Dashboard" %}
  </a>
</p>
<table class="table table-hover align-middle">
  <thead class="table-dark">
    <tr>
      <th>{% trans "Name" %}</th>
      <th>{% trans "Status" %}</th>
      <th>{% trans "Arrived at" %}</th>
      <th>{% trans "Actions" %}</th>
    </tr>
  </thead>
  <tbody>
    {% for p in organizers %}
    <tr>
      <td>{{ p }}</td>
      <td>
        {% if p.attendance_status == 'arrived' %}<span class="badge bg-success">{% trans "Arrived" %}</span>
        {% elif p.attendance_status == 'departed' %}<span class="badge bg-secondary">{% trans "Departed" %}</span>
        {% elif p.attendance_status == 'not_coming' %}<span class="badge bg-danger">{% trans "Not coming" %}</span>
        {% else %}<span class="badge bg-warning text-dark">{% trans "Expected" %}</span>{% endif %}
      </td>
      <td>{{ p.arrived_at|date:"d.m.Y H:i"|default:"—" }}</td>
      <td>
        {% with next_url=request.path %}
        {% if p.attendance_status != 'arrived' %}
        <form method="post" action="{% url 'SkaRe:attendance_set_status' p.pk %}" class="d-inline">
          {% csrf_token %}<input type="hidden" name="new_status" value="arrived"><input type="hidden" name="next" value="{{ next_url }}">
          <button type="submit" class="btn btn-success btn-sm">{% trans "Arrived" %}</button>
        </form>
        {% endif %}
        {% if p.attendance_status == 'arrived' %}
        <form method="post" action="{% url 'SkaRe:attendance_set_status' p.pk %}" class="d-inline">
          {% csrf_token %}<input type="hidden" name="new_status" value="departed"><input type="hidden" name="next" value="{{ next_url }}">
          <button type="submit" class="btn btn-secondary btn-sm">{% trans "Departed" %}</button>
        </form>
        {% endif %}
        {% if p.attendance_status != 'not_coming' %}
        <form method="post" action="{% url 'SkaRe:attendance_set_status' p.pk %}" class="d-inline">
          {% csrf_token %}<input type="hidden" name="new_status" value="not_coming"><input type="hidden" name="next" value="{{ next_url }}">
          <button type="submit" class="btn btn-outline-danger btn-sm">{% trans "Not coming" %}</button>
        </form>
        {% endif %}
        {% endwith %}
      </td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="text-muted text-center">{% trans "No organizers." %}</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 5: Run all attendance tests**

```bash
uv run python manage.py test SkaRe.tests.test_attendance_views --verbosity=0 2>&1 | tail -5
```

Expected: All PASS.

- [ ] **Step 6: Run full suite**

```bash
uv run python manage.py test SkaRe --verbosity=0 2>&1 | tail -3
```

Expected: OK.

- [ ] **Step 7: Commit**

```bash
git add SkaRe/views/attendance.py SkaRe/templates/SkaRe/attendance/ SkaRe/tests/test_attendance_views.py
git commit -m "feat: InfoDesk attendance views (units, individuals, organizers)"
```
