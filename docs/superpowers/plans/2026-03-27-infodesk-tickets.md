# InfoDesk — Sail Ticket Views

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all sail ticket InfoDesk views: list with filters, detail with status actions and RFID pairing, quick lookup, bulk ticket creation, boats on water safety view, and CSV export.

**Architecture:** All views in `SkaRe/views/tickets.py`. `BulkTicketCreateForm` in `SkaRe/forms/tickets.py`. Status changes always write a `SailTicketLog` entry. Templates in `SkaRe/templates/SkaRe/tickets/`.

**Tech Stack:** Django 6.0, Python 3.12, Bootstrap 5.3.0, `uv run python manage.py ...` for all commands.

**Starting state:** Plans A complete. Ticket stub views return 200. 196+ tests passing.

**Spec:** `docs/superpowers/specs/2026-03-26-plachtis-overhaul-design.md` — Section 4 (sail ticket subsections).

---

## File Map

| File | Action | Purpose |
|------|---------|---------|
| `SkaRe/forms/tickets.py` | Create | `BulkTicketCreateForm` |
| `SkaRe/forms/__init__.py` | Modify | Re-export `BulkTicketCreateForm` |
| `SkaRe/views/tickets.py` | Replace stubs | All ticket views |
| `SkaRe/templates/SkaRe/tickets/list.html` | Create | Ticket list with filters |
| `SkaRe/templates/SkaRe/tickets/detail.html` | Create | Ticket detail + logs + actions |
| `SkaRe/templates/SkaRe/tickets/lookup.html` | Create | Quick lookup + inline results |
| `SkaRe/templates/SkaRe/tickets/create_bulk.html` | Create | Bulk creation form |
| `SkaRe/templates/SkaRe/tickets/on_water.html` | Create | Safety view |
| `SkaRe/tests/test_ticket_views.py` | Create | Ticket view tests |

---

## Task 1: BulkTicketCreateForm + ticket view implementations

**Files:**
- Create: `SkaRe/forms/tickets.py`
- Modify: `SkaRe/forms/__init__.py`
- Replace: `SkaRe/views/tickets.py`

- [ ] **Step 1: Create SkaRe/forms/tickets.py**

```python
from django import forms
from django.utils.translation import gettext_lazy as _


class BulkTicketCreateForm(forms.Form):
    p550_reserves = forms.IntegerField(
        min_value=0, initial=0, required=True,
        label=_('P550 reserve tickets'),
        help_text=_('Extra P550 tickets beyond registered P550 boats'),
    )
    sail_reserves = forms.IntegerField(
        min_value=0, initial=0, required=True,
        label=_('Sailboat reserve tickets'),
        help_text=_('Extra sailboat tickets beyond registered sailboats'),
    )
    other_reserves = forms.IntegerField(
        min_value=0, initial=0, required=True,
        label=_('Other boat reserve tickets'),
        help_text=_('Extra other-boat tickets beyond registered other boats'),
    )
    spare_count = forms.IntegerField(
        min_value=0, initial=0, required=True,
        label=_('Spare tickets'),
        help_text=_('Spare tickets not assigned to any boat'),
    )
```

- [ ] **Step 2: Update SkaRe/forms/__init__.py**

Append this import to `SkaRe/forms/__init__.py`:

```python
from .tickets import BulkTicketCreateForm
```

- [ ] **Step 3: Write failing tests**

Create `SkaRe/tests/test_ticket_views.py`:

```python
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from SkaRe.models import SailTicket, SailTicketLog, Boat, BoatClass


def _make_infodesk():
    user = User.objects.create_user(username='desk', password='pw')
    group, _ = Group.objects.get_or_create(name='InfoDesk')
    user.groups.add(group)
    return user


def _make_boat(user, name='Albatros', sail_number='CZE1234'):
    bc = BoatClass.objects.get_or_create(
        name='P550', defaults={'category': BoatClass.Category.SAIL, 'order': 1}
    )[0]
    return Boat.objects.create(
        created_by=user, boat_class=bc, name=name, sail_number=sail_number,
        contact_person='Leader', contact_phone='123456789',
    )


def _make_ticket(code='P550-001', color=None, status=None, boat=None):
    kwargs = {
        'code': code,
        'color': color or SailTicket.Color.P550,
    }
    if status:
        kwargs['status'] = status
    if boat:
        kwargs['boat'] = boat
    return SailTicket.objects.create(**kwargs)


class TicketListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')

    def test_list_returns_200(self):
        url = reverse('SkaRe:ticket_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_list_shows_ticket_codes(self):
        _make_ticket('P550-001')
        _make_ticket('SAIL-001', SailTicket.Color.SAIL)
        url = reverse('SkaRe:ticket_list')
        response = self.client.get(url)
        self.assertContains(response, 'P550-001')
        self.assertContains(response, 'SAIL-001')

    def test_list_filter_by_status(self):
        _make_ticket('P550-001', status=SailTicket.Status.ON_WATER)
        _make_ticket('P550-002', status=SailTicket.Status.ASHORE)
        url = reverse('SkaRe:ticket_list') + '?status=on_water'
        response = self.client.get(url)
        self.assertContains(response, 'P550-001')
        self.assertNotContains(response, 'P550-002')


class TicketDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.ticket = _make_ticket('P550-001')

    def test_detail_returns_200(self):
        url = reverse('SkaRe:ticket_detail', kwargs={'ticket_id': self.ticket.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'P550-001')

    def test_detail_shows_logs(self):
        SailTicketLog.objects.create(
            ticket=self.ticket,
            status=SailTicket.Status.ON_WATER,
            changed_by=self.desk,
        )
        url = reverse('SkaRe:ticket_detail', kwargs={'ticket_id': self.ticket.pk})
        response = self.client.get(url)
        self.assertContains(response, 'on_water')


class TicketSetStatusTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.ticket = _make_ticket('P550-001')

    def _post(self, new_status, next_url=None):
        url = reverse('SkaRe:ticket_set_status', kwargs={'ticket_id': self.ticket.pk})
        data = {'new_status': new_status}
        if next_url:
            data['next'] = next_url
        return self.client.post(url, data)

    def test_set_on_water_updates_status(self):
        self._post('on_water')
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, SailTicket.Status.ON_WATER)

    def test_set_status_creates_log(self):
        self._post('on_water')
        self.assertEqual(SailTicketLog.objects.filter(ticket=self.ticket).count(), 1)
        log = SailTicketLog.objects.get(ticket=self.ticket)
        self.assertEqual(log.status, 'on_water')
        self.assertEqual(log.changed_by, self.desk)

    def test_invalid_status_returns_400(self):
        response = self._post('flying')
        self.assertEqual(response.status_code, 400)

    def test_redirects_to_next(self):
        next_url = reverse('SkaRe:ticket_lookup')
        response = self._post('on_water', next_url=next_url)
        self.assertRedirects(response, next_url)

    def test_get_not_allowed(self):
        url = reverse('SkaRe:ticket_set_status', kwargs={'ticket_id': self.ticket.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class TicketPairRfidTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.ticket = _make_ticket('P550-001')

    def test_pair_rfid_sets_pending_pairing(self):
        url = reverse('SkaRe:ticket_pair_rfid', kwargs={'ticket_id': self.ticket.pk})
        self.client.post(url)
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.pending_pairing)

    def test_pair_rfid_clears_other_pending(self):
        other = _make_ticket('P550-002')
        other.pending_pairing = True
        other.save()
        url = reverse('SkaRe:ticket_pair_rfid', kwargs={'ticket_id': self.ticket.pk})
        self.client.post(url)
        other.refresh_from_db()
        self.assertFalse(other.pending_pairing)
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.pending_pairing)


class TicketLookupTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_lookup_empty_shows_no_results(self):
        url = reverse('SkaRe:ticket_lookup')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_lookup_by_code(self):
        _make_ticket('P550-042')
        url = reverse('SkaRe:ticket_lookup') + '?q=P550-042'
        response = self.client.get(url)
        self.assertContains(response, 'P550-042')

    def test_lookup_by_boat_name(self):
        boat = _make_boat(self.owner, name='Albatros')
        _make_ticket('P550-001', boat=boat)
        url = reverse('SkaRe:ticket_lookup') + '?q=Albatros'
        response = self.client.get(url)
        self.assertContains(response, 'P550-001')

    def test_lookup_by_sail_number(self):
        boat = _make_boat(self.owner, sail_number='CZE9999')
        _make_ticket('P550-002', boat=boat)
        url = reverse('SkaRe:ticket_lookup') + '?q=CZE9999'
        response = self.client.get(url)
        self.assertContains(response, 'P550-002')


class BulkTicketCreateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_get_shows_form(self):
        url = reverse('SkaRe:ticket_create_bulk')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_creates_boat_tickets_and_reserves(self):
        _make_boat(self.owner)  # one P550 boat
        url = reverse('SkaRe:ticket_create_bulk')
        response = self.client.post(url, {
            'p550_reserves': 2,
            'sail_reserves': 0,
            'other_reserves': 0,
            'spare_count': 1,
        })
        self.assertRedirects(response, reverse('SkaRe:ticket_list'))
        # 1 boat ticket + 2 reserves + 1 spare = 4
        self.assertEqual(SailTicket.objects.count(), 4)

    def test_boat_ticket_has_boat_fk_set(self):
        boat = _make_boat(self.owner)
        url = reverse('SkaRe:ticket_create_bulk')
        self.client.post(url, {
            'p550_reserves': 0, 'sail_reserves': 0,
            'other_reserves': 0, 'spare_count': 0,
        })
        ticket = SailTicket.objects.filter(boat=boat).first()
        self.assertIsNotNone(ticket)

    def test_spare_tickets_have_no_boat(self):
        url = reverse('SkaRe:ticket_create_bulk')
        self.client.post(url, {
            'p550_reserves': 0, 'sail_reserves': 0,
            'other_reserves': 0, 'spare_count': 3,
        })
        spares = SailTicket.objects.filter(color=SailTicket.Color.SPARE)
        self.assertEqual(spares.count(), 3)
        self.assertTrue(all(t.boat is None for t in spares))

    def test_skips_boats_already_assigned_a_ticket(self):
        boat = _make_boat(self.owner)
        existing = _make_ticket('P550-001', boat=boat)
        url = reverse('SkaRe:ticket_create_bulk')
        self.client.post(url, {
            'p550_reserves': 0, 'sail_reserves': 0,
            'other_reserves': 0, 'spare_count': 0,
        })
        # No duplicate ticket for the same boat
        self.assertEqual(SailTicket.objects.filter(boat=boat).count(), 1)


class TicketOnWaterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_on_water_shows_only_on_water_tickets(self):
        boat = _make_boat(self.owner, 'Albatros')
        _make_ticket('P550-001', boat=boat, status=SailTicket.Status.ON_WATER)
        _make_ticket('P550-002', status=SailTicket.Status.ASHORE)
        url = reverse('SkaRe:ticket_on_water')
        response = self.client.get(url)
        self.assertContains(response, 'P550-001')
        self.assertNotContains(response, 'P550-002')


class TicketExportCsvTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.desk = _make_infodesk()
        self.client.login(username='desk', password='pw')
        self.owner = User.objects.create_user(username='owner', password='pw')

    def test_csv_export_returns_csv(self):
        boat = _make_boat(self.owner, 'Albatros', 'CZE1234')
        _make_ticket('P550-001', boat=boat)
        url = reverse('SkaRe:ticket_export_csv')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode()
        self.assertIn('P550-001', content)
        self.assertIn('Albatros', content)
```

- [ ] **Step 4: Run — expect FAIL**

```bash
uv run python manage.py test SkaRe.tests.test_ticket_views --verbosity=0 2>&1 | tail -5
```

Expected: FAIL (stubs return plain 200, no template rendering; form/lookup tests will fail differently).

- [ ] **Step 5: Implement SkaRe/views/tickets.py**

Replace `SkaRe/views/tickets.py` with:

```python
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.utils.translation import gettext as _
from ..permissions import infodesk_required
from ..models import SailTicket, SailTicketLog, Boat, BoatClass
from ..forms import BulkTicketCreateForm

VALID_TICKET_STATUSES = {s.value for s in SailTicket.Status}


def _boat_color(boat):
    """Map a registered boat to the corresponding SailTicket.Color."""
    if not boat.boat_class:
        return SailTicket.Color.OTHER
    if boat.boat_class.name == 'P550':
        return SailTicket.Color.P550
    if boat.boat_class.category == BoatClass.Category.SAIL:
        return SailTicket.Color.SAIL
    return SailTicket.Color.OTHER


def _generate_codes(color_prefix, count):
    """Generate `count` unique sequential codes for the given prefix, skipping existing ones."""
    existing = set(
        SailTicket.objects.filter(code__startswith=f'{color_prefix}-')
        .values_list('code', flat=True)
    )
    codes = []
    n = 1
    while len(codes) < count:
        code = f'{color_prefix}-{n:03d}'
        if code not in existing:
            codes.append(code)
        n += 1
    return codes


COLOR_PREFIX = {
    SailTicket.Color.P550: 'P550',
    SailTicket.Color.SAIL: 'SAIL',
    SailTicket.Color.OTHER: 'OTHER',
    SailTicket.Color.SPARE: 'SPARE',
}


@infodesk_required
def ticket_list(request):
    tickets = SailTicket.objects.select_related('boat', 'boat__boat_class')
    status_filter = request.GET.get('status', '')
    color_filter = request.GET.get('color', '')
    if status_filter in VALID_TICKET_STATUSES:
        tickets = tickets.filter(status=status_filter)
    if color_filter in {c.value for c in SailTicket.Color}:
        tickets = tickets.filter(color=color_filter)
    return render(request, 'SkaRe/tickets/list.html', {
        'tickets': tickets,
        'status_filter': status_filter,
        'color_filter': color_filter,
        'statuses': SailTicket.Status,
        'colors': SailTicket.Color,
    })


@infodesk_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        SailTicket.objects.select_related('boat', 'boat__boat_class'),
        pk=ticket_id,
    )
    logs = ticket.logs.select_related('changed_by').order_by('-changed_at')
    return render(request, 'SkaRe/tickets/detail.html', {
        'ticket': ticket,
        'logs': logs,
        'statuses': SailTicket.Status,
    })


@infodesk_required
def ticket_set_status(request, ticket_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    ticket = get_object_or_404(SailTicket, pk=ticket_id)
    new_status = request.POST.get('new_status', '')
    if new_status not in VALID_TICKET_STATUSES:
        return HttpResponseBadRequest('Invalid status')
    ticket.status = new_status
    ticket.save(update_fields=['status', 'updated_at'])
    SailTicketLog.objects.create(
        ticket=ticket,
        status=new_status,
        changed_by=request.user,
    )
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if next_url:
        return redirect(next_url)
    return redirect('SkaRe:ticket_detail', ticket_id=ticket.pk)


@infodesk_required
def ticket_pair_rfid(request, ticket_id):
    if request.method != 'POST':
        return redirect('SkaRe:ticket_detail', ticket_id=ticket_id)
    ticket = get_object_or_404(SailTicket, pk=ticket_id)
    with transaction.atomic():
        SailTicket.objects.filter(pending_pairing=True).update(pending_pairing=False)
        ticket.pending_pairing = True
        ticket.save(update_fields=['pending_pairing', 'updated_at'])
    messages.info(request, _('Waiting for RFID scan on ticket %(code)s…') % {'code': ticket.code})
    return redirect('SkaRe:ticket_detail', ticket_id=ticket.pk)


@infodesk_required
def ticket_lookup(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = SailTicket.objects.filter(
            Q(code__icontains=query) |
            Q(boat__name__icontains=query) |
            Q(boat__sail_number__icontains=query) |
            Q(boat__contact_person__icontains=query)
        ).select_related('boat', 'boat__boat_class').order_by('code')
    return render(request, 'SkaRe/tickets/lookup.html', {
        'query': query,
        'results': results,
        'statuses': SailTicket.Status,
    })


@infodesk_required
def ticket_create_bulk(request):
    if request.method == 'POST':
        form = BulkTicketCreateForm(request.POST)
        if form.is_valid():
            p550_reserves = form.cleaned_data['p550_reserves']
            sail_reserves = form.cleaned_data['sail_reserves']
            other_reserves = form.cleaned_data['other_reserves']
            spare_count = form.cleaned_data['spare_count']

            # Boats that don't yet have any ticket assigned
            assigned_boat_ids = set(
                SailTicket.objects.filter(boat__isnull=False).values_list('boat_id', flat=True)
            )
            boats = Boat.objects.select_related('boat_class').exclude(pk__in=assigned_boat_ids)

            # Group boats by color
            boat_groups = {
                SailTicket.Color.P550: [],
                SailTicket.Color.SAIL: [],
                SailTicket.Color.OTHER: [],
            }
            for boat in boats:
                color = _boat_color(boat)
                boat_groups[color].append(boat)

            reserve_counts = {
                SailTicket.Color.P550: p550_reserves,
                SailTicket.Color.SAIL: sail_reserves,
                SailTicket.Color.OTHER: other_reserves,
            }

            with transaction.atomic():
                created = 0
                for color, color_boats in boat_groups.items():
                    total = len(color_boats) + reserve_counts[color]
                    codes = _generate_codes(COLOR_PREFIX[color], total)
                    for i, boat in enumerate(color_boats):
                        SailTicket.objects.create(code=codes[i], color=color, boat=boat)
                        created += 1
                    for i in range(len(color_boats), total):
                        SailTicket.objects.create(code=codes[i], color=color)
                        created += 1
                spare_codes = _generate_codes(COLOR_PREFIX[SailTicket.Color.SPARE], spare_count)
                for code in spare_codes:
                    SailTicket.objects.create(code=code, color=SailTicket.Color.SPARE)
                    created += 1

            messages.success(request, _('%(n)d tickets created.') % {'n': created})
            return redirect('SkaRe:ticket_list')
    else:
        # Pre-fill boat counts for preview
        form = BulkTicketCreateForm()

    unassigned_boats = Boat.objects.select_related('boat_class').exclude(
        pk__in=SailTicket.objects.filter(boat__isnull=False).values_list('boat_id', flat=True)
    )
    boat_preview = {}
    for boat in unassigned_boats:
        color = _boat_color(boat)
        boat_preview[color] = boat_preview.get(color, 0) + 1

    return render(request, 'SkaRe/tickets/create_bulk.html', {
        'form': form,
        'boat_preview': boat_preview,
        'existing_ticket_count': SailTicket.objects.count(),
    })


@infodesk_required
def ticket_on_water(request):
    tickets = SailTicket.objects.filter(
        status=SailTicket.Status.ON_WATER
    ).select_related('boat', 'boat__boat_class', 'boat__created_by')
    return render(request, 'SkaRe/tickets/on_water.html', {'tickets': tickets})


@infodesk_required
def ticket_export_csv(request):
    tickets = SailTicket.objects.select_related(
        'boat', 'boat__boat_class'
    ).order_by('color', 'code')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="sail_tickets.csv"'
    response.write('\ufeff')  # UTF-8 BOM for Excel

    writer = csv.writer(response)
    writer.writerow([
        'Code', 'Color', 'Boat class', 'Sail number', 'Boat name',
        'Contact person', 'Contact phone', 'RFID UID', 'Status',
    ])
    for ticket in tickets:
        boat = ticket.boat
        writer.writerow([
            ticket.code,
            ticket.color,
            boat.boat_class.name if boat and boat.boat_class else '',
            boat.sail_number if boat else '',
            boat.name if boat else '',
            boat.contact_person if boat else '',
            boat.contact_phone if boat else '',
            ticket.rfid_uid,
            ticket.status,
        ])
    return response
```

- [ ] **Step 6: Run tests — expect FAIL on template tests**

```bash
uv run python manage.py test SkaRe.tests.test_ticket_views --verbosity=0 2>&1 | tail -5
```

Expected: Logic tests pass (set_status, pair_rfid, CSV export, bulk create), template tests fail (TemplateDoesNotExist).

---

## Task 2: Ticket templates

**Files:**
- Create: `SkaRe/templates/SkaRe/tickets/list.html`
- Create: `SkaRe/templates/SkaRe/tickets/detail.html`
- Create: `SkaRe/templates/SkaRe/tickets/lookup.html`
- Create: `SkaRe/templates/SkaRe/tickets/create_bulk.html`
- Create: `SkaRe/templates/SkaRe/tickets/on_water.html`

- [ ] **Step 1: Create list.html**

Create `SkaRe/templates/SkaRe/tickets/list.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Sail Tickets" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-3"><i class="bi bi-ticket-perforated"></i> {% trans "Sail Tickets" %}</h1>
<div class="mb-3 d-flex gap-2">
  <a href="{% url 'SkaRe:infodesk_dashboard' %}" class="btn btn-outline-secondary btn-sm">
    <i class="bi bi-arrow-left"></i> {% trans "Dashboard" %}
  </a>
  <a href="{% url 'SkaRe:ticket_lookup' %}" class="btn btn-primary btn-sm">
    <i class="bi bi-search"></i> {% trans "Quick lookup" %}
  </a>
  <a href="{% url 'SkaRe:ticket_create_bulk' %}" class="btn btn-outline-success btn-sm">
    <i class="bi bi-plus-circle"></i> {% trans "Bulk create" %}
  </a>
  <a href="{% url 'SkaRe:ticket_on_water' %}" class="btn btn-outline-danger btn-sm">
    <i class="bi bi-water"></i> {% trans "On water" %}
  </a>
  <a href="{% url 'SkaRe:ticket_export_csv' %}" class="btn btn-outline-dark btn-sm">
    <i class="bi bi-download"></i> {% trans "Export CSV" %}
  </a>
</div>

<form class="row g-2 mb-3" method="get">
  <div class="col-auto">
    <select name="status" class="form-select form-select-sm">
      <option value="">{% trans "All statuses" %}</option>
      {% for s in statuses %}
        <option value="{{ s.value }}" {% if status_filter == s.value %}selected{% endif %}>{{ s.label }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="col-auto">
    <select name="color" class="form-select form-select-sm">
      <option value="">{% trans "All colors" %}</option>
      {% for c in colors %}
        <option value="{{ c.value }}" {% if color_filter == c.value %}selected{% endif %}>{{ c.label }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="col-auto">
    <button type="submit" class="btn btn-secondary btn-sm">{% trans "Filter" %}</button>
  </div>
</form>

<table class="table table-hover align-middle table-sm">
  <thead class="table-dark">
    <tr>
      <th>{% trans "Code" %}</th>
      <th>{% trans "Color" %}</th>
      <th>{% trans "Boat" %}</th>
      <th>{% trans "Status" %}</th>
      <th>{% trans "RFID" %}</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {% for ticket in tickets %}
    <tr>
      <td><a href="{% url 'SkaRe:ticket_detail' ticket.pk %}">{{ ticket.code }}</a></td>
      <td>{{ ticket.get_color_display }}</td>
      <td>{{ ticket.boat|default:"—" }}</td>
      <td>
        {% if ticket.status == 'on_water' %}<span class="badge bg-primary">{{ ticket.get_status_display }}</span>
        {% elif ticket.status == 'lost' %}<span class="badge bg-danger">{{ ticket.get_status_display }}</span>
        {% else %}<span class="badge bg-secondary">{{ ticket.get_status_display }}</span>{% endif %}
      </td>
      <td>
        {% if ticket.rfid_uid %}<i class="bi bi-check-circle text-success"></i>
        {% elif ticket.pending_pairing %}<i class="bi bi-hourglass text-warning"></i>
        {% else %}<i class="bi bi-dash text-muted"></i>{% endif %}
      </td>
      <td>
        <a href="{% url 'SkaRe:ticket_detail' ticket.pk %}" class="btn btn-outline-primary btn-sm">{% trans "Detail" %}</a>
      </td>
    </tr>
    {% empty %}
    <tr><td colspan="6" class="text-muted text-center">{% trans "No tickets found." %}</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 2: Create detail.html**

Create `SkaRe/templates/SkaRe/tickets/detail.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{{ ticket.code }} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-2">{{ ticket.code }}</h1>
<p class="text-muted">{{ ticket.get_color_display }}</p>
<div class="mb-3 d-flex gap-2">
  <a href="{% url 'SkaRe:ticket_list' %}" class="btn btn-outline-secondary btn-sm">
    <i class="bi bi-arrow-left"></i> {% trans "All tickets" %}
  </a>
</div>

{% if messages %}
  {% for msg in messages %}
    <div class="alert alert-info alert-dismissible fade show">{{ msg }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>
  {% endfor %}
{% endif %}

<div class="row mb-4">
  <div class="col-md-6">
    <table class="table table-bordered table-sm">
      <tr><th>{% trans "Status" %}</th><td>{{ ticket.get_status_display }}</td></tr>
      <tr><th>{% trans "Boat" %}</th><td>{% if ticket.boat %}<a href="{% url 'SkaRe:boat_detail' ticket.boat.pk %}">{{ ticket.boat }}</a>{% else %}—{% endif %}</td></tr>
      <tr><th>{% trans "RFID UID" %}</th><td>{{ ticket.rfid_uid|default:"—" }}</td></tr>
      <tr><th>{% trans "Pending pairing" %}</th><td>{% if ticket.pending_pairing %}<span class="badge bg-warning text-dark">{% trans "Waiting for scan…" %}</span>{% else %}{% trans "No" %}{% endif %}</td></tr>
    </table>
  </div>
  <div class="col-md-6">
    <h5>{% trans "Change status" %}</h5>
    <div class="d-flex gap-2 flex-wrap">
      {% for s in statuses %}
      <form method="post" action="{% url 'SkaRe:ticket_set_status' ticket.pk %}">
        {% csrf_token %}
        <input type="hidden" name="new_status" value="{{ s.value }}">
        <input type="hidden" name="next" value="{{ request.path }}">
        <button type="submit" class="btn btn-sm {% if ticket.status == s.value %}btn-secondary disabled{% else %}btn-outline-primary{% endif %}">
          {{ s.label }}
        </button>
      </form>
      {% endfor %}
    </div>
    <div class="mt-3">
      <h5>{% trans "RFID" %}</h5>
      <form method="post" action="{% url 'SkaRe:ticket_pair_rfid' ticket.pk %}">
        {% csrf_token %}
        <button type="submit" class="btn btn-warning btn-sm">
          <i class="bi bi-broadcast"></i> {% trans "Pair RFID" %}
        </button>
      </form>
    </div>
  </div>
</div>

<h5>{% trans "Change log" %}</h5>
<table class="table table-sm table-striped">
  <thead><tr><th>{% trans "Time" %}</th><th>{% trans "Status" %}</th><th>{% trans "By" %}</th><th>{% trans "Note" %}</th></tr></thead>
  <tbody>
    {% for log in logs %}
    <tr>
      <td>{{ log.changed_at|date:"d.m.Y H:i" }}</td>
      <td>{{ log.status }}</td>
      <td>{{ log.changed_by|default:"—" }}</td>
      <td>{{ log.note|default:"" }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="4" class="text-muted">{% trans "No changes yet." %}</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 3: Create lookup.html**

Create `SkaRe/templates/SkaRe/tickets/lookup.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Ticket Lookup" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-3"><i class="bi bi-search"></i> {% trans "Ticket Quick Lookup" %}</h1>
<a href="{% url 'SkaRe:infodesk_dashboard' %}" class="btn btn-outline-secondary btn-sm mb-3">
  <i class="bi bi-arrow-left"></i> {% trans "Dashboard" %}
</a>
<form method="get" class="mb-4">
  <div class="input-group">
    <input type="text" name="q" value="{{ query }}" class="form-control form-control-lg"
           placeholder="{% trans 'Ticket code, boat name, sail number, or owner…' %}" autofocus>
    <button type="submit" class="btn btn-primary">{% trans "Search" %}</button>
  </div>
</form>

{% if query %}
  <p class="text-muted">{% blocktrans with n=results|length %}{{ n }} result(s) for "{{ query }}"{% endblocktrans %}</p>
  <table class="table table-hover align-middle">
    <thead class="table-dark">
      <tr>
        <th>{% trans "Code" %}</th>
        <th>{% trans "Color" %}</th>
        <th>{% trans "Boat" %}</th>
        <th>{% trans "Status" %}</th>
        <th>{% trans "Actions" %}</th>
      </tr>
    </thead>
    <tbody>
      {% for ticket in results %}
      <tr>
        <td><a href="{% url 'SkaRe:ticket_detail' ticket.pk %}">{{ ticket.code }}</a></td>
        <td>{{ ticket.get_color_display }}</td>
        <td>{{ ticket.boat|default:"—" }}</td>
        <td>{{ ticket.get_status_display }}</td>
        <td>
          {% with next_url=request.get_full_path %}
          {% for s in statuses %}
          <form method="post" action="{% url 'SkaRe:ticket_set_status' ticket.pk %}" class="d-inline">
            {% csrf_token %}
            <input type="hidden" name="new_status" value="{{ s.value }}">
            <input type="hidden" name="next" value="{{ next_url }}">
            <button type="submit" class="btn btn-sm {% if ticket.status == s.value %}btn-secondary disabled{% else %}btn-outline-primary{% endif %}">
              {{ s.label }}
            </button>
          </form>
          {% endfor %}
          {% endwith %}
        </td>
      </tr>
      {% empty %}
      <tr><td colspan="5" class="text-muted text-center">{% trans "No tickets found." %}</td></tr>
      {% endfor %}
    </tbody>
  </table>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Create create_bulk.html**

Create `SkaRe/templates/SkaRe/tickets/create_bulk.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Bulk Create Tickets" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-3"><i class="bi bi-plus-circle"></i> {% trans "Bulk Create Sail Tickets" %}</h1>
<a href="{% url 'SkaRe:ticket_list' %}" class="btn btn-outline-secondary btn-sm mb-3">
  <i class="bi bi-arrow-left"></i> {% trans "All tickets" %}
</a>

{% if existing_ticket_count > 0 %}
<div class="alert alert-warning">
  <i class="bi bi-exclamation-triangle"></i>
  {% blocktrans with n=existing_ticket_count %}{{ n }} tickets already exist. Only boats without an assigned ticket will receive a new one.{% endblocktrans %}
</div>
{% endif %}

<div class="card mb-4">
  <div class="card-header">{% trans "Registered boats (without a ticket)" %}</div>
  <div class="card-body">
    <ul class="mb-0">
      {% for color, count in boat_preview.items %}<li>{{ color }}: {{ count }}</li>{% empty %}<li class="text-muted">{% trans "None" %}</li>{% endfor %}
    </ul>
  </div>
</div>

<form method="post">
  {% csrf_token %}
  {% for field in form %}
  <div class="mb-3">
    <label class="form-label fw-bold">{{ field.label }}</label>
    {{ field }}
    {% if field.help_text %}<div class="form-text">{{ field.help_text }}</div>{% endif %}
    {% for error in field.errors %}<div class="text-danger">{{ error }}</div>{% endfor %}
  </div>
  {% endfor %}
  <button type="submit" class="btn btn-success">
    <i class="bi bi-check-circle"></i> {% trans "Create tickets" %}
  </button>
</form>
{% endblock %}
```

- [ ] **Step 5: Create on_water.html**

Create `SkaRe/templates/SkaRe/tickets/on_water.html`:

```html
{% extends 'SkaRe/base.html' %}
{% load i18n %}

{% block title %}{% trans "Boats on Water" %} - SkaRe{% endblock %}

{% block content %}
<h1 class="mb-3"><i class="bi bi-water"></i> {% trans "Boats Currently on Water" %}</h1>
<p class="text-muted">{% trans "Safety view — refreshed on load." %}</p>
<div class="mb-3 d-flex gap-2">
  <a href="{% url 'SkaRe:infodesk_dashboard' %}" class="btn btn-outline-secondary btn-sm">
    <i class="bi bi-arrow-left"></i> {% trans "Dashboard" %}
  </a>
  <a href="{{ request.path }}" class="btn btn-primary btn-sm">
    <i class="bi bi-arrow-clockwise"></i> {% trans "Refresh" %}
  </a>
</div>

<table class="table table-hover align-middle">
  <thead class="table-dark">
    <tr>
      <th>{% trans "Ticket" %}</th>
      <th>{% trans "Color" %}</th>
      <th>{% trans "Boat" %}</th>
      <th>{% trans "Class" %}</th>
      <th>{% trans "Contact" %}</th>
      <th>{% trans "Contact phone" %}</th>
    </tr>
  </thead>
  <tbody>
    {% for ticket in tickets %}
    <tr>
      <td><a href="{% url 'SkaRe:ticket_detail' ticket.pk %}">{{ ticket.code }}</a></td>
      <td>{{ ticket.get_color_display }}</td>
      <td>{% if ticket.boat %}{{ ticket.boat.name }}{% if ticket.boat.sail_number %} ({{ ticket.boat.sail_number }}){% endif %}{% else %}—{% endif %}</td>
      <td>{{ ticket.boat.boat_class|default:"—" }}</td>
      <td>{{ ticket.boat.contact_person|default:"—" }}</td>
      <td>{{ ticket.boat.contact_phone|default:"—" }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="6" class="text-success text-center fw-bold">{% trans "No boats on water." %}</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 6: Run all ticket tests**

```bash
uv run python manage.py test SkaRe.tests.test_ticket_views --verbosity=0 2>&1 | tail -5
```

Expected: All PASS.

- [ ] **Step 7: Run full suite**

```bash
uv run python manage.py test SkaRe --verbosity=0 2>&1 | tail -3
```

Expected: OK.

- [ ] **Step 8: Commit**

```bash
git add SkaRe/forms/tickets.py SkaRe/forms/__init__.py SkaRe/views/tickets.py SkaRe/templates/SkaRe/tickets/ SkaRe/tests/test_ticket_views.py
git commit -m "feat: InfoDesk sail ticket views (list, detail, lookup, bulk create, on-water, CSV)"
```
